"""
Calcula as métricas dos experimentos a partir dos CSVs de avaliar_zero_shot.py e
finetune_cv.py, e gera as tabelas (Markdown) e figuras usadas no artigo.

Métricas por QUADRO (cada imagem isolada):
  revocação     = fração dos quadros com a situação em que o detector disparou;
  alarme falso  = fração dos quadros de cenas normais em que o detector disparou;
  AUC           = área sob a curva ROC (1 = separa perfeitamente, 0,5 = acaso).

Métricas por VÍDEO (sequência de quadros com a confirmação temporal do sistema,
K perigosos entre os últimos W): se o alarme foi confirmado nos vídeos com a
situação, em quantos quadros, e quantos alarmes falsos surgiram nos vídeos normais.

Rodar a partir da pasta backend:
    .venv\\Scripts\\python.exe ..\\experimentos\\metricas.py
"""

from collections import deque
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "experimentos" / "resultados"
FIGS = RAIZ / "docs" / "artigo" / "figuras"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

JANELA_FACA = (3, 8)        # K de W, como no WeaponDetector
JANELA_ENFORCAR = (6, 12)   # K de W, como no ChokeDetector
# Taxa das rajadas do dataset, calculada pelos horários do EXIF (~100 fotos em ~8 s)
FPS_DATASET = 12.3


def negativos(df):
    """Quadros negativos: sem anotação E pertencentes a uma sequência normal.

    Os poucos quadros sem anotação no início/fim das sequências de faca ou de
    estrangulamento são transições da ação (ambíguos) e ficam fora das métricas
    por quadro: não contam como positivos nem como negativos.
    """
    tipo = df.groupby("clipe")["rotulo"].transform(lambda s: s.mode().iat[0])
    return df.rotulo.eq("normal") & tipo.eq("normal")


