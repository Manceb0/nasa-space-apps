"""Figura del recálculo: mapas de clase de confianza antes y después de quitar el escalón de IMERG (A_frec) y la
sensibilidad al año de corte. Datos: results/tendencias/tendencias_celdas.csv (P0 publicado) y
results/tropical/recalculo/. Sin barras ni pasteles."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..galeria.estilo import OI, TEMAS, aplicar, cabecera, pie  # noqa: E402
from .figuras import _outline  # noqa: E402

RES = Path("results/tropical/recalculo")
OUT = Path("figures/tropical")
COL = {"robusta": "#0072B2", "consistente": "#56B4E9", "en disputa": "#D55E00"}
LAB = {"robusta": "robust (both agree, both significant)", "consistente": "consistent (same sign, one significant)",
       "en disputa": "in dispute (opposite signs, one significant)"}
PANELES = [("SDII", "anual", "Rain per wet day (SDII)"),
           ("RACHAS15", "seca", "Dry spells ≥ 15 d, Dec-Apr")]


def _mapa(ax, df, t, titulo):
    none = df[~df["clase_confianza"].isin(COL)]
    ax.scatter(none["lon"], none["lat"], marker="s", s=17, c=t["none"], linewidths=0)
    for k, c in COL.items():
        d = df[df["clase_confianza"] == k]
        ax.scatter(d["lon"], d["lat"], marker="s", s=17, c=c, linewidths=0)
    _outline(ax, t)
    n = df["clase_confianza"].value_counts()
    ax.set_title(f"{titulo}\n{n.get('en disputa', 0)} in dispute · {n.get('consistente', 0)} consistent · "
                 f"{n.get('robusta', 0)} robust", loc="left", fontsize=9.5, color=t["ink"])
    ax.set_aspect(1 / np.cos(np.radians(18.8)))
    ax.set_xlim(-72.1, -68.2)
    ax.set_ylim(17.5, 20.1)
    ax.axis("off")


def figura(t):
    aplicar(t)
    orig = pd.read_csv("results/tendencias/tendencias_celdas.csv")
    corr = pd.read_csv(RES / "tendencias_celdas_A_frec.csv")
    sens = pd.read_csv(RES / "sensibilidad_corte.csv")
    nat = pd.read_csv(RES / "nacional_IMERG_foco.csv")
    fig = plt.figure(figsize=(13.333, 7.5), facecolor=t["bg"])
    gs = fig.add_gridspec(2, 3, left=0.04, right=0.98, top=0.72, bottom=0.17, hspace=0.35, wspace=0.18,
                          width_ratios=[1, 1, 1.05])
    for r, (idx, per, name) in enumerate(PANELES):
        for c, (df, tag) in enumerate(((orig, "as published"), (corr, "step removed"))):
            ax = fig.add_subplot(gs[r, c])
            d = df[(df["indice"] == idx) & (df["periodo"] == per) & (df["fuente"] == "IMERG")]
            _mapa(ax, d, t, f"{'ab'[r]}{c + 1}  {name} · {tag}")
    # c) sensibilidad al año de corte
    ax = fig.add_subplot(gs[:, 2])
    s = sens[sens["corte"] != "sin corrección"].copy()
    s["corte"] = s["corte"].astype(int)
    base = int(sens.loc[sens["corte"] == "sin corrección", "disputa_anuales"].iloc[0])
    ax.plot(s["corte"], s["disputa_anuales"], color=OI["vermillion"], marker="o", lw=2)
    ax.axhline(base, color=t["muted"], ls="--", lw=1)
    ax.text(2006.2, base * 0.97, f"no correction: {base}", color=t["muted"], fontsize=8.5, va="top")
    ax.axvline(2014, color=OI["yellow"], lw=1.2)
    ax.text(2014.2, base * 0.35, "cut used\n(step found\nin 2013-10)", color=OI["yellow"], fontsize=8.5)
    ax.set_yscale("symlog", linthresh=10)
    ax.set_ylim(0, base * 1.4)
    ax.set_xlabel("year the IMERG step is assumed to start", fontsize=9)
    ax.set_ylabel("cell-index pairs in dispute (annual frequency indices)", fontsize=9)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_title("c   Caution: almost any cut year removes the disputes.\n"
                 "     The correction alone does not date the step;\n"
                 "     the change-point test and the gauges do.", loc="left", fontsize=9.5, color=t["ink"])
    # leyenda
    for k, (lab, c) in enumerate([(LAB[x], COL[x]) for x in COL] + [("no detectable signal", t["none"])]):
        fig.text(0.04 + k * 0.235, 0.105, "■", color=c, fontsize=13, va="center")
        fig.text(0.053 + k * 0.235, 0.105, lab, color=t["ink"], fontsize=8.5, va="center")
    g = nat.set_index(["indice", "periodo", "variante"])
    sd0, sd1 = g.loc[("SDII", "anual", "original")], g.loc[("SDII", "anual", "A_frec")]
    rs0, rs1 = g.loc[("RACHAS15", "seca", "original")], g.loc[("RACHAS15", "seca", "A_frec")]
    cabecera(fig, t, "Remove one step in the satellite record and most 'disputes' disappear.",
             f"IMERG's national trends fall apart once its 2013 counting step is removed: rain intensity "
             f"{sd0['pendiente_pct_decada']:+.1f} %/decade (p = {sd0['p']:.3f}) → {sd1['pendiente_pct_decada']:+.1f} % "
             f"(p = {sd1['p']:.2f});\ndry-season dry spells {rs0['pendiente_pct_decada']:+.1f} % (p < 0.001) → "
             f"{rs1['pendiente_pct_decada']:+.1f} % (p = {rs1['p']:.2f}). The two products were not describing two "
             "different climates.\nOnly the frequency-based indices are corrected; rain amounts are left untouched.",
             ts=19, ss=10.5)
    pie(fig, t, "Same P0 engine (Theil-Sen, Hamed-Rao Mann-Kendall, BH-FDR at q = 0.10 (2α, Wilks 2016), 442 cells, 2001-2024). Correction: per cell "
               "and index, the IMERG − CHIRPS mean difference\nafter vs before 2014 is subtracted from IMERG from 2014 on "
               "(CHIRPS as reference, supported by 4 GHCN-Daily gauges). Without a reference series the step and the trend\n"
               "cannot be separated (variant B fabricates trends). NASA GPM IMERG V07 · CHIRPS v2.0 · Stellar Horizons · "
               "NASA Space Apps 2026.", y=0.012)
    base_p = OUT / f"08_after_the_correction_{t['name']}"
    fig.savefig(base_p.with_suffix(".png"), dpi=200, facecolor=t["bg"],
                metadata={"Software": "matplotlib; figure code written with AI assistance (Claude), data unaltered"})
    fig.savefig(base_p.with_suffix(".pdf"), facecolor=t["bg"])
    plt.close(fig)
    return base_p


def main():
    for k in ("dark", "light"):
        print(figura(TEMAS[k]))


if __name__ == "__main__":
    main()
