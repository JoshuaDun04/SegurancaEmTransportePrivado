"""
Ajuste fino do YOLOv8 no dataset da equipe (classes FACA e ENFORCAR), com
validação cruzada de 3 partes separadas POR VÍDEO.

Por que por vídeo: os quadros de um mesmo vídeo são quase idênticos. Se o mesmo
vídeo aparecesse no treino e no teste (como na divisão original do Roboflow, que
sorteia quadros), o modelo seria testado em imagens que praticamente já viu e o
resultado sairia inflado.

Cada parte tem vídeos normais, de faca e de estrangulamento. Em cada rodada, o
modelo é treinado em duas partes e testado na terceira; ao final, cada quadro do
dataset foi avaliado exatamente uma vez, por um modelo que nunca viu o vídeo dele.
O modelo usado no teste é o da última época (last.pt), e não o "melhor" segundo a
validação, para não escolher o modelo olhando para os dados de teste.

Rodar a partir da pasta backend:
    .venv\\Scripts\\python.exe ..\\experimentos\\finetune_cv.py [n|s] [epocas] [lote]
"""

import csv
import sys
import time
from pathlib import Path

import numpy as np
from ultralytics import YOLO

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados" / "derivado"
TREINOS = RAIZ / "dados" / "treinos"
SAIDA = RAIZ / "experimentos" / "resultados"

# Partes estratificadas por tipo de vídeo (prefixo do nome = data_hora da gravação)
PARTES = {
    "A": ["20250530_190801", "20250530_191740",                     # normais
          "20250530_190936", "20250530_191840",                     # faca
          "20250530_191022", "20250530_191609", "20250530_191937"],  # estrangulamento
    "B": ["20250530_191404", "20250530_191807",
          "20250530_191448", "20250530_191902",
          "20250530_191037", "20250530_191642", "20250530_192006", "20250530_191124"],
    "C": ["20250530_191419",
          "20250530_191459", "20250530_191519",
          "20250530_191049", "20250530_192025", "20250530_191555"],
}
NOMES = {0: "FACA", 1: "ENFORCAR"}


def main():
    tamanho = sys.argv[1] if len(sys.argv) > 1 else "n"
    epocas = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    # Na GTX 1650 (4 GB), use lote 4 se outros programas estiverem ocupando a GPU.
    lote = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    TREINOS.mkdir(parents=True, exist_ok=True)
    SAIDA.mkdir(parents=True, exist_ok=True)

    with open(DADOS / "indice.csv", encoding="utf-8") as f:
        indice = list(csv.DictReader(f))
    todos = {c for p in PARTES.values() for c in p}
    faltando = {i["clipe"] for i in indice} - todos
    assert not faltando, f"vídeos sem parte definida: {faltando}"

    linhas, tempos = [], []
    for teste, clipes_teste in PARTES.items():
        treino = [i for i in indice if i["clipe"] not in clipes_teste]
        avaliar = [i for i in indice if i["clipe"] in clipes_teste]
        pasta = TREINOS / f"yolov8{tamanho}_parte{teste}"
        pasta.mkdir(exist_ok=True)
        (pasta / "treino.txt").write_text(
            "\n".join(str(DADOS / "images" / i["arquivo"]) for i in treino), encoding="utf-8")
        (pasta / "teste.txt").write_text(
            "\n".join(str(DADOS / "images" / i["arquivo"]) for i in avaliar), encoding="utf-8")
        (pasta / "dados.yaml").write_text(
            f"train: {pasta / 'treino.txt'}\nval: {pasta / 'teste.txt'}\n"
            f"names:\n  0: FACA\n  1: ENFORCAR\n", encoding="utf-8")

        print(f"\n=== Parte de teste {teste}: treino {len(treino)} quadros, teste {len(avaliar)} ===")
        t0 = time.time()
        modelo = YOLO(f"yolov8{tamanho}.pt")  # parte do modelo pré-treinado no COCO
        modelo.train(data=str(pasta / "dados.yaml"), epochs=epocas, imgsz=640, batch=lote,
                     workers=2, cache=True, seed=0, deterministic=True, project=str(pasta),
                     name="treino", exist_ok=True, plots=False, verbose=False)
        print(f"treino: {(time.time() - t0) / 60:.1f} min")

        final = YOLO(str(pasta / "treino" / "weights" / "last.pt"))
        for item in avaliar:
            t1 = time.perf_counter()
            r = final.predict(str(DADOS / "images" / item["arquivo"]), conf=0.01,
                              verbose=False, device=0)[0]
            tempos.append((time.perf_counter() - t1) * 1000)
            maximo = {0: 0.0, 1: 0.0}
            for b in r.boxes:
                cls = int(b.cls[0])
                maximo[cls] = max(maximo[cls], float(b.conf[0]))
            linhas.append({"arquivo": item["arquivo"], "clipe": item["clipe"],
                           "quadro": item["quadro"], "rotulo": item["rotulo"], "parte": teste,
                           "ft_faca": maximo[0], "ft_enforcar": maximo[1]})

    saida = SAIDA / f"finetune_yolov8{tamanho}_quadros.csv"
    with open(saida, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)
    print(f"\nInferência (inclui leitura do arquivo): mediana {np.median(tempos[10:]):.1f} ms")
    print(f"Resultados em {saida}")


if __name__ == "__main__":
    main()
