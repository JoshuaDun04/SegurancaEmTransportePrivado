"""
Compara o ajuste fino do YOLOv8n e do YOLOv8s (mesma validação cruzada por
sequência, 50 épocas; lote 8 no n e 4 no s, por limite de memória da GTX 1650).

Gera experimentos/resultados/comparacao_n_s.md com:
- métricas por quadro (revocação, alarme falso, AUC) com IC 95% por bootstrap de sequências;
- resultados por sequência com a confirmação temporal do sistema;
- resultado por rodada da validação cruzada.

Rodar a partir da pasta backend:
    .venv\\Scripts\\python.exe ..\\experimentos\\comparar_tamanhos.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "experimentos"))
from analises_extras import bootstrap, resumo_janela  # noqa: E402
from metricas import auc, negativos  # noqa: E402

RES = RAIZ / "experimentos" / "resultados"
JANELAS = {"FACA": (3, 8), "ENFORCAR": (6, 12)}
COLUNAS = {"FACA": "ft_faca", "ENFORCAR": "ft_enforcar"}


def pct(v, ic):
    return f"{v:.1%} [{ic[0]:.1%}; {ic[1]:.1%}]".replace(".", ",")


def main():
    modelos = {}
    for tam in "ns":
        arq = RES / f"finetune_yolov8{tam}_quadros.csv"
        if arq.exists():
            modelos[tam] = pd.read_csv(arq)
    md = ["# YOLOv8n x YOLOv8s ajustados (validação cruzada por sequência)\n"]

    md.append("## Por quadro (limiar 0,45; IC 95% por bootstrap de sequências)\n")
    md.append("| Modelo | Classe | Revocação | Alarme falso | AUC |")
    md.append("|---|---|---|---|---|")
    for tam, df in modelos.items():
        for classe, col in COLUNAS.items():
            def rev(d, classe=classe, col=col):
                m = d.rotulo.eq(classe)
                return (d[col] >= 0.45)[m].mean() if m.any() else np.nan

            def falso(d, col=col):
                return (d[col] >= 0.45)[negativos(d)].mean()

            def area(d, classe=classe, col=col):
                return auc(d[col][d.rotulo.eq(classe)], d[col][negativos(d)])

            md.append(f"| YOLOv8{tam} | {classe} | {pct(rev(df), bootstrap(df, rev))} | "
                      f"{pct(falso(df), bootstrap(df, falso))} | {area(df):.3f} |".replace(".", ","))

    md.append("\n## Por sequência (janelas do sistema: faca 3 de 8, estrangulamento 6 de 12)\n")
    md.append("| Modelo | Classe | Sequências detectadas | Normais com alarme | Tempo mediano |")
    md.append("|---|---|---|---|---|")
    for tam, df in modelos.items():
        for classe, col in COLUNAS.items():
            k, w = JANELAS[classe]
            det, fal, t = resumo_janela(df.assign(p=df[col] >= 0.45), "p", classe, k, w)
            md.append(f"| YOLOv8{tam} | {classe} | {det} | {fal} | {t.replace('.', ',')} |")

    md.append("\n## Por rodada da validação cruzada (revocação por quadro, limiar 0,45)\n")
    md.append("| Modelo | Parte | Faca | Estrangulamento | Alarme falso |")
    md.append("|---|---|---|---|---|")
    for tam, df in modelos.items():
        for parte, g in df.groupby("parte"):
            alarme = (g.ft_faca >= 0.45) | (g.ft_enforcar >= 0.45)
            md.append(f"| YOLOv8{tam} | {parte} | {(g[g.rotulo.eq('FACA')].ft_faca >= 0.45).mean():.1%} | "
                      f"{(g[g.rotulo.eq('ENFORCAR')].ft_enforcar >= 0.45).mean():.1%} | "
                      f"{alarme[negativos(g)].mean():.1%} |".replace(".", ","))

    (RES / "comparacao_n_s.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
