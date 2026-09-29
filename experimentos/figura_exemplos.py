"""
Gera a figura com exemplos do dataset (normal, faca, estrangulamento), com as
caixas anotadas e os ROSTOS DESFOCADOS, para uso no artigo.

Os rostos são localizados pelos pontos-chave de nariz, olhos e orelhas do
YOLOv8s-pose; cada cabeça recebe um desfoque forte em uma região proporcional à
distância entre esses pontos.

Rodar a partir da pasta backend:
    .venv\\Scripts\\python.exe ..\\experimentos\\figura_exemplos.py
"""

from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados" / "derivado"
SAIDA = RAIZ / "docs" / "artigo" / "figuras" / "fig5_exemplos.png"
EXEMPLOS = [("20250530_190801_050", "(a) normal"),
            ("20250530_191840_030", "(b) faca"),
            ("20250530_192006_050", "(c) estrangulamento")]
CORES = {0: (0, 0, 255), 1: (0, 140, 255)}  # FACA vermelho, ENFORCAR laranja (BGR)


def desfocar_rostos(img, pose):
    r = pose.predict(img, conf=0.10, verbose=False)[0]
    if r.keypoints is None:
        return img
    for kps in r.keypoints.data.cpu().numpy():
        olhos_nariz = kps[:3]  # nariz e olhos (as orelhas espalham demais a região)
        visiveis = olhos_nariz[olhos_nariz[:, 2] > 0.2][:, :2]
        if len(visiveis) == 0:
            continue
        cx, cy = visiveis.mean(axis=0)
        # Tamanho da cabeça estimado pela distância entre os olhos, com limites
        olho_e, olho_d = kps[1], kps[2]
        dist_olhos = np.hypot(*(olho_e[:2] - olho_d[:2])) if min(olho_e[2], olho_d[2]) > 0.2 else 20
        raio = float(np.clip(dist_olhos * 1.8, 18, 45))
        # Elipse cobrindo testa, olhos, nariz e boca, sem descer até o pescoço
        mascara = np.zeros(img.shape[:2], np.uint8)
        cv2.ellipse(mascara, (int(cx), int(cy - raio * 0.2)), (int(raio), int(raio * 1.25)), 0, 0, 360, 255, -1)
        borrada = cv2.GaussianBlur(img, (0, 0), sigmaX=10)
        img[mascara > 0] = borrada[mascara > 0]
    return img


def main():
    pose = YOLO("yolov8s-pose.pt")
    quadros = []
    for nome, legenda in EXEMPLOS:
        img = cv2.imread(str(DADOS / "images" / f"{nome}.jpg"))
        img = desfocar_rostos(img, pose)
        h, w = img.shape[:2]
        for linha in (DADOS / "labels" / f"{nome}.txt").read_text().splitlines():
            if not linha.strip():
                continue
            c, x, y, bw, bh = map(float, linha.split())
            p0 = (int((x - bw / 2) * w), int((y - bh / 2) * h))
            p1 = (int((x + bw / 2) * w), int((y + bh / 2) * h))
            cv2.rectangle(img, p0, p1, CORES[int(c)], 3)
        faixa = np.full((44, w, 3), 255, np.uint8)
        cv2.putText(faixa, legenda, (10, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2, cv2.LINE_AA)
        quadros.append(np.vstack([img, faixa]))
        quadros.append(np.full((684, 8, 3), 255, np.uint8))
    cv2.imwrite(str(SAIDA), np.hstack(quadros[:-1]))
    print(f"Figura: {SAIDA}")


if __name__ == "__main__":
    main()
