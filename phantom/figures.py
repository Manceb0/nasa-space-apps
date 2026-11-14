"""Figuras de evidencia (matplotlib). Solo datos reales; las pruebas escriben en carpetas temporales.

Reglas: un panel por variable (sin doble eje), colores Okabe-Ito con una segunda pista
(marcador, estilo de línea o posición), etiquetas directas, letras de panel, tamaño físico
fijo, PDF + PNG y un JSON de procedencia junto a cada figura. Las leyendas largas van en
figures/LEYENDAS.md, no dentro de la imagen.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import drought  # noqa: E402

# Okabe & Ito (2008), paleta segura para daltonismo
OI = {"black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73",
      "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7"}
GREY = "#9A9A9A"
LIGHT = "#E6E6E6"
MM = 1 / 25.4
WIDTH_MM = 180

RC = {
    "font.family": "DejaVu Sans",
    "font.size": 7,
    "axes.titlesize": 7,
    "axes.labelsize": 7,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#333333",
    "axes.labelcolor": "#111111",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "lines.linewidth": 0.9,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
}

REGION_NAME = {"noroeste": "Montecristi (Línea Noroeste)", "jaragua": "Jaragua"}


@contextmanager
def style():
    with plt.rc_context(RC):
        yield


def panel_letter(ax, letter: str, text: str = "") -> None:
    ax.text(0, 1.04, letter, transform=ax.transAxes, fontsize=8, fontweight="bold", va="bottom", ha="left")
    if text:
        ax.text(0.03, 1.04, text, transform=ax.transAxes, fontsize=7, va="bottom", ha="left")


def save(fig, stem: Path, provenance: dict) -> list[str]:
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        p = stem.with_suffix(f".{ext}")
        fig.savefig(p, **kw)  # sin bbox_inches="tight": se conserva el tamaño físico
        out.append(p.name)
    w, h = fig.get_size_inches()
    prov = {"archivos": out, "tamano_mm": [round(w * 25.4, 1), round(h * 25.4, 1)], **provenance}
    stem.with_suffix(".json").write_text(json.dumps(prov, ensure_ascii=False, indent=2, default=str), encoding="utf-8", newline="\n")
    plt.close(fig)
    return out


def _year_axis(ax) -> None:
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_minor_locator(mdates.YearLocator(1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlim(pd.Timestamp("2000-11-01"), pd.Timestamp("2025-02-01"))


def fig_droughts(series: dict, events: dict, stem: Path) -> list[str]:
    """Fig. 1: SPI-3 (IMERG) y humedad de la zona de raíces (GLDAS), un panel cada uno, por región."""
    with style():
        fig, axes = plt.subplots(4, 1, figsize=(WIDTH_MM * MM, 150 * MM), sharex=True, layout="constrained",
                                 gridspec_kw={"height_ratios": [1.25, 1, 1.25, 1]})
        letters = iter("abcd")
        for k, reg in enumerate(("noroeste", "jaragua")):
            ax_s, ax_m = axes[2 * k], axes[2 * k + 1]
            s3 = drought.spi(series[f"imerg_precip_{reg}"].values, 3)
            soil = drought.standardized_anomaly(series[f"gldas_rootmoist_{reg}"].values)
            ev = events[reg]

            neg = s3.where(s3 < 0)
            pos = s3.where(s3 >= 0)
            ax_s.bar(neg.index, neg, width=24, color=OI["vermillion"], linewidth=0)
            ax_s.bar(pos.index, pos, width=24, color=GREY, linewidth=0)
            ax_s.axhline(0, color="#333333", lw=0.5)
            ax_s.axhline(-1, color="#333333", lw=0.6, ls=(0, (4, 2)))
            ax_s.text(0.998, -1.08, "SPI = −1", transform=ax_s.get_yaxis_transform(), va="top", ha="right", fontsize=6.5)
            lo = -3.4
            for _, e in ev.iterrows():
                ax_s.plot([e["inicio"], e["fin"] + pd.offsets.MonthEnd(0)], [lo + 0.25] * 2, color="#000000",
                          lw=2.2, solid_capstyle="butt")
            for _, e in ev.nsmallest(3, "severidad").iterrows():
                y0, y1 = e["inicio"].year, e["fin"].year
                ax_s.text(e["inicio"], lo + 0.45, f"{y0}" if y0 == y1 else f"{y0}–{str(y1)[2:]}", fontsize=6.5,
                          ha="left", va="bottom")
            ax_s.set_ylim(lo, 3.2)
            ax_s.set_ylabel("SPI-3")
            panel_letter(ax_s, next(letters), f"{REGION_NAME[reg]}: lluvia acumulada a 3 meses (IMERG V07)")

            ax_m.plot(soil.index, soil, color="#000000", lw=0.8)
            ax_m.axhline(0, color="#333333", lw=0.5)
            ax_m.axhline(-1, color="#333333", lw=0.6, ls=(0, (4, 2)))
            ax_m.text(0.998, -1.08, "z = −1", transform=ax_m.get_yaxis_transform(), va="top", ha="right", fontsize=6.5)
            ax_m.set_ylim(-3.2, 3.8)
            ax_m.set_ylabel("z")
            panel_letter(ax_m, next(letters), f"{REGION_NAME[reg]}: humedad del suelo en la zona de raíces "
                                              "(GLDAS Noah 2.1), anomalía estandarizada por mes")
        _year_axis(axes[-1])
        axes[-1].set_xlabel("Año")
    return save(fig, stem, {
        "datos": ["data/giovanni/imerg_precip_noroeste.csv", "data/giovanni/imerg_precip_jaragua.csv",
                  "data/giovanni/gldas_rootmoist_noroeste.csv", "data/giovanni/gldas_rootmoist_jaragua.csv"],
        "transformaciones": ["SPI-3: gamma por mes calendario con probabilidad de cero (phantom.drought.spi)",
                             "z de humedad: (x - media del mes) / desviación del mes, 2001-2024"],
        "marcas": "barras negras bajo el eje = eventos SPI-3 <= -1 durante 2+ meses; años = los 3 más severos",
        "faltantes": "SPI-3 no existe en los 2 primeros meses (ventana de 3 meses); se dejan vacíos",
    })


def fig_criteria(catalog: pd.DataFrame, stem: Path) -> list[str]:
    """Fig. 2: periodos secos según cada criterio, para ver dónde coinciden lluvia y suelo."""
    crit_order = [("SPI-3", "SPI-3 ≤ −1", OI["vermillion"]), ("SPI-6", "SPI-6 ≤ −1", OI["orange"]),
                  ("humedad", "Suelo z ≤ −1", OI["blue"])]
    with style():
        fig, axes = plt.subplots(2, 1, figsize=(WIDTH_MM * MM, 62 * MM), sharex=True, layout="constrained")
        for ax, reg, letter in zip(axes, ("noroeste", "jaragua"), "ab"):
            sub = catalog[catalog["region"] == reg]
            for row, (key, label, color) in enumerate(crit_order):
                y = len(crit_order) - 1 - row
                ev = sub[sub["criterio"].str.startswith(key)]
                spans = [(mdates.date2num(r["inicio"]),
                          mdates.date2num(r["fin"] + pd.offsets.MonthEnd(0)) - mdates.date2num(r["inicio"]))
                         for _, r in ev.iterrows()]
                ax.broken_barh(spans, (y - 0.32, 0.64), facecolors=color, linewidth=0)
                ax.text(-0.005, y, label, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=6.5)
            ax.set_yticks([])
            ax.spines["left"].set_visible(False)
            ax.set_ylim(-0.6, len(crit_order) - 0.4)
            ax.xaxis.grid(True, which="major", color=LIGHT, lw=0.5)
            ax.set_axisbelow(True)
            panel_letter(ax, letter, REGION_NAME[reg])
        _year_axis(axes[-1])
        axes[-1].set_xlabel("Año")
    return save(fig, stem, {
        "datos": "results/sequias_catalogo.csv",
        "criterios": [c[1] for c in crit_order],
        "nota": "Una racha cuenta si dura 2+ meses. GLDAS recibe lluvia como entrada: coincidir no es validación independiente.",
    })


def _smooth(z: pd.Series) -> pd.Series:
    return z.dropna().sort_index().rolling(3, center=True, min_periods=1).median()


def fig_event(pid: str, start, end, stop, signals: dict, recoveries: dict, stem: Path,
              threshold: float = -1.0) -> list[str]:
    """Una sequía, tres paneles alineados: NDVI, GPP (modelo), dosel vs. aire. Puntos = observaciones
    válidas; línea = mediana móvil de 3; línea vertical = recuperación detectada."""
    start, end, stop = map(pd.Timestamp, (start, end, stop))
    lo, hi = start - pd.Timedelta(days=200), stop + pd.Timedelta(days=60)
    spec = [("ndvi", "NDVI (se ve)", OI["green"], "o"),
            ("gpp_modelo", "GPP MOD17 (modelo)", OI["blue"], "s"),
            ("lst_menos_aire", "Dosel vs. aire (−z)", OI["vermillion"], "^")]
    with style():
        fig, axes = plt.subplots(3, 1, figsize=(WIDTH_MM * MM, 110 * MM), sharex=True, sharey=True,
                                 layout="constrained")
        for ax, (key, label, color, marker), letter in zip(axes, spec, "abc"):
            z = signals[key]
            z = z[(z.index >= lo) & (z.index <= hi)].dropna()
            ax.axvspan(start, end, color=LIGHT, lw=0)
            ax.axhline(0, color="#333333", lw=0.5)
            ax.axhline(threshold, color="#333333", lw=0.6, ls=(0, (4, 2)))
            ax.plot(z.index, z, ls="none", marker=marker, ms=2.4, mfc="white", mec=color, mew=0.7)
            sm = _smooth(z)
            ax.plot(sm.index, sm, color=color, lw=1.1)
            rec = recoveries.get(key)
            if rec is not None and not pd.isna(rec):
                ax.axvline(rec, color="#000000", lw=0.7, ls=(0, (1, 1.5)))
                ax.text(rec, 0.04, f" vuelve: {pd.Timestamp(rec):%Y-%m-%d}", transform=ax.get_xaxis_transform(),
                        va="bottom", ha="left", fontsize=6.5)
            else:
                ax.text(0.99, 0.04, f"sin recuperación antes de {stop:%Y-%m-%d}", transform=ax.transAxes,
                        va="bottom", ha="right", fontsize=6.5)
            ax.set_ylabel("z")
            panel_letter(ax, letter, label)
        axes[0].text(start, 0.03, " sequía (SPI-3)", transform=axes[0].get_xaxis_transform(), fontsize=6.5,
                     va="bottom", ha="left", color="#333333")
        axes[-1].xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        axes[-1].set_xlim(lo, hi)
    return save(fig, stem, {
        "punto": pid, "evento": [start, end], "fin_ventana": stop,
        "transformaciones": ["z robusto por época del año (mediana, 1.4826 MAD), >= 8 años por época",
                             "LST - T2M MERRA-2 del mes, invertido (negativo = dosel más caliente)",
                             "línea = mediana móvil de 3 observaciones válidas"],
        "umbral_recuperacion": threshold,
        "recuperaciones": recoveries,
    })


def fig_sensitivity(sens: pd.DataFrame, stem: Path, resolution_days: int = 32) -> list[str]:
    """Δt de cada combinación de supuestos, por evento y señal. Banda gris = ±32 días (precisión)."""
    ok = sens[sens["estado"] == "ambos_recuperados"].copy()
    ok["evento"] = ok["id"] + "  " + pd.to_datetime(ok["evento_inicio"]).dt.strftime("%Y-%m")
    events = sorted(ok["evento"].unique())
    funcs = [("gpp_modelo", "GPP MOD17 (modelo)", OI["blue"], -0.18),
             ("lst_menos_aire", "Dosel vs. aire", OI["vermillion"], 0.18)]
    markers = {"ndvi": "o", "evi": "D"}
    with style():
        h = max(45, 9 * len(events) + 25)
        fig, ax = plt.subplots(figsize=(WIDTH_MM * MM, h * MM), layout="constrained")
        ax.axvspan(-resolution_days, resolution_days, color=LIGHT, lw=0)
        ax.axvline(0, color="#333333", lw=0.6)
        rng = np.random.default_rng(0)
        for fkey, flabel, color, off in funcs:
            for gkey, mk in markers.items():
                d = ok[(ok["funcion"] == fkey) & (ok["verde"] == gkey)]
                y = d["evento"].map({e: i for i, e in enumerate(events)}) + off + rng.uniform(-0.06, 0.06, len(d))
                ax.plot(d["dt_dias"], y, ls="none", marker=mk, ms=3, mfc="white", mec=color, mew=0.8)
        ax.set_yticks(range(len(events)), events)
        ax.set_ylim(-0.6, len(events) - 0.4)
        ax.invert_yaxis()
        ax.set_xlabel("Δt = recuperación de la función − recuperación del verdor (días)")
        ax.text(0.01, 1.01, "azul: GPP MOD17 (modelo) · bermellón: dosel vs. aire · círculo: NDVI · rombo: EVI · "
                f"gris: ±{resolution_days} d", transform=ax.transAxes, fontsize=6.5, va="bottom")
    return save(fig, stem, {
        "datos": "results/sensibilidad.csv",
        "combinaciones": "verdor {NDVI, EVI} × umbral {−1.5, −1, −0.5} × persistencia {2, 3, 4}",
        "nota": "solo combinaciones donde ambas señales se recuperaron; desplazamiento vertical pequeño para separar puntos (semilla 0)",
    })
