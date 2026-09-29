"""
Benchmark de latência do pipeline de detecção (usado nos resultados do artigo).

Mede, para cada configuração de hardware/precisão, o tempo de inferência de cada
modelo e do pipeline completo, com as mesmas imagens e no mesmo tamanho de frame
que o app envia. Reporta mediana e percentil 95 (p95) em milissegundos.

Rodar com:
    .venv\\Scripts\\python.exe benchmark.py
"""

import os
import platform
import statistics
import time

import cv2
import numpy as np
import torch
import ultralytics
from ultralytics import YOLO

from detector import ChokeDetector, SharedModel, WeaponDetector

REPETICOES = 100
AQUECIMENTO = 10
# O app envia o snapshot do preview reduzido para 480 px de largura; em um celular
# com tela 1080x2340 (ex: Galaxy A34), isso dá um frame de 480x1040 em retrato.
FRAME_W, FRAME_H = 480, 1040


def carregar_frames():
    assets = os.path.join(os.path.dirname(ultralytics.__file__), "assets")
    frames = []
    for nome in ("bus.jpg", "zidane.jpg"):
        img = cv2.imread(os.path.join(assets, nome))
        frames.append(cv2.resize(img, (FRAME_W, FRAME_H)))
    return frames


def percentil(valores, p):
    return float(np.percentile(valores, p))


def medir(func, frames):
    for i in range(AQUECIMENTO):
        func(frames[i % len(frames)])
    tempos = []
    for i in range(REPETICOES):
        t0 = time.perf_counter()
        func(frames[i % len(frames)])
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        tempos.append((time.perf_counter() - t0) * 1000)
    return statistics.median(tempos), percentil(tempos, 95)


def configurar(modelo: SharedModel, device, precision):
    modelo.device = device
    modelo.precision = precision


def main():
    frames = carregar_frames()
    print(f"Python {platform.python_version()} | torch {torch.__version__} | "
          f"ultralytics {ultralytics.__version__}")
    print(f"CPU: {platform.processor()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Frame: {FRAME_W}x{FRAME_H} | {REPETICOES} repetições após {AQUECIMENTO} de aquecimento\n")

    # Decodificação do JPEG (etapa que o servidor faz antes da inferência)
    jpeg = cv2.imencode(".jpg", frames[0], [cv2.IMWRITE_JPEG_QUALITY, 60])[1]
    med, p95 = medir(lambda _f: cv2.imdecode(jpeg, cv2.IMREAD_COLOR), frames)
    print(f"Decodificação JPEG ({len(jpeg) / 1024:.0f} KB): mediana {med:.1f} ms | p95 {p95:.1f} ms\n")

    arma = SharedModel("yolov8n.pt")
    pose = SharedModel("yolov8n-pose.pt")

    configs = [("CPU", "cpu", "fp32")]
    if torch.cuda.is_available():
        configs += [("GPU FP32", 0, "fp32"), ("GPU FP16", 0, "fp16")]

    print(f"{'Configuração':<12} {'Etapa':<22} {'Mediana (ms)':>13} {'p95 (ms)':>10}")
    for nome, device, precision in configs:
        configurar(arma, device, precision)
        configurar(pose, device, precision)
        weapon = WeaponDetector(arma)
        choke = ChokeDetector(pose)
        etapas = [
            ("YOLOv8n (objetos)", weapon.process),
            ("YOLOv8n-pose (pose)", choke.process),
            ("Pipeline completo", lambda f: (weapon.process(f), choke.process(f))),
        ]
        for etapa, func in etapas:
            med, p95 = medir(func, frames)
            print(f"{nome:<12} {etapa:<22} {med:>13.1f} {p95:>10.1f}")


if __name__ == "__main__":
    main()
