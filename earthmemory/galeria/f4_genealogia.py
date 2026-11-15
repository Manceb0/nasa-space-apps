"""Pieza 4 · «Genealogy of the data»: de qué insumos cuelga cada producto (diagrama aluvial con curvas de Bézier).

Fuente única de verdad: results/auditoria/procedencia_insumos_compartidos.csv (insumo × producto, V = verificado en la
documentación oficial, I = inferido) + procedencia_matriz.csv (nombres y clases). Se resaltan los insumos que
alimentan a dos o más de los cuatro productos de lluvia usados en la decisión de sequía (IMERG, CHIRPS, lluvia de
forzamiento GLDAS, MERRA-2): por eso su acuerdo no es una validación independiente.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath

from . import datos as D
from .estilo import OI, SLIDE, cabecera, entrada, guardar, lienzo, pie, procedencia, theme_list

NOMBRE = "04_genealogy_of_the_data"
FUENTE = ("Source: Stellar Horizons provenance audit (results/auditoria/procedencia_insumos_compartidos.csv), verified "
          "2026-11-14 against official ATBDs, READMEs and user guides\n"
          "(IMERG V07, CHIRPS v2.0, GLDAS-2.1, SMAP L4 V008, "
          "SMAP L3 V6, MERRA-2/POWER, TerraClimate v1.1, GEOGLOWS v2, MODIS, GRACE-FO, GHCN-D/GSOD).")
INSUMO_EN = {
    "Pluviómetros GTS/SYNOP": ("Rain gauges on the WMO GTS (SYNOP)", "gauge"),
    "GPCC": ("GPCC gauge analysis", "gauge"),
    "GHCN/GSOD": ("GHCN / GSOD station archives", "gauge"),
    "CPC Unified": ("CPC Unified gauge analysis", "gauge"),
    "IR geoestacionario": ("Geostationary infrared", "sat"),
    "Microondas pasivas": ("Passive microwave radiometers", "sat"),
    "Tb SMAP banda L": ("SMAP L-band brightness temperature", "sat"),
    "Reflectancia MODIS": ("MODIS reflectance", "sat"),
    "Gravimetría GRACE": ("GRACE gravimetry", "sat"),
    "Sistema GEOS / MERRA-2": ("NASA GEOS system / MERRA-2", "model"),
    "ERA5": ("ECMWF ERA5 reanalysis", "model"),
    "NCEP (CFSv2 / GDAS)": ("NCEP CFSv2 / GDAS", "model"),
}
PRODUCTO_EN = {"IMERG": "GPM IMERG V07 Final", "CHIRPS": "CHIRPS v2.0", "GLDAS_forzamiento": "GLDAS-2.1 forcing rain",
               "MERRA2": "MERRA-2 (NASA POWER)", "Estaciones": "GHCN-D / GSOD stations", "SMAP_L4": "SMAP L4 soil moisture",
               "SMAP_L3": "SMAP L3 soil moisture", "TerraClimate": "TerraClimate v1.1", "GEOGLOWS": "GEOGLOWS v2 river flow",
               "MOD13A3": "MODIS MOD13A3 NDVI", "MOD17": "MODIS MOD17 NPP", "GRACE": "GRACE / GRACE-FO"}
ORDEN_P = ["IMERG", "CHIRPS", "GLDAS_forzamiento", "MERRA2", "Estaciones", "SMAP_L4", "SMAP_L3", "TerraClimate",
           "GEOGLOWS", "MOD13A3", "MOD17", "GRACE"]
SEQUIA = ["IMERG", "CHIRPS", "GLDAS_forzamiento", "MERRA2"]
GRUPO_EN = {"gauge": "Rain gauges", "sat": "Satellite sensors", "model": "Models & reanalyses"}


def cargar():
    m = pd.read_csv(D.R_AUD / "procedencia_insumos_compartidos.csv").set_index("insumo").fillna("")
    assert set(m.columns) == set(ORDEN_P), m.columns
    assert set(m.index) == set(INSUMO_EN), m.index
    orden_i = [k for g in ("gauge", "sat", "model") for k in INSUMO_EN if INSUMO_EN[k][1] == g]
    m = m.loc[orden_i, ORDEN_P]
    edges = [(i, p, m.loc[i, p]) for i in m.index for p in m.columns if m.loc[i, p] in ("V", "I")]
    compartidos = [i for i in m.index if sum(m.loc[i, p] in ("V", "I") for p in SEQUIA) >= 2]
    return m, edges, compartidos


def bezier(x0, y0, x1, y1):
    xm = (x0 + x1) / 2
    verts = [(x0, y0), (xm, y0), (xm, y1), (x1, y1)]
    return MPath(verts, [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4])


def dibujar(t, m, edges, compartidos):
    fig = lienzo(t, SLIDE)
    ax = fig.add_axes([0.03, 0.095, 0.94, 0.655])
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.6, len(ORDEN_P) - 0.4)
    ax.invert_yaxis()
    ax.axis("off")
    XL, XR = 0.30, 0.70
    yi = {k: n + (0.35 if INSUMO_EN[k][1] == "sat" else 0) + (0.7 if INSUMO_EN[k][1] == "model" else 0) - 0.35
          for n, k in enumerate(m.index)}
    yp = {k: n + (0.35 if n >= 4 else 0) - 0.175 for n, k in enumerate(ORDEN_P)}
    grey = t["muted"]
    # aristas: primero las no resaltadas
    def hl(i, p):
        return i in compartidos and p in SEQUIA
    for i, p, st in sorted(edges, key=lambda e: hl(e[0], e[1])):
        h = hl(i, p)
        col = OI["vermillion"] if h else grey
        alpha = 0.95 if h else 0.45
        lw = 2.0 if h else 1.1
        if p == "GRACE":
            col, alpha, lw = OI["green"], 0.95, 2.0
        patch = PathPatch(bezier(XL + 0.012, yi[i], XR - 0.012, yp[p]), fc="none", ec=col, lw=lw, alpha=alpha,
                          ls=(0, (4, 2.2)) if st == "I" else "-", zorder=3 if h else 2, capstyle="round")
        ax.add_patch(patch)
    # nodos
    deg_i = {i: sum(1 for e in edges if e[0] == i) for i in m.index}
    deg_p = {p: sum(1 for e in edges if e[1] == p) for p in ORDEN_P}
    for i in m.index:
        sh = i in compartidos
        ax.scatter([XL], [yi[i]], s=26 + 16 * deg_i[i], color=OI["vermillion"] if sh else t["muted"], zorder=5,
                   edgecolors=t["bg"], linewidths=1.2)
        ax.text(XL - 0.02, yi[i], INSUMO_EN[i][0], ha="right", va="center", fontsize=10.4,
                color=t["ink"] if sh else t["muted"], fontweight="bold" if sh else "normal")
        ax.text(XL + 0.022, yi[i] - 0.28, f"→ {deg_i[i]}", ha="left", va="center", fontsize=7.5, color=t["muted"])
    for p in ORDEN_P:
        dr = p in SEQUIA
        c = t["ink"] if dr else t["muted"]
        if p == "GRACE":
            c = OI["green"]
        ax.scatter([XR], [yp[p]], s=26 + 16 * deg_p[p], color=c, zorder=5, edgecolors=t["bg"], linewidths=1.2)
        ax.text(XR + 0.02, yp[p], PRODUCTO_EN[p], ha="left", va="center", fontsize=10.4, color=c,
                fontweight="bold" if dr else "normal")
    # grupos de insumos
    for g in ("gauge", "sat", "model"):
        ks = [k for k in m.index if INSUMO_EN[k][1] == g]
        y0, y1 = yi[ks[0]], yi[ks[-1]]
        ax.plot([0.012, 0.012], [y0 - 0.3, y1 + 0.3], color=t["faint"], lw=2.2, solid_capstyle="butt")
        ax.text(0.0, (y0 + y1) / 2, GRUPO_EN[g], rotation=90, ha="right", va="center", fontsize=8.6, color=t["muted"])
    # llave de los cuatro productos de la auditoría de sequía
    y0, y1 = yp[SEQUIA[0]], yp[SEQUIA[-1]]
    xb = 0.905
    ax.plot([xb, xb + 0.008, xb + 0.008, xb], [y0 - 0.3, y0 - 0.3, y1 + 0.3, y1 + 0.3], color=OI["vermillion"], lw=1.4)
    ax.text(xb + 0.016, (y0 + y1) / 2, "the four products\nin the drought\naudit (barcode)", ha="left", va="center",
            fontsize=9, color=OI["vermillion"], linespacing=1.3)
    ax.text(XR + 0.02, yp["GRACE"] + 0.42, "the only gauge-free water witness,\nbut ~3° effective resolution "
            "(wider than the DR)", ha="left", va="top", fontsize=8.2, color=OI["green"], linespacing=1.25)
    ax.text(XL, -0.95, "INPUTS", ha="center", fontsize=9, color=t["muted"], fontweight="bold")
    ax.text(XR, -0.95, "PRODUCTS", ha="center", fontsize=9, color=t["muted"], fontweight="bold")
    nV = sum(1 for e in edges if e[2] == "V")
    nI = len(edges) - nV
    cabecera(fig, t, "Agreement is not validation: the products share their ancestors",
             f"Which inputs feed which product, from the official documentation ({nV} links verified, solid; {nI} "
             f"inferred, dashed).\n{len(compartidos)} of {len(m.index)} inputs feed two or more of the four rainfall products "
             "used to call drought (vermillion).\nRain gauges reported on the WMO GTS feed all four of them.", ts=21, ss=11.2,
             y=0.955)
    pie(fig, t, FUENTE + "\nNode size ∝ number of links. '→ n' = products fed by the input.  ·  Analysis: Stellar "
                "Horizons, NASA Space Apps 2026", size=7.3, y=0.02)
    return fig


def run(temas=None) -> dict:
    m, edges, compartidos = cargar()
    files = []
    nV = sum(1 for e in edges if e[2] == "V")
    numeros = {"n_insumos": len(m.index), "n_productos": len(m.columns), "n_aristas": len(edges), "n_verificadas": nV,
               "n_inferidas": len(edges) - nV, "insumos_compartidos_por_productos_de_sequia": compartidos,
               "aristas": [{"insumo": i, "producto": p, "estado": s} for i, p, s in edges]}
    for t in theme_list(temas):
        files += guardar(dibujar(t, m, edges, compartidos), NOMBRE, t,
                         f"Bipartite provenance diagram: {len(m.index)} inputs to {len(m.columns)} products, {len(edges)} links "
                         f"({nV} verified). Shared inputs of the four drought products: {', '.join(compartidos)}.", FUENTE)
    alt_en = (f"An alluvial diagram: {len(m.index)} inputs on the left (rain gauges, satellite sensors, models) connect "
              f"through curved lines to {len(m.columns)} products on the right. Vermillion curves show that "
              f"{len(compartidos)} inputs, led by the WMO GTS SYNOP rain gauges, each feed two or more of the four rainfall "
              f"products used in the drought audit (IMERG, CHIRPS, GLDAS forcing, MERRA-2). Only GRACE gravimetry "
              f"(green) is gauge-free, at about 3 degrees resolution.")
    alt_es = (f"Diagrama aluvial: {len(m.index)} insumos a la izquierda (pluviómetros, sensores satelitales, modelos) se "
              f"conectan con {len(m.columns)} productos a la derecha. Las curvas bermellón muestran que {len(compartidos)} "
              f"insumos, empezando por los pluviómetros SYNOP del GTS, alimentan a dos o más de los cuatro productos de "
              f"lluvia de la auditoría de sequía. Solo la gravimetría GRACE (verde) es independiente de los pluviómetros, "
              f"con ~3° de resolución.")
    procedencia(NOMBRE, "Agreement is not validation (genealogy of the data)", "Coincidir no es validar (genealogía de los datos)",
                files, [entrada("results/auditoria/procedencia_insumos_compartidos.csv", "matriz insumo × producto (V/I)"),
                        entrada("results/auditoria/procedencia_matriz.csv", "ficha de cada producto"),
                        entrada("results/auditoria/procedencia.json", "aristas y veredicto")],
                "Cada arista = celda V o I de la matriz; sólida = V (verificado), discontinua = I (inferido). Resaltadas las "
                "aristas de insumos que alimentan ≥ 2 de {IMERG, CHIRPS, GLDAS_forzamiento, MERRA2} hacia esos productos.",
                numeros, alt_en, alt_es, ["Ver procedencia_matriz.csv para las URL de cada afirmación."])
    return {"archivos": files, "numeros": numeros}
