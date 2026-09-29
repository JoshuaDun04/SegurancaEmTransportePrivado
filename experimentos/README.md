# Experimentos do artigo

Scripts que geram todos os resultados do artigo (`docs/artigo/`) a partir do
conjunto de dados da equipe. O dataset **não vai para o git** (pasta `dados/`,
imagens com pessoas); baixe o export COCO do Roboflow Universe
(`sivip/custom-workflow-2-object-detection-dlzx4`) e extraia em
`dados/Custom Workflow 2 Object Detection.coco/`.

Todos rodam a partir da pasta `backend`, com o `.venv` do servidor (precisa
também de `pandas`: `.venv\Scripts\python.exe -m pip install pandas`).

| Ordem | Script | O que faz | Tempo (GTX 1650) |
|---|---|---|---|
| 1 | `preparar_dataset.py` | Junta os splits do Roboflow, recupera sequência/quadro pelo nome do arquivo, reduz para 480x640 e grava rótulos YOLO em `dados/derivado/` | ~3 min |
| 2 | `avaliar_zero_shot.py` | Modelos sem ajuste: YOLOv8 n/s/m (faca) e heurística com pose n/s, escores por quadro | ~5 min |
| 3 | `finetune_cv.py n 50 8` | Ajuste fino do YOLOv8n com validação cruzada de 3 partes **por sequência** | ~90 min |
| 4 | `metricas.py` | Tabelas (`resultados/resultados.md`) e a Figura 5 do artigo | segundos |
| 5 | `figura_exemplos.py` | Figura 3 do artigo, com os rostos desfocados | segundos |
| 6 | `estimar_dados.py` | Consumo de internet móvel por hora e veículos por GPU (servidor remoto) | segundos |

```bash
cd backend
.venv\Scripts\python.exe ..\experimentos\preparar_dataset.py
.venv\Scripts\python.exe ..\experimentos\avaliar_zero_shot.py
.venv\Scripts\python.exe ..\experimentos\finetune_cv.py n 50 8
.venv\Scripts\python.exe ..\experimentos\metricas.py
.venv\Scripts\python.exe ..\experimentos\figura_exemplos.py
```

**Memória da GPU:** com 4 GB, feche jogos e outros programas que usam a GPU
antes do passo 3; se ainda faltar memória, use lote 4 (`finetune_cv.py n 50 4`).

**Por que dividir por sequência:** a divisão original do Roboflow sorteia
quadros, então a mesma rajada de fotos aparece no treino e no teste e o
resultado sai inflado. `finetune_cv.py` define as três partes com sequências
inteiras (ver `PARTES` no script).

Os resultados já calculados ficam em `resultados/` (CSVs por quadro e o resumo
`resultados.md`). Os modelos treinados ficam em `dados/treinos/` (fora do git).

## Gerar o artigo

```bash
cd docs\artigo
node gerar_artigo.js        # precisa do pacote npm "docx" (npm install docx)
```

As figuras 1, 2 e 4 vêm de `docs/artigo/gerar_figuras.py`.
