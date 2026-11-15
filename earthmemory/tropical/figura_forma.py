"""Figura 10: ¿tendencia o escalón? Serie nacional con los modelos, mapa de la forma por celda, fechas de escalón y
la validación con series sintéticas. Lee results/tropical/forma/. Sin barras ni pasteles."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..galeria.estilo import OI, TEMAS, aplicar, cabecera, pie  # noqa: E402
from .figuras import _outline  # noqa: E402

RES = Path("results/tropical/forma")
OUT = Path("figures/tropical")
ORD = ["sin cambio", "tendencia", "escalón", "tendencia + escalón", "indistinguibles"]


def colores(t):
    return {"sin cambio": t["none"], "tendencia": OI["blue"], "escalón": OI["vermillion"],
            "tendencia + escalón": OI["orange"], "indistinguibles": OI["purple"]}


def figura(t):
    aplicar(t)
    COL = colores(t)
    R = json.loads((RES / "resumen.json").read_text(encoding="utf-8"))
    T = pd.read_csv(RES / "celdas.csv")
    S = pd.read_csv(RES / "serie_nacional.csv", index_col=0)
    C = pd.read_csv(RES / "validacion_confusion.csv")
    N = R["nacional"]
    y = 100 * S.iloc[:, 0].to_numpy()
    x = pd.PeriodIndex(S.index, freq="M").to_timestamp()
    n = y.size

    fig = plt.figure(figsize=(13.333, 7.5), facecolor=t["bg"])
    gs = fig.add_gridspec(2, 3, left=0.06, right=0.98, top=0.75, bottom=0.17, hspace=0.5, wspace=0.28,
                          height_ratios=[1, 1.1], width_ratios=[1.15, 1, 1])
    # a) serie nacional y dos modelos
    ax = fig.add_subplot(gs[0, :])
    ax.plot(x, y, color=t["muted"], lw=0.7, alpha=0.7)
    ax.plot(x, pd.Series(y).rolling(12, center=True).mean(), color=t["ink"], lw=1.6, label="media móvil de 12 meses")
    tt = np.arange(n)
    b = np.polyfit(tt, y, 1)
    ax.plot(x, np.polyval(b, tt), color=OI["blue"], lw=2, ls="--",
            label=f"tendencia (ΔBIC {N['delta_bic_vs_mejor']['tendencia']:+.1f})")
    k = list(S.index).index(N["escalon_fecha"])
    m0, m1 = y[:k].mean(), y[k:].mean()
    ax.plot(x[:k], [m0] * k, color=OI["vermillion"], lw=2.4)
    ax.plot(x[k:], [m1] * (n - k), color=OI["vermillion"], lw=2.4,
            label=f"escalón en {N['escalon_fecha']} (mejor modelo; fecha posible {N['escalon_rango_dbic2'][0]} a "
                  f"{N['escalon_rango_dbic2'][1]})")
    ax.axhline(0, color=t["muted"], lw=0.6)
    ax.axvline(pd.Timestamp("2013-10-01"), color=OI["yellow"], lw=1, ls=":")
    ax.text(pd.Timestamp("2013-11-01"), ax.get_ylim()[1] * 0.9, "oct-2013 (Pettitt)", color=OI["yellow"],
            fontsize=8.5, va="top")
    ax.set_ylabel("IMERG − CHIRPS\n(pp de días con lluvia)", fontsize=9)
    ax.legend(loc="lower left", fontsize=8.5, frameon=False, ncol=3)
    ax.set_title("a   Serie nacional (media de 442 celdas, sin ciclo estacional). Gana el escalón, pero en 2018, "
                 "no en 2013", loc="left", fontsize=10, color=t["ink"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    # b) mapa por celda
    ax = fig.add_subplot(gs[1, 0])
    for c in ORD:
        d = T[T["clase"] == c]
        ax.scatter(d["lon"], d["lat"], marker="s", s=15, c=COL[c], linewidths=0, label=f"{c} ({len(d)})")
    _outline(ax, t)
    ax.set_aspect(1 / np.cos(np.radians(18.8)))
    ax.set_xlim(-72.1, -68.2)
    ax.set_ylim(17.5, 20.1)
    ax.axis("off")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.02), fontsize=7.5, frameon=False, ncol=3, markerscale=1.4,
              handletextpad=0.3, columnspacing=0.8)
    ax.set_title("b   Forma elegida por celda (la validación dice\n     que por celda la forma NO es fiable)",
                 loc="left", fontsize=10, color=t["ink"])
    # c) fechas de escalón (puntos apilados por año)
    ax = fig.add_subplot(gs[1, 1])
    e = T[T["clase"].isin(["escalón", "tendencia + escalón"])]
    yrs = e["fecha_escalon"].str[:4].astype(int)
    for yr, cnt in yrs.value_counts().items():
        ax.scatter([yr] * cnt, np.arange(cnt) + 1, s=9, color=OI["vermillion"], linewidths=0)
    ax.set_xlim(2001, 2025)
    ax.set_ylim(0, max(yrs.value_counts().max() + 3, 10))
    ax.axvline(2013.75, color=OI["yellow"], lw=1, ls=":")
    ax.set_ylabel("celdas", fontsize=9)
    ax.set_title(f"c   Año del escalón ({len(e)} celdas): el pico es 2018\n     "
                 f"({100 * R['max_frac_fechas_escalon_en_12_meses']:.0f} % en 12 meses), no 2013",
                 loc="left", fontsize=10, color=t["ink"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    # d) validación (matriz de confusión, ruido nacional, cambio 4,5 pp)
    ax = fig.add_subplot(gs[1, 2])
    v = C[(C["ruido"] == "nacional") & (C["cambio_total_pp"] == 4.5)].set_index("verdad")
    filas = ["sin cambio", "tendencia", "escalón", "tendencia + escalón"]
    cols = ORD
    M = v.loc[filas, cols].to_numpy()
    ax.imshow(M, cmap="Greys" if t["name"] == "light" else "gray", vmin=0, vmax=1.3, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{100 * M[i, j]:.0f}", ha="center", va="center", fontsize=8.5,
                    color=t["bg"] if M[i, j] > 0.55 else t["ink"])
    ax.set_xticks(range(len(cols)), ["sin\ncambio", "tend.", "escalón", "ambos", "indist."], fontsize=8)
    ax.set_yticks(range(len(filas)), ["sin cambio", "tendencia", "escalón", "ambos"], fontsize=8)
    ax.set_xlabel("lo que elige el método (%)", fontsize=8.5)
    ax.set_ylabel("lo que se simuló", fontsize=8.5)
    ax.set_title("d   Validación (ruido nacional, 4,5 pp):\n     tendencia → «escalón» solo el 5 %",
                 loc="left", fontsize=10, color=t["ink"])
    ac = R["acierto_forma_validacion"]
    cabecera(fig, t, "Hay un cambio en IMERG − CHIRPS, pero su forma y su fecha no se pueden fijar.",
             f"En el país gana un escalón en {N['escalon_fecha']} (ΔBIC {N['delta_bic_vs_mejor']['tendencia']:.1f} "
             "frente a la tendencia), no en 2013. Por celda, el método solo acierta la forma en el "
             f"{100 * ac['celda 4.5 pp']:.0f} % de las simulaciones\ncon un cambio de 4,5 pp: detecta que hay "
             f"cambio (en {442 - R['clases_celdas'].get('sin cambio', 0)} de 442 celdas; falsos positivos "
             f"{100 * R['falsos_cambios_validacion']['celda']:.0f} %), pero no cuál. "
             "Una deriva curva o varios saltos no se simularon.", ts=18, ss=10.5)
    pie(fig, t, "Modelos con errores AR(1) (Prais-Winsten, verosimilitud gaussiana exacta), elegidos por BIC; la fecha "
                "del escalón se busca en toda la serie y cuenta como parámetro;\n«indistinguibles» = otra forma a "
                "menos de 2 de BIC.\nValidación: 150 series sintéticas por caso con el ruido observado. Celdas "
                "vecinas no son independientes. Días ≥ 1 mm. NASA GPM IMERG V07 · CHIRPS v2.0 · Stellar Horizons.",
        y=0.012)
    base = OUT / f"10_tendencia_o_escalon_{t['name']}"
    fig.savefig(base.with_suffix(".png"), dpi=200, facecolor=t["bg"],
                metadata={"Software": "matplotlib; figure code written with AI assistance (Claude), data unaltered"})
    fig.savefig(base.with_suffix(".pdf"), facecolor=t["bg"])
    plt.close(fig)
    return base


def main():
    for k in ("dark", "light"):
        print(figura(TEMAS[k]))


if __name__ == "__main__":
    main()
