"""
Estima o consumo de internet móvel do app com servidor remoto.

Mede o tamanho dos quadros do dataset no formato que o app envia (480 px de
largura, JPEG qualidade 60, codificado em base64) e projeta o volume de dados por
hora para algumas taxas de quadros. Também estima quantos veículos uma GPU atende,
a partir do tempo por quadro medido em benchmark.py.

Rodar a partir da pasta backend:
    .venv\\Scripts\\python.exe ..\\experimentos\\estimar_dados.py
"""

import base64
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
IMAGENS = sorted((RAIZ / "dados" / "derivado" / "images").glob("*.jpg"))[::5]  # 1 a cada 5 quadros
TEMPO_GPU_MS = 20.8  # pipeline completo na GTX 1650 (benchmark.py, mediana)


def main():
    tamanhos = []
    for arquivo in IMAGENS:
        img = cv2.imread(str(arquivo))
        _, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 60])
        tamanhos.append(len(base64.b64encode(jpeg.tobytes())))
    mediana = float(np.median(tamanhos))
    print(f"{len(tamanhos)} quadros: mediana {mediana / 1024:.1f} KB por quadro (base64), "
          f"p95 {np.percentile(tamanhos, 95) / 1024:.1f} KB")

    capacidade = 1000 / TEMPO_GPU_MS
    print(f"\nCapacidade estimada da GPU: {capacidade:.0f} quadros/s (sem contar rede e sobrecargas)")
    print(f"{'Quadros/s por veículo':>22} {'Mbit/s':>8} {'GB/hora':>8} {'GB em 8 h':>10} {'Veículos por GPU':>17}")
    for fps in (2, 5, 6.7):
        print(f"{fps:>22} {mediana * 8 * fps / 1e6:>8.2f} {mediana * fps * 3600 / 1e9:>8.2f} "
              f"{mediana * fps * 3600 * 8 / 1e9:>10.1f} {capacidade / fps:>17.0f}")


if __name__ == "__main__":
    main()
