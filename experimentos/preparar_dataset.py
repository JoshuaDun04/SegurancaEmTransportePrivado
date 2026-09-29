"""
Prepara o dataset da equipe (export COCO do Roboflow) para os experimentos.

- Junta train/valid/test do Roboflow: a divisão original sorteia QUADROS, então o
  mesmo vídeo aparece nos três conjuntos. Os experimentos refazem a divisão por
  vídeo (ver finetune_cv.py).
- Recupera o vídeo (clipe) e o número do quadro a partir do nome do arquivo
  (ex: 20250530_191022_072_jpg.rf.XXXX.jpg -> clipe 20250530_191022, quadro 72).
- Reduz cada imagem para 480x640, a mesma largura que o app envia ao servidor.
- Grava rótulos no formato YOLO (0 = FACA, 1 = ENFORCAR) e um índice CSV.

Rodar a partir da pasta backend:
    .venv\\Scripts\\python.exe ..\\experimentos\\preparar_dataset.py
"""

import csv
import json
import re
from pathlib import Path

import cv2

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "dados" / "Custom Workflow 2 Object Detection.coco"
DESTINO = RAIZ / "dados" / "derivado"
LARGURA, ALTURA = 480, 640
CLASSES = {"FACA": 0, "ENFORCAR": 1}
PADRAO = re.compile(r"(\d{8}_\d{6})_(\d+)(?:\(\d+\))?_jpg")


def main():
    (DESTINO / "images").mkdir(parents=True, exist_ok=True)
    (DESTINO / "labels").mkdir(parents=True, exist_ok=True)
    linhas = []
    for split in ("train", "valid", "test"):
        coco = json.loads((ORIGEM / split / "_annotations.coco.json").read_text(encoding="utf-8"))
        nomes = {c["id"]: c["name"] for c in coco["categories"]}
        anotacoes = {}
        for a in coco["annotations"]:
            anotacoes.setdefault(a["image_id"], []).append(a)

        for img in coco["images"]:
            clipe, quadro = PADRAO.match(img["file_name"]).groups()
            base = f"{clipe}_{int(quadro):03d}"
            w0, h0 = img["width"], img["height"]

            imagem = cv2.imread(str(ORIGEM / split / img["file_name"]))
            imagem = cv2.resize(imagem, (LARGURA, ALTURA), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(DESTINO / "images" / f"{base}.jpg"), imagem, [cv2.IMWRITE_JPEG_QUALITY, 90])

            rotulos, yolo = set(), []
            for a in anotacoes.get(img["id"], []):
                nome = nomes[a["category_id"]]
                if nome not in CLASSES:
                    continue
                rotulos.add(nome)
                x, y, w, h = a["bbox"]  # COCO: canto superior esquerdo + largura/altura, em pixels
                yolo.append(f"{CLASSES[nome]} {(x + w / 2) / w0:.6f} {(y + h / 2) / h0:.6f} "
                            f"{w / w0:.6f} {h / h0:.6f}")
            (DESTINO / "labels" / f"{base}.txt").write_text("\n".join(yolo), encoding="utf-8")

            rotulo = "/".join(sorted(rotulos)) or "normal"
            linhas.append({"arquivo": f"{base}.jpg", "clipe": clipe, "quadro": int(quadro),
                           "rotulo": rotulo, "split_roboflow": split})

    linhas.sort(key=lambda r: (r["clipe"], r["quadro"]))
    with open(DESTINO / "indice.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)
    print(f"{len(linhas)} imagens preparadas em {DESTINO}")


if __name__ == "__main__":
    main()
