"""Pieza 2 · «Spiral of disagreement»: los 288 meses como espiral de Arquímedes (2001 en el centro → 2024 fuera),
meses alrededor del círculo (enero arriba, sentido horario). Color = nº de provincias (de 32) en que los cuatro
productos de lluvia NO son unánimes sobre la sequía (SPI-3 ≤ −1): mismas definiciones que la auditoría.
"""

from __future__ import annotations

import numpy as np
import matplotlib as mpl
from matplotlib.collections import LineCollection
from matplotlib.colors import BoundaryNorm, ListedColormap

from . import datos as D
from .estilo import OI, SLIDE, SQUARE, cabecera, entrada, guardar, lienzo, pie, procedencia, theme_list

NOMBRE = "02_spiral_of_disagreement"
FUENTE = ("Data: NASA GPM IMERG V07 Final · CHC CHIRPS v2.0 · NASA GLDAS-2.1 forcing rain (GPCP) · NASA MERRA-2 via "
          "POWER · geoBoundaries ADM1.")
MES = "JFMAMJJASOND"


def cmap_tema(t: dict):
    base = mpl.colormaps["cividis"]
    if t["name"] == "dark":
        return ListedColormap([base(x) for x in np.linspace(0.10, 1.0, 33)])
    out = []
    for x in np.linspace(0, 1, 33):          # claro: crema casi blanca (0) → azul marino (32), luminosidad monótona
        c = np.array(base(0.9 - 0.9 * x)[:3])
        w = 0.25 + 0.75 * x
        out.append(tuple(w * c + (1 - w) * np.ones(3)))
    return ListedColormap(out)


def geometria(n: int, r0: float = 0.16, r1: float = 1.0, sub: int = 12):
    """Puntos (x, y) por sub-paso. Mes i ocupa el arco [i, i+1)/12 de vuelta; r crece linealmente."""
    s = np.linspace(0, n, n * sub + 1)
    ang = np.pi / 2 - 2 * np.pi * (s / 12.0)
    r = r0 + (r1 - r0) * s / n
    return s, r * np.cos(ang), r * np.sin(ang), r


def dibujar(t: dict, v: np.ndarray, meses, info: dict, size=SLIDE):
    sq = size == SQUARE
    fig = lienzo(t, size)
    ax = fig.add_axes([0.08, 0.12, 0.84, 0.70] if sq else [0.47, 0.06, 0.50, 0.89])
    ax.set_aspect("equal")
    ax.axis("off")
    n = v.size
    sub = 12
    s, x, y, r = geometria(n, sub=sub)
    pts = np.column_stack([x, y])
    segs = np.stack([pts[:-1], pts[1:]], 1)
    vals = np.repeat(v, sub).astype(float)
    cm = cmap_tema(t)
    norm = BoundaryNorm(np.arange(-0.5, 33.5, 1), cm.N)
    ok = np.isfinite(vals)
    lw = 3.1 if sq else 5.8
    lc = LineCollection(segs[ok], colors=cm(norm(vals[ok])), linewidths=lw, capstyle="projecting")
    ax.add_collection(lc)
    # guías de mes (radiales tenues) y etiquetas
    R = 1.075
    for m in range(12):
        a = np.pi / 2 - 2 * np.pi * (m + 0.5) / 12
        ax.text(R * np.cos(a), R * np.sin(a), MES[m], ha="center", va="center", fontsize=7 if sq else 11,
                color=t["muted"])
    # años a lo largo del radio de enero (inicio de cada año)
    for yv in (2001, 2005, 2010, 2015, 2020, 2024):
        i = (yv - 2001) * 12
        rr = 0.16 + 0.84 * i / n
        a = np.pi / 2 + 0.03
        ax.text(rr * np.cos(a) - 0.012, rr * np.sin(a), str(yv), ha="right", va="center", fontsize=5.5 if sq else 8.5,
                color=t["ink"], bbox=dict(boxstyle="square,pad=0.12", fc=t["bg"], ec="none", alpha=0.85))
    ax.set_xlim(-1.18, 1.18)
    ax.set_ylim(-1.15, 1.15)
    # barra de color (clave)
    if sq:
        cax = fig.add_axes([0.25, 0.085, 0.5, 0.018])
    else:
        cax = fig.add_axes([0.045, 0.27, 0.36, 0.028])
    sm = mpl.cm.ScalarMappable(norm=norm, cmap=cm)
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal", ticks=[0, 8, 16, 24, 32])
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=6 if sq else 10, length=0, pad=3, colors=t["muted"])
    cb.ax.set_title("provinces where the four products disagree on drought (of 32)", fontsize=6 if sq else 10.5,
                    color=t["ink"], loc="left", pad=5)
    if sq:
        cabecera(fig, t, "Spiral of disagreement",
                 "Each turn is a year (2001 centre → 2024 rim), Jan at top.\nColour: provinces where four rainfall "
                 "products split on drought (SPI-3 ≤ −1)", x=0.05, y=0.955, ts=15, ss=7.2)
        pie(fig, t, "Data: NASA IMERG V07 · CHIRPS v2.0 · GLDAS-2.1 (GPCP) · MERRA-2/POWER. Analysis: Stellar "
                    "Horizons, NASA Space Apps 2026", x=0.05, y=0.018, size=4.8)
    else:
        cabecera(fig, t, "Spiral of\ndisagreement", "", x=0.045, y=0.92, ts=30, ss=12)
        fig.text(0.045, 0.74,
                 "24 years of drought monitoring in the Dominican Republic,\none turn per year (2001 at the centre, "
                 "2024 at the rim),\nJanuary at the top. The colour counts the provinces where\nfour rainfall products "
                 "do not agree on a drought call\n(SPI-3 ≤ −1 in some products but not all).", ha="left", va="top",
                 fontsize=12, color=t["muted"], linespacing=1.45)
        fig.text(0.045, 0.47, f"{info['meses_con_desacuerdo']} of {info['meses_validos']} months",
                 fontsize=24, fontweight="bold", color=t["ink"], ha="left", va="bottom")
        fig.text(0.045, 0.455, f"had at least one province where the products split; in {info['meses_ge16']} months, "
                 "half the\ncountry or more.", fontsize=11, color=t["muted"], ha="left", va="top", linespacing=1.35)
        pie(fig, t, FUENTE + "\nSPI-3 per product with its own 2001–2024 climatology; area-weighted province means. "
                    "Jan–Feb 2001 have no SPI-3.\nProducts share inputs: agreement is not independent validation.\n"
                    "Analysis: Stellar Horizons, NASA Space Apps 2026", size=7.8, y=0.03)
    return fig


