"""
Análises complementares do artigo, a partir dos CSVs já gerados (não roda modelos):

1. Intervalos de confiança de 95% por bootstrap POR SEQUÊNCIA: sorteia as
   sequências com reposição (e não os quadros, que são correlacionados dentro de
   uma mesma rajada) e recalcula as métricas por quadro 2.000 vezes.
2. Ablação da janela de confirmação temporal (K de W): sequências detectadas,
   sequências normais com alarme e tempo até o alarme.
3. Ablação das regras da heurística de estrangulamento: só a regra (i), só a (ii)
   e as duas.
4. Ablação do limiar do modelo ajustado, por quadro e por sequência.

Rodar a partir da pasta backend:
    .venv\\Scripts\\python.exe ..\\experimentos\\analises_extras.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "experimentos"))
from metricas import FPS_DATASET, auc, confirmacoes, negativos  # noqa: E402

RES = RAIZ / "experimentos" / "resultados"
N_BOOT = 2000
rng = np.random.default_rng(0)


def carregar():
    zs = pd.read_csv(RES / "zero_shot_quadros.csv")
    ft = pd.read_csv(RES / "finetune_yolov8n_quadros.csv")
    for p in "ns":
        zs[f"escore_enf_{p}"] = np.minimum(zs[f"outro_{p}"], zs[f"proprio_{p}"])
    return zs.merge(ft[["arquivo", "parte", "ft_faca", "ft_enforcar"]], on="arquivo")


def tipo_sequencia(df):
    return df.groupby("clipe")["rotulo"].agg(lambda s: s.mode().iat[0])


def bootstrap(df, funcao):
    """IC 95% sorteando sequências com reposição."""
    grupos = {c: g for c, g in df.groupby("clipe")}
    tipos = tipo_sequencia(df)
    por_tipo = {t: tipos[tipos == t].index.to_numpy() for t in tipos.unique()}
    valores = []
    for _ in range(N_BOOT):
        # sorteio estratificado: mantém o número de sequências de cada tipo
        escolhidas = np.concatenate([rng.choice(v, size=len(v), replace=True) for v in por_tipo.values()])
        amostra = pd.concat([grupos[c] for c in escolhidas], ignore_index=True)
        valores.append(funcao(amostra))
    valores = np.array(valores, dtype=float)
    return np.nanpercentile(valores, 2.5), np.nanpercentile(valores, 97.5)


def fmt(v, ic, pct=True):
    if pct:
        return f"{v:.1%} [{ic[0]:.1%}; {ic[1]:.1%}]"
    return f"{v:.3f} [{ic[0]:.3f}; {ic[1]:.3f}]"


def secao_ic(df, md):
    md.append("## 1. Intervalos de confiança (95%, bootstrap por sequência, 2.000 reamostragens)\n")
    md.append("| Método | Revocação | Alarme falso | AUC |")
    md.append("|---|---|---|---|")
    casos = [
        ("Faca – YOLOv8n COCO (0,45)", "FACA", lambda d: d.faca_n >= 0.45, "faca_n", True),
        ("Faca – YOLOv8s COCO (0,45)", "FACA", lambda d: d.faca_s >= 0.45, "faca_s", True),
        ("Faca – YOLOv8m COCO (0,45)", "FACA", lambda d: d.faca_m >= 0.45, "faca_m", True),
        ("Faca – YOLOv8m COCO (0,25)", "FACA", lambda d: d.faca_m >= 0.25, "faca_m", True),
        ("Faca – YOLOv8n ajustado (0,45)", "FACA", lambda d: d.ft_faca >= 0.45, "ft_faca", True),
        ("Estrang. – heurística pose n (τ=0,6)", "ENFORCAR", lambda d: d.escore_enf_n < 0.6, "escore_enf_n", False),
        ("Estrang. – heurística pose s (τ=0,6)", "ENFORCAR", lambda d: d.escore_enf_s < 0.6, "escore_enf_s", False),
        ("Estrang. – YOLOv8n ajustado (0,45)", "ENFORCAR", lambda d: d.ft_enforcar >= 0.45, "ft_enforcar", True),
    ]
    for nome, alvo, regra, escore, maior in casos:
        def rev(d, alvo=alvo, regra=regra):
            m = d.rotulo.eq(alvo)
            return regra(d)[m].mean() if m.any() else np.nan

        def falso(d, regra=regra):
            return regra(d)[negativos(d)].mean()

        def area(d, alvo=alvo, escore=escore, maior=maior):
            s = d[escore] if maior else -d[escore].clip(upper=50)
            return auc(s[d.rotulo.eq(alvo)], s[negativos(d)])

        md.append(f"| {nome} | {fmt(rev(df), bootstrap(df, rev))} | {fmt(falso(df), bootstrap(df, falso))} | "
                  f"{fmt(area(df), bootstrap(df, area), pct=False)} |")


def resumo_janela(df, coluna, alvo, k, w):
    detectadas, normais_alarme, tempos = 0, 0, []
    n_alvo = n_normal = 0
    for _, g in df.sort_values("quadro").groupby("clipe"):
        if len(g) < 12:
            continue
        tipo = g.rotulo.mode().iat[0]
        inicios = confirmacoes(g[coluna].to_numpy(), k, w)
        if tipo == alvo:
            n_alvo += 1
            if inicios:
                detectadas += 1
                tempos.append((inicios[0] + 1) / FPS_DATASET)
        elif tipo == "normal":
            n_normal += 1
            normais_alarme += bool(inicios)
    tempo = f"{np.median(tempos):.1f} s" if tempos else "-"
    return f"{detectadas}/{n_alvo}", f"{normais_alarme}/{n_normal}", tempo


def secao_janela(df, md):
    md.append("\n## 2. Ablação da janela de confirmação (K de W)\n")
    md.append("| Detector | Janela | Sequências detectadas | Normais com alarme | Tempo até o alarme (mediana) |")
    md.append("|---|---|---|---|---|")
    df = df.assign(f_ft=df.ft_faca >= 0.45, e_ft=df.ft_enforcar >= 0.45,
                   e_hs=df.escore_enf_s < 0.6, e_hn=df.escore_enf_n < 0.6)
    for nome, col, alvo in [("Faca – ajustado", "f_ft", "FACA"), ("Estrang. – ajustado", "e_ft", "ENFORCAR"),
                            ("Estrang. – heurística pose s", "e_hs", "ENFORCAR"),
                            ("Estrang. – heurística pose n", "e_hn", "ENFORCAR")]:
        for k, w in [(1, 1), (3, 8), (6, 12), (10, 20)]:
            det, fal, t = resumo_janela(df, col, alvo, k, w)
            rotulo = "sem janela (1 de 1)" if k == 1 else f"{k} de {w}"
            md.append(f"| {nome} | {rotulo} | {det} | {fal} | {t} |")


def secao_regras(df, md):
    md.append("\n## 3. Ablação das regras da heurística (τ = 0,6, por quadro)\n")
    md.append("| Pose | Regras | Revocação (estrangulamento) | Alarme falso (normal) | Disparo em cenas de faca |")
    md.append("|---|---|---|---|---|")
    for p in "ns":
        for nome, regra in [("só (i): mão de outra pessoa", df[f"outro_{p}"] < 0.6),
                            ("só (ii): duas mãos próprias", df[f"proprio_{p}"] < 0.6),
                            ("(i) + (ii)", (df[f"outro_{p}"] < 0.6) | (df[f"proprio_{p}"] < 0.6))]:
            md.append(f"| {p} | {nome} | {regra[df.rotulo.eq('ENFORCAR')].mean():.1%} | "
                      f"{regra[negativos(df)].mean():.1%} | {regra[df.rotulo.eq('FACA')].mean():.1%} |")


def secao_limiar(df, md):
    md.append("\n## 4. Ablação do limiar do modelo ajustado\n")
    md.append("| Classe | Limiar | Revocação (quadro) | Alarme falso (quadro) | Sequências detectadas | Normais com alarme |")
    md.append("|---|---|---|---|---|---|")
    for nome, col, alvo, (k, w) in [("Faca", "ft_faca", "FACA", (3, 8)), ("Estrangulamento", "ft_enforcar", "ENFORCAR", (6, 12))]:
        for t in (0.25, 0.45, 0.65, 0.85):
            p = df[col] >= t
            det, fal, _ = resumo_janela(df.assign(p=p), "p", alvo, k, w)
            md.append(f"| {nome} | {t:.2f} | {p[df.rotulo.eq(alvo)].mean():.1%} | "
                      f"{p[negativos(df)].mean():.1%} | {det} | {fal} |")


def main():
    df = carregar()
    md = ["# Análises complementares\n"]
    secao_ic(df, md)
    secao_janela(df, md)
    secao_regras(df, md)
    secao_limiar(df, md)
    (RES / "analises_extras.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
