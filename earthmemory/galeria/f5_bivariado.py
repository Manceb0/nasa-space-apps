"""Pieza 5 · Coroplético bivariado 3 × 3 en la rejilla 0.1°: sensibilidad de la decisión de sequía al producto
(tasa condicional de cambio, SPI-3 ≤ −1, 4 productos) × distancia a la estación GHCN-D activa más cercana.

Datos: results/auditoria/donde_medir_prototipo.csv (443 celdas 0.1° con ≥ 25 % de RD), PROTOTIPO como en la auditoría.
Clases por terciles de cada variable. Paleta: claro = Stevens (sustractiva); oscuro = mezcla aditiva sobre el fondo
(luminosidad monótona en ambos ejes).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection

from . import datos as D
from .estilo import SLIDE, cabecera, entrada, guardar, lienzo, pie, procedencia, theme_list

NOMBRE = "05_bivariate_where_to_measure"
STEVENS = [["#e8e8e8", "#ace4e4", "#5ac8c8"],   # fila = tercil de distancia (0 cerca), col = tercil de cambio
           ["#dfb0d6", "#a5add3", "#5698b9"],
           ["#be64ac", "#8c62aa", "#3b4994"]]


def paleta(t):
    if t["name"] == "light":
        return STEVENS
    base = np.array([0.17, 0.19, 0.22])
    c1 = np.array([0.00, 0.50, 0.56])    # cambio de decisión → turquesa
    c2 = np.array([0.72, 0.17, 0.46])    # distancia → magenta
    return [[tuple(np.clip(base + (j / 2) * c1 + (i / 2) * c2, 0, 1)) for j in range(3)] for i in range(3)]


def cargar():
    d = pd.read_csv(D.R_AUD / "donde_medir_prototipo.csv")
    f = d["tasa_cambio_condicional_spi3"]
    s = d["dist_estacion_ghcn_activa_km"]
    qf = np.nanquantile(f, [1 / 3, 2 / 3])
    qs = np.nanquantile(s, [1 / 3, 2 / 3])
    d["cf"] = np.digitize(f, qf)
    d["cs"] = np.digitize(s, qs)
    st = pd.read_csv(D.R_AUD / "estaciones_meta.csv")
    act = st[(st["red"] == "GHCN-Daily") & (st["activa_2024"] == True)]  # noqa: E712
    return d, qf, qs, act


def dibujar(t, d, qf, qs, act):
    fig = lienzo(t, SLIDE)
    pal = paleta(t)
    ax = fig.add_axes([0.33, 0.05, 0.66, 0.86])
    patches, cols = [], []
    for _, r in d.iterrows():
        patches.append(Rectangle((r["lon"] - 0.05, r["lat"] - 0.05), 0.1, 0.1))
        cols.append(pal[int(r["cs"])][int(r["cf"])])
    ax.add_collection(PatchCollection(patches, facecolor=cols, edgecolor=cols, linewidth=0.3, zorder=2))
    for _, rings in D.adm1_rings():
        for e in rings:
            ax.plot(e[:, 0], e[:, 1], color=t["bg"], lw=0.8, zorder=3, alpha=0.55)
            ax.plot(e[:, 0], e[:, 1], color=t["ink"], lw=0.3, zorder=3.1, alpha=0.45)
    ax.scatter(act["lon"], act["lat"], marker="^", s=70, color=t["ink"], edgecolors=t["bg"], linewidths=0.9, zorder=5)
    for _, r in act.iterrows():
        e_ = r["lon"] > -68.8
        ax.text(r["lon"] + (-0.06 if e_ else 0.05), r["lat"] + 0.06, r["nombre"], fontsize=8, color=t["ink"], zorder=6,
                ha="right" if e_ else "left",
                bbox=dict(boxstyle="square,pad=0.1", fc=t["bg"], ec="none", alpha=0.6))
    ax.set_xlim(-72.1, -68.25)
    ax.set_ylim(17.45, 20.0)
    ax.set_aspect(1 / np.cos(np.radians(18.8)))
    ax.axis("off")
    ax.text(-68.3, 17.55, "PROTOTYPE", ha="right", va="bottom", fontsize=16, fontweight="bold", color=t["muted"],
            alpha=0.9)
    # leyenda cuadrada 3 × 3
    lg = fig.add_axes([0.085, 0.13, 0.115, 0.115 * 13.333 / 7.5])
    for i in range(3):
        for j in range(3):
            lg.add_patch(Rectangle((j, i), 1, 1, fc=pal[i][j], ec=t["bg"], lw=1.2))
    lg.set_xlim(0, 3)
    lg.set_ylim(0, 3)
    lg.set_aspect("equal")
    lg.set_xticks([0, 1, 2, 3])
    lg.set_xticklabels(["", f"{qf[0] * 100:.0f}%", f"{qf[1] * 100:.0f}%", ""], fontsize=8.5)
    lg.set_yticks([0, 1, 2, 3])
    lg.set_yticklabels(["", f"{qs[0]:.0f} km", f"{qs[1]:.0f} km", ""], fontsize=8.5)
    lg.tick_params(length=0, colors=t["muted"])
    for s_ in lg.spines.values():
        s_.set_visible(False)
    lg.set_xlabel("decision flips with product →", fontsize=9.5, color=t["ink"], labelpad=4)
    lg.set_ylabel("distance to an active station →", fontsize=9.5, color=t["ink"], labelpad=4)
    n_top = int(((d["cf"] == 2) & (d["cs"] == 2)).sum())
    top = d[(d["cf"] == 2) & (d["cs"] == 2)]["provincia"].value_counts()
    cabecera(fig, t, "Where doubt is high\nand gauges are far", "", x=0.035, y=0.93, ts=26)
    fig.text(0.035, 0.73,
             "Each 0.1° cell (~11 km) combines two audit\nresults: how often the drought call flips with\n"
             "the rainfall product (SPI-3 ≤ −1, four products)\nand how far the nearest active GHCN-Daily\n"
             "station is. Classes are terciles of each.", fontsize=11, color=t["muted"], va="top", linespacing=1.45)
    fig.text(0.035, 0.52, f"{n_top} cells", fontsize=24, fontweight="bold", color=t["ink"], va="bottom")
    fig.text(0.035, 0.51, "in the top-right class (high flip rate, far\nfrom a station), mostly in "
             + ", ".join(top.index[:2]) + "\nand " + top.index[2] + ".", fontsize=10.2, color=t["muted"], va="top", linespacing=1.35)
    pie(fig, t, "Data: results/auditoria/donde_medir_prototipo.csv (IMERG V07 · CHIRPS v2.0 · GLDAS-2.1 · MERRA-2/POWER;\n"
                "GHCN-Daily stations active in 2024, ▲) · geoBoundaries ADM1. PROTOTYPE: does not say where stations\n"
                "should go (missing: site access, exposure, population, the ONAMET/INDRHI network).  ·  Analysis: Stellar "
                "Horizons, NASA Space Apps 2026", x=0.035, y=0.02, size=7.4)
    return fig, n_top, top


def run(temas=None) -> dict:
    d, qf, qs, act = cargar()
    assert len(d) == 443
    files = []
    n_top = top = None
    for t in theme_list(temas):
        fig, n_top, top = dibujar(t, d, qf, qs, act)
        files += guardar(fig, NOMBRE, t, "Bivariate 3x3 choropleth (0.1 deg): drought-decision flip rate x distance to the "
                         "nearest active GHCN-Daily station. Prototype.", "results/auditoria/donde_medir_prototipo.csv")
    tab = pd.crosstab(d["cs"], d["cf"])
    numeros = {"n_celdas": len(d), "terciles_tasa_cambio": list(qf), "terciles_distancia_km": list(qs),
               "n_celdas_por_clase_dist_x_cambio": tab.to_dict(), "n_celdas_clase_alta_alta": n_top,
               "provincias_clase_alta_alta": top.to_dict(), "estaciones_activas": act["nombre"].tolist()}
    alt_en = (f"Map of the Dominican Republic in 443 squares of 0.1 degrees, coloured with a 3-by-3 bivariate palette: one "
              f"axis is how often the drought decision flips with the rainfall product, the other the distance to the "
              f"nearest active GHCN-Daily station (triangles). {n_top} cells fall in the high-high class, mostly in "
              f"{', '.join(top.index[:3])}. Labelled PROTOTYPE.")
    alt_es = (f"Mapa de la RD en 443 cuadros de 0.1° con paleta bivariada 3 × 3: un eje es cuánto cambia la decisión de "
              f"sequía según el producto, el otro la distancia a la estación GHCN-Daily activa más cercana (triángulos). "
              f"{n_top} celdas en la clase alta-alta, sobre todo en {', '.join(top.index[:3])}. Marcado PROTOTIPO.")
    procedencia(NOMBRE, "Where doubt is high and gauges are far (prototype)", "Donde la duda es alta y los pluviómetros "
                "están lejos (prototipo)", files,
                [entrada("results/auditoria/donde_medir_prototipo.csv", "tasa_cambio_condicional_spi3, dist_estacion_ghcn_activa_km"),
                 entrada("results/auditoria/estaciones_meta.csv", "estaciones GHCN-Daily activas en 2024"),
                 entrada("data/nacional/limites/geoBoundaries-DOM-ADM1.geojson", "límites ADM1")],
                "Terciles (np.nanquantile 1/3, 2/3) de cada variable; clase = (tercil distancia, tercil cambio).",
                numeros, alt_en, alt_es, ["PROTOTIPO: no prueba dónde deben ir estaciones (ver AUDITORIA_CONFIANZA.md §6)."])
    return {"archivos": files, "numeros": numeros}