def run(temas=None) -> dict:
    spi = D.spi3_provincias()
    E, cnt = D.estados(spi, -1.0)
    D.check_contra_auditoria(E, cnt)
    Em = E.to_numpy()
    valid = (Em != D.NODATA).all(1)
    v = np.where(valid, np.isin(Em, (D.SPLIT, D.MAJ, D.CONTRA)).sum(1), np.nan).astype(float)
    assert int(np.nansum(v)) == cnt["n_no_unanime"] == 2836
    info = {"meses_validos": int(valid.sum()), "meses_con_desacuerdo": int((v >= 1).sum()),
            "meses_ge16": int((v >= 16).sum()), "max": int(np.nanmax(v)),
            "mes_max": str(E.index[int(np.nanargmax(v))].date()), "suma": int(np.nansum(v)),
            "n_meses_max": int((v == np.nanmax(v)).sum())}
    import pandas as pd
    pd.DataFrame({"mes": E.index, "provincias_no_unanimes": v}).to_csv(D.DATOS / "espiral_serie.csv", index=False)
    files = []
    desc = (f"Spiral of disagreement: 288 months 2001-2024; colour = number of provinces (of 32) where four rainfall "
            f"products are not unanimous on drought (SPI-3 <= -1). {info['meses_con_desacuerdo']} of "
            f"{info['meses_validos']} months had at least one; peak {info['max']} in {info['mes_max'][:7]}.")
    for t in theme_list(temas):
        files += guardar(dibujar(t, v, E.index, info), NOMBRE, t, desc, FUENTE)
        files += guardar(dibujar(t, v, E.index, info, SQUARE), NOMBRE, t, desc, FUENTE, "_square")
    alt_en = (f"An Archimedean spiral of 288 monthly segments, 2001 at the centre and 2024 at the rim, January at the top. "
              f"Segment colour (cividis) shows how many of 32 provinces had a non-unanimous drought call among four "
              f"rainfall products. Bright bands appear in drought years; {info['meses_con_desacuerdo']} of "
              f"{info['meses_validos']} months had at least one province in disagreement; maximum {info['max']} "
              f"provinces in {info['mes_max'][:7]}.")
    alt_es = (f"Espiral de Arquímedes de 288 segmentos mensuales (2001 en el centro, 2024 en el borde, enero arriba). "
              f"El color indica en cuántas de las 32 provincias los cuatro productos de lluvia no fueron unánimes sobre "
              f"la sequía. {info['meses_con_desacuerdo']} de {info['meses_validos']} meses tuvieron al menos una; "
              f"máximo {info['max']} provincias en {info['mes_max'][:7]}.")
    procedencia(NOMBRE, "Spiral of disagreement", "Espiral del desacuerdo", files,
                [entrada("figures/galeria/_datos/spi3_provincias.parquet", "SPI-3 provincia-mes recalculado con el motor de auditoría"),
                 entrada("results/auditoria/cambio_decision_sequia_nacional.json", "control: 2836 no unánimes")],
                "n provincias por mes con decision.flip_components()['no_unanime'] (umbral −1.0, 4 productos). Suma = "
                "n_no_unanime de la auditoría (assert).", info, alt_en, alt_es,
                ["Escala de color por recuento entero 0-32 (sin interpolar).",
                 "Los productos comparten insumos: el desacuerdo es un mínimo."])
    return {"archivos": files, "numeros": info}
