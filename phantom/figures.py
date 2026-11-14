"""Figuras. Todas se hacen desde datos reales; las pruebas no escriben en figures/."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
import pandas as pd  # noqa: E402

from . import drought  # noqa: E402

INK = "#14161a"
MUTED = "#6b7078"
DRY = "#c4572f"
GREEN = "#2f7d4f"
FUNC = "#2f5d9e"
HEAT = "#b23a48"

if any("Poppins" in f.name for f in font_manager.fontManager.ttflist):
    plt.rcParams["font.family"] = "Poppins"
plt.rcParams.update({
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.titleweight": "bold",
    "axes.titlesize": 13, "font.size": 10, "figure.dpi": 130,
})


def drought_timeline(series: dict, events: dict, path: Path) -> None:
    fig, axes = plt.subplots(len(events), 1, figsize=(12, 3.3 * len(events)), sharex=True)
    for ax, (reg, ev) in zip(axes, events.items()):
        p = series[f"imerg_precip_{reg}"].values
        s3 = drought.spi(p, 3)
        soil = drought.standardized_anomaly(series[f"gldas_rootmoist_{reg}"].values)
        ax.bar(s3.index, s3.clip(upper=0), width=25, color=DRY, alpha=0.85, label="SPI-3 negativo (IMERG)")
        ax.bar(s3.index, s3.clip(lower=0), width=25, color="#d9dadc", label="SPI-3 positivo")
        ax.plot(soil.index, soil, color=INK, lw=1.1, label="Humedad zona raíces, z (GLDAS)")
        for _, e in ev.iterrows():
            ax.axvspan(e["inicio"], e["fin"] + pd.offsets.MonthEnd(0), color=DRY, alpha=0.12, lw=0)
        ax.axhline(-1, color=DRY, lw=0.8, ls="--")
        ax.axhline(0, color=MUTED, lw=0.6)
        ax.set_title({"noroeste": "Montecristi (Línea Noroeste)", "jaragua": "Jaragua"}.get(reg, reg), loc="left")
        ax.set_ylabel("índice estandarizado")
    axes[0].legend(loc="lower left", ncol=3, frameon=False, fontsize=8)
    axes[-1].set_xlabel("Franjas: sequías usadas (SPI-3 ≤ −1 durante 2+ meses). Datos: NASA GPM IMERG V07, GLDAS Noah 2.1, vía Giovanni.")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def event_panel(pid: str, start, end, stop, ndvi_z: pd.Series, funcs: dict, path: Path) -> None:
    start, end, stop = map(pd.Timestamp, (start, end, stop))
    lo, hi = start - pd.Timedelta(days=180), stop + pd.Timedelta(days=60)
    fig, ax = plt.subplots(figsize=(11, 4))
    win = lambda s: s[(s.index >= lo) & (s.index <= hi)].dropna()  # noqa: E731
    ax.plot(win(ndvi_z).index, win(ndvi_z), color=GREEN, lw=2, marker="o", ms=3, label="Se ve: NDVI (z)")
    colors = {"gpp_modelo": FUNC, "lst_menos_aire": HEAT}
    labels = {"gpp_modelo": "GPP MOD17 (modelo, z)", "lst_menos_aire": "Dosel frío vs. aire (−z de LST − T aire)"}
    for k, z in funcs.items():
        ax.plot(win(z).index, win(z), color=colors.get(k, INK), lw=1.4, label=labels.get(k, k))
    ax.axvspan(start, end, color=DRY, alpha=0.12, lw=0, label="Sequía (SPI-3)")
    ax.axhline(-1.0, color=MUTED, lw=0.8, ls="--")
    ax.axhline(0, color=MUTED, lw=0.5)
    ax.set_title(f"{pid}: sequía {start:%Y-%m} a {end:%Y-%m}", loc="left")
    ax.set_ylabel("anomalía estandarizada (negativo = peor)")
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
