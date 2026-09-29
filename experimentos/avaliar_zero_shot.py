"""
Avalia o sistema ATUAL (modelos pré-treinados no COCO, sem ajuste fino) no dataset
da equipe, quadro a quadro. Grava os escores contínuos em um CSV para que os
limiares possam ser variados depois sem rodar os modelos de novo (metricas.py).

Para cada quadro:
- faca_<m>: maior confiança de knife/scissors dada pelo detector YOLOv8<m> (n, s, m);
- pessoas_<p>, outro_<p>, proprio_<p>: saída da heurística de estrangulamento com o
  estimador de pose YOLOv8<p>-pose (n, s):
    outro   = menor distância normalizada entre um punho de OUTRA pessoa e o pescoço
              de alguém (regra i);
    proprio = menor valor, entre as pessoas, da MAIOR distância dos dois punhos ao
              próprio pescoço (regra ii: os dois punhos precisam estar perto).
  O quadro é perigoso para um limiar tau se outro < tau ou proprio < tau.

Rodar a partir da pasta backend:
    .venv\\Scripts\\python.exe ..\\experimentos\\avaliar_zero_shot.py
"""

import csv
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
from detector import ChokeDetector  # noqa: E402

DADOS = RAIZ / "dados" / "derivado"
SAIDA = RAIZ / "experimentos" / "resultados"
CLASSES_PERIGO = {"knife", "scissors"}
DETECTORES = ["n", "s", "m"]
POSES = ["n", "s"]


def escore_heuristica(kps_todas, det: ChokeDetector):
    """Reproduz a heurística do ChokeDetector, mas devolve distâncias contínuas."""
    outro, proprio = np.inf, np.inf
    pescocos = [det._neck(k) for k in kps_todas]
    for v, info in enumerate(pescocos):
        if info is None:
            continue
        pescoco, largura = info
        for a, kps in enumerate(kps_todas):
            dists = []
            for idx in (det.LEFT_WRIST, det.RIGHT_WRIST):
                punho = kps[idx]
                if punho[2] >= det.keypoint_conf:
                    dists.append(float(np.hypot(*(punho[:2] - pescoco)) / largura))
                else:
                    dists.append(np.inf)
            if a != v:
                outro = min(outro, min(dists))
            else:
                proprio = min(proprio, max(dists))
    return outro, proprio


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    with open(DADOS / "indice.csv", encoding="utf-8") as f:
        indice = list(csv.DictReader(f))

    detectores = {m: YOLO(f"yolov8{m}.pt") for m in DETECTORES}
    poses = {p: YOLO(f"yolov8{p}-pose.pt") for p in POSES}
    referencia = ChokeDetector(model=None)  # só para reaproveitar os parâmetros e _neck()
    tempos = {f"det_{m}": [] for m in DETECTORES} | {f"pose_{p}": [] for p in POSES}

    linhas = []
    for i, item in enumerate(indice):
        img = cv2.imread(str(DADOS / "images" / item["arquivo"]))
        linha = dict(item)

        for m, modelo in detectores.items():
            t0 = time.perf_counter()
            r = modelo.predict(img, conf=0.01, verbose=False, device=0)[0]
            tempos[f"det_{m}"].append((time.perf_counter() - t0) * 1000)
            confs = [float(b.conf[0]) for b in r.boxes if modelo.names[int(b.cls[0])] in CLASSES_PERIGO]
            linha[f"faca_{m}"] = max(confs, default=0.0)

        for p, modelo in poses.items():
            t0 = time.perf_counter()
            r = modelo.predict(img, conf=referencia.conf_threshold, verbose=False, device=0)[0]
            tempos[f"pose_{p}"].append((time.perf_counter() - t0) * 1000)
            kps = r.keypoints.data.cpu().numpy() if r.keypoints is not None and len(r.keypoints) else []
            outro, proprio = escore_heuristica(kps, referencia)
            linha[f"pessoas_{p}"] = len(kps)
            linha[f"outro_{p}"] = outro
            linha[f"proprio_{p}"] = proprio

        linhas.append(linha)
        if (i + 1) % 200 == 0:
            print(f"{i + 1}/{len(indice)} quadros")

    with open(SAIDA / "zero_shot_quadros.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)

    print("\nTempo por quadro (mediana, ms, GPU):")
    for nome, t in tempos.items():
        print(f"  {nome}: {np.median(t[10:]):.1f}")
    print(f"\nResultados em {SAIDA / 'zero_shot_quadros.csv'}")


if __name__ == "__main__":
    main()
