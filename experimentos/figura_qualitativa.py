"""
Figura de resultados qualitativos do modelo ajustado: acertos e erros reais.

Cada quadro é processado pelo modelo da rodada da validação cruzada em que a sua
sequência estava no TESTE (ou seja, um modelo que nunca viu aquela sequência).
Desenha a anotação (linha fina branca) e a detecção do modelo (caixa colorida com
a confiança), com os rostos desfocados. Roda na CPU.

Rodar a partir da pasta backend:
    .venv\\Scripts\\python.exe ..\\experimentos\\figura_qualitativa.py
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "experimentos"))
from figura_exemplos import desfocar_rostos  # noqa: E402

DADOS = RAIZ / "dados" / "derivado"
TREINOS = RAIZ / "dados" / "treinos"
SAIDA = RAIZ / "docs" / "artigo" / "figuras" / "fig6_qualitativa.png"
LIMIAR = 0.45
# (quadro, parte em que a sequência foi testada, legenda)
CASOS = [
    ("20250530_191840_030", "A", "(a) faca detectada"),
    ("20250530_190936_070", "A", "(b) faca não detectada"),
    ("20250530_192006_050", "B", "(c) estrangulamento detectado"),
    ("20250530_190801_070", "A", "(d) alarme falso (cena normal)"),
]
CORES = {0: (0, 0, 255), 1: (0, 140, 255)}  # FACA vermelho, ENFORCAR laranja (BGR)
NOMES = {0: "FACA", 1: "ENFORCAR"}


def main():
    pose = YOLO("yolov8s-pose.pt")
    modelos = {}
    quadros = []
    for nome, parte, legenda in CASOS:
        if parte not in modelos:
            modelos[parte] = YOLO(str(TREINOS / f"yolov8n_parte{parte}" / "treino" / "weights" / "last.pt"))
        img = cv2.imread(str(DADOS / "images" / f"{nome}.jpg"))
        r = modelos[parte].predict(img, conf=LIMIAR, verbose=False, device="cpu")[0]
        img = desfocar_rostos(img, pose)
        h, w = img.shape[:2]
        # Anotação (verdade): linha fina branca
        for linha in (DADOS / "labels" / f"{nome}.txt").read_text().splitlines():
            if linha.strip():
                _, x, y, bw, bh = map(float, linha.split())
                cv2.rectangle(img, (int((x - bw / 2) * w), int((y - bh / 2) * h)),
                              (int((x + bw / 2) * w), int((y + bh / 2) * h)), (255, 255, 255), 1)
        # Detecção do modelo: caixa grossa colorida com a confiança
        for b in r.boxes:
            c, conf = int(b.cls[0]), float(b.conf[0])
            x0, y0, x1, y1 = map(int, b.xyxy[0])
            cv2.rectangle(img, (x0, y0), (x1, y1), CORES[c], 3)
            texto = f"{NOMES[c]} {conf:.2f}".replace(".", ",")
            (tw, th), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(img, (x0, max(y0 - th - 8, 0)), (x0 + tw + 6, max(y0, th + 8)), CORES[c], -1)
            cv2.putText(img, texto, (x0 + 3, max(y0 - 5, th + 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (255, 255, 255), 2, cv2.LINE_AA)
        faixa = np.full((44, w, 3), 255, np.uint8)
        cv2.putText(faixa, legenda, (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 0, 0), 2, cv2.LINE_AA)
        quadros.append(np.vstack([img, faixa]))
        quadros.append(np.full((h + 44, 8, 3), 255, np.uint8))
    cv2.imwrite(str(SAIDA), np.hstack(quadros[:-1]))
    print(f"Figura: {SAIDA}")


if __name__ == "__main__":
    main()