def auc(pos, neg):
    """AUC pela estatística de Mann-Whitney (empates contam meio)."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    todos = np.concatenate([pos, neg])
    ordem = pd.Series(todos).rank().to_numpy()
    return (ordem[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def confirmacoes(perigo, k, w):
    """Aplica a janela K-de-W; devolve os índices em que um alarme começa."""
    hist, ativo, inicios = deque(maxlen=w), False, []
    for i, p in enumerate(perigo):
        hist.append(bool(p))
        confirmado = sum(hist) >= k
        if confirmado and not ativo:
            inicios.append(i)
        ativo = confirmado
    return inicios


def por_video(df, coluna_perigo, rotulo_alvo, k, w):
    """Resumo por vídeo: alarme nos vídeos da situação e alarmes falsos nos normais."""
    linhas = []
    for clipe, g in df.sort_values("quadro").groupby("clipe"):
        if len(g) < w:  # quadros avulsos (vídeos com 1 imagem) não formam sequência
            continue
        tipo = g["rotulo"].mode().iat[0]
        inicios = confirmacoes(g[coluna_perigo].to_numpy(), k, w)
        linhas.append({"clipe": clipe, "tipo": tipo, "n": len(g), "alarmes": len(inicios),
                       "primeiro": (inicios[0] + 1) if inicios else None})
    v = pd.DataFrame(linhas)
    alvo, normais = v[v.tipo == rotulo_alvo], v[v.tipo == "normal"]
    return {
        "videos_alvo": len(alvo),
        "detectados": int((alvo.alarmes > 0).sum()),
        "quadros_ate_alarme": alvo.primeiro.dropna().tolist(),
        "videos_normais": len(normais),
        "normais_com_alarme": int((normais.alarmes > 0).sum()),
        "alarmes_falsos": int(normais.alarmes.sum()),
    }


def sistema_por_video(df, detectores):
    """Sistema completo: alarme se QUALQUER detector confirmar (cada um com sua janela).

    detectores: lista de (coluna_booleana, K, W). Vídeos de faca ou estrangulamento são
    positivos; vídeos normais, negativos.
    """
    linhas = []
    for clipe, g in df.sort_values("quadro").groupby("clipe"):
        if len(g) < 12:
            continue
        tipo = g["rotulo"].mode().iat[0]
        inicios = sorted(i for col, k, w in detectores for i in confirmacoes(g[col].to_numpy(), k, w))
        linhas.append({"tipo": tipo, "alarmou": bool(inicios), "primeiro": (inicios[0] + 1) if inicios else None,
                       "alarmes": sum(len(confirmacoes(g[col].to_numpy(), k, w)) for col, k, w in detectores)})
    v = pd.DataFrame(linhas)
    pos, neg = v[v.tipo != "normal"], v[v.tipo == "normal"]
    return {"positivos": len(pos), "detectados": int(pos.alarmou.sum()),
            "quadros_ate_alarme": pos.primeiro.dropna().tolist(),
            "normais": len(neg), "normais_com_alarme": int(neg.alarmou.sum()),
            "alarmes_falsos": int(neg.alarmes.sum())}


def fmt_tempo(quadros):
    if not quadros:
        return "-"
    med = np.median(quadros)
    return (f"{med:.0f} ({min(quadros):.0f}–{max(quadros):.0f}) ≈ {med / FPS_DATASET:.1f} s "
            f"({min(quadros) / FPS_DATASET:.1f}–{max(quadros) / FPS_DATASET:.1f} s)")


def linha_quadro(df, escore, limiar, alvo, maior_e_perigo=True):
    s = df[escore]
    perigo = (s >= limiar) if maior_e_perigo else (s < limiar)
    pos, neg = df.rotulo.eq(alvo), negativos(df)
    sinal = s if maior_e_perigo else -s.clip(upper=50)
    return perigo, {
        "revocacao": perigo[pos].mean(), "alarme_falso": perigo[neg].mean(),
        "auc": auc(sinal[pos], sinal[neg]),
    }


def main():
    zs = pd.read_csv(RES / "zero_shot_quadros.csv")
    ft_path = RES / "finetune_yolov8n_quadros.csv"
    ft = pd.read_csv(ft_path) if ft_path.exists() else None
    md = ["# Resultados dos experimentos\n"]
    md.append(f"Quadros: {len(zs)} ({zs.rotulo.value_counts().to_dict()})\n")

    # ---------- Faca ----------
    md.append("## Faca: por quadro (positivos: FACA; negativos: normal)\n")
    md.append("| Detector | Limiar | Revocação | Alarme falso | AUC |")
    md.append("|---|---|---|---|---|")
    configs_faca = [(f"YOLOv8{m} COCO", f"faca_{m}", t, zs) for m in "nsm" for t in (0.45, 0.25)]
    if ft is not None:
        configs_faca += [("YOLOv8n ajustado", "ft_faca", t, ft) for t in (0.45, 0.25)]
    for nome, col, t, df in configs_faca:
        _, r = linha_quadro(df, col, t, "FACA")
        md.append(f"| {nome} | {t} | {r['revocacao']:.1%} | {r['alarme_falso']:.1%} | {r['auc']:.3f} |")

    # ---------- Estrangulamento ----------
    for p in "ns":
        zs[f"escore_enf_{p}"] = np.minimum(zs[f"outro_{p}"], zs[f"proprio_{p}"])
    md.append("\n## Estrangulamento: por quadro (positivos: ENFORCAR; negativos: normal)\n")
    md.append("| Método | Limiar | Revocação | Alarme falso | Alarme em cenas de faca | AUC |")
    md.append("|---|---|---|---|---|---|")
    for p in "ns":
        for tau in (0.4, 0.6, 0.8):
            perigo, r = linha_quadro(zs, f"escore_enf_{p}", tau, "ENFORCAR", maior_e_perigo=False)
            md.append(f"| Heurística (pose {p}) | τ={tau} | {r['revocacao']:.1%} | {r['alarme_falso']:.1%} | "
                      f"{perigo[zs.rotulo.eq('FACA')].mean():.1%} | {r['auc']:.3f} |")
    if ft is not None:
        for t in (0.45, 0.25):
            perigo, r = linha_quadro(ft, "ft_enforcar", t, "ENFORCAR")
            md.append(f"| YOLOv8n ajustado | {t} | {r['revocacao']:.1%} | {r['alarme_falso']:.1%} | "
                      f"{perigo[ft.rotulo.eq('FACA')].mean():.1%} | {r['auc']:.3f} |")

    # ---------- Por vídeo, com confirmação temporal ----------
    md.append("\n## Por vídeo, com confirmação temporal\n")
    md.append("| Situação | Método | Vídeos detectados | Quadros até o alarme (mediana; faixa) "
              "| Vídeos normais com alarme | Alarmes falsos |")
    md.append("|---|---|---|---|---|---|")
    casos = [
        ("Faca", "YOLOv8n COCO (0,45)", zs.assign(p=zs.faca_n >= 0.45), "FACA", JANELA_FACA),
        ("Faca", "YOLOv8m COCO (0,25)", zs.assign(p=zs.faca_m >= 0.25), "FACA", JANELA_FACA),
        ("Estrangulamento", "Heurística pose n (τ=0,6)", zs.assign(p=zs.escore_enf_n < 0.6), "ENFORCAR", JANELA_ENFORCAR),
        ("Estrangulamento", "Heurística pose s (τ=0,6)", zs.assign(p=zs.escore_enf_s < 0.6), "ENFORCAR", JANELA_ENFORCAR),
    ]
    if ft is not None:
        casos += [
            ("Faca", "YOLOv8n ajustado (0,45)", ft.assign(p=ft.ft_faca >= 0.45), "FACA", JANELA_FACA),
            ("Estrangulamento", "YOLOv8n ajustado (0,45)", ft.assign(p=ft.ft_enforcar >= 0.45), "ENFORCAR", JANELA_ENFORCAR),
        ]
    resumo_videos = {}
    for sit, nome, df, alvo, (k, w) in casos:
        r = por_video(df, "p", alvo, k, w)
        resumo_videos[(sit, nome)] = r
        md.append(f"| {sit} | {nome} | {r['detectados']}/{r['videos_alvo']} | {fmt_tempo(r['quadros_ate_alarme'])} | "
                  f"{r['normais_com_alarme']}/{r['videos_normais']} | {r['alarmes_falsos']} |")

    # ---------- Sistema completo (faca OU estrangulamento) ----------
    md.append("\n## Sistema completo por vídeo (alarme = faca OU estrangulamento)\n")
    md.append("| Configuração | Vídeos perigosos detectados | Quadros até o alarme | "
              "Vídeos normais com alarme | Alarmes falsos |")
    md.append("|---|---|---|---|---|")
    zs["f_n45"], zs["f_m25"] = zs.faca_n >= 0.45, zs.faca_m >= 0.25
    zs["e_n6"], zs["e_s6"] = zs.escore_enf_n < 0.6, zs.escore_enf_s < 0.6
    sistemas = [
        ("Atual: YOLOv8n (0,45) + heurística pose n", zs, [("f_n45", *JANELA_FACA), ("e_n6", *JANELA_ENFORCAR)]),
        ("Sem treino, melhorado: YOLOv8m (0,25) + heurística pose s", zs,
         [("f_m25", *JANELA_FACA), ("e_s6", *JANELA_ENFORCAR)]),
    ]
    if ft is not None:
        ft["f45"], ft["e45"] = ft.ft_faca >= 0.45, ft.ft_enforcar >= 0.45
        misto = ft.merge(zs[["arquivo", "e_s6"]], on="arquivo")
        sistemas += [
            ("Ajustado: YOLOv8n treinado (FACA e ENFORCAR, 0,45)", ft,
             [("f45", *JANELA_FACA), ("e45", *JANELA_ENFORCAR)]),
            ("Híbrido: YOLOv8n treinado (FACA) + heurística pose s", misto,
             [("f45", *JANELA_FACA), ("e_s6", *JANELA_ENFORCAR)]),
        ]
    for nome, df, dets in sistemas:
        r = sistema_por_video(df, dets)
        md.append(f"| {nome} | {r['detectados']}/{r['positivos']} | {fmt_tempo(r['quadros_ate_alarme'])} | "
                  f"{r['normais_com_alarme']}/{r['normais']} | {r['alarmes_falsos']} |")

    # ---------- Variação entre as partes da validação cruzada ----------
    if ft is not None:
        md.append("\n## Modelo ajustado por parte da validação cruzada (limiar 0,45, por quadro)\n")
        md.append("| Parte | Quadros | Revocação FACA | Revocação ENFORCAR | Alarme falso | AUC FACA | AUC ENFORCAR "
                  "| mAP@0,5 (última época) |")
        md.append("|---|---|---|---|---|---|---|---|")
        for parte, g in ft.groupby("parte"):
            neg = negativos(g)
            alarme = (g.ft_faca >= 0.45) | (g.ft_enforcar >= 0.45)
            res_csv = RAIZ / "dados" / "treinos" / f"yolov8n_parte{parte}" / "treino" / "results.csv"
            mapa = "-"
            if res_csv.exists():
                r = pd.read_csv(res_csv)
                r.columns = [c.strip() for c in r.columns]
                mapa = f"{r['metrics/mAP50(B)'].iloc[-1]:.3f}"
            md.append(
                f"| {parte} | {len(g)} | {(g[g.rotulo.eq('FACA')].ft_faca >= 0.45).mean():.1%} | "
                f"{(g[g.rotulo.eq('ENFORCAR')].ft_enforcar >= 0.45).mean():.1%} | {alarme[neg].mean():.1%} | "
                f"{auc(g[g.rotulo.eq('FACA')].ft_faca, g[neg].ft_faca):.3f} | "
                f"{auc(g[g.rotulo.eq('ENFORCAR')].ft_enforcar, g[neg].ft_enforcar):.3f} | {mapa} |")

    (RES / "resultados.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))

    # ---------- Figura: curvas revocação x alarme falso ----------
    fig, eixos = plt.subplots(1, 2, figsize=(6.4, 3.0))
    limiares = np.linspace(0, 1, 201)
    estilos = {"n": ("#bbbbbb", "--"), "s": ("#777777", "-."), "m": ("#444444", ":")}
    ax = eixos[0]
    pos, neg = zs.rotulo.eq("FACA"), negativos(zs)
    for m in "nsm":
        cor, ls = estilos[m]
        ax.plot([(zs[neg][f"faca_{m}"] >= t).mean() for t in limiares],
                [(zs[pos][f"faca_{m}"] >= t).mean() for t in limiares], ls, color=cor, label=f"YOLOv8{m} COCO")
    if ft is not None:
        pf, nf = ft.rotulo.eq("FACA"), negativos(ft)
        ax.plot([(ft[nf].ft_faca >= t).mean() for t in limiares],
                [(ft[pf].ft_faca >= t).mean() for t in limiares], "-", color="black", lw=1.6, label="YOLOv8n ajustado")
    ax.set_title("Faca", fontsize=9)
    ax.set_xlabel("Alarme falso (quadros normais)")
    ax.set_ylabel("Revocação")
    ax.legend(frameon=False, fontsize=6.5, loc="lower right")

    ax = eixos[1]
    taus = np.linspace(0, 3, 301)
    pos, neg = zs.rotulo.eq("ENFORCAR"), negativos(zs)
    for p, (cor, ls) in (("n", estilos["n"]), ("s", estilos["s"])):
        e = zs[f"escore_enf_{p}"]
        ax.plot([(e[neg] < t).mean() for t in taus], [(e[pos] < t).mean() for t in taus], ls, color=cor,
                label=f"Heurística (pose {p})")
        ax.plot((e[neg] < 0.6).mean(), (e[pos] < 0.6).mean(), "o", color=cor, ms=4)
    if ft is not None:
        pf, nf = ft.rotulo.eq("ENFORCAR"), negativos(ft)
        ax.plot([(ft[nf].ft_enforcar >= t).mean() for t in limiares],
                [(ft[pf].ft_enforcar >= t).mean() for t in limiares], "-", color="black", lw=1.6,
                label="YOLOv8n ajustado")
    ax.set_title("Estrangulamento (● = τ 0,6)", fontsize=9)
    ax.set_xlabel("Alarme falso (quadros normais)")
    ax.legend(frameon=False, fontsize=6.5, loc="lower right")
    virgula = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ","))
    for ax in eixos:
        ax.xaxis.set_major_formatter(virgula)
        ax.yaxis.set_major_formatter(virgula)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.02)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGS / "fig4_curvas.png", dpi=300)
    print(f"\nFigura: {FIGS / 'fig4_curvas.png'}")


if __name__ == "__main__":
    main()
