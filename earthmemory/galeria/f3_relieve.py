"""Pieza 3 · «Ridgeline relief map» (estilo Unknown Pleasures) de la República Dominicana.

Perfiles horizontales de elevación (Copernicus GLO-90, mosaico 1/300° del motor de alta resolución) apilados de
norte a sur. Cada tramo de línea se colorea por la clase de confianza de la tendencia 2001-2024 de la intensidad
diaria simple (SDII, anual) en su celda 0.1° (results/tendencias/tendencias_celdas.csv):
  en disputa = IMERG y CHIRPS con tendencias de signo opuesto y al menos una FDR-significativa;
  consistente = mismo signo, una significativa; sin señal detectable; fuera del dominio (Haití / celdas < 25 % RD).
Cuenca del Yuna (contorno elevado sobre el relieve) y presa de Hatillo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection

from . import datos as D
from .estilo import OI, SLIDE, SQUARE, cabecera, entrada, guardar, lienzo, pie, procedencia, theme_list

NOMBRE = "03_ridgeline_relief"
K = 1.0e-4            # grados de latitud por metro de elevación (exageración vertical ≈ 11×)
PASO = 0.03           # separación entre perfiles (grados)
FUENTE = ("Data: Copernicus GLO-90 DEM (ESA/Airbus, via AWS open data) · NASA GPM IMERG V07 Final and CHC CHIRPS v2.0 "
          "daily, SDII trends 2001–2024 (Mann-Kendall/Sen with FDR q ≤ 0.10, Stellar Horizons trend engine) · Yuna basin "
          "from HydroSHEDS.")


def clases_sdii() -> tuple[dict, dict]:
    d = pd.read_csv(D.R_TEN / "tendencias_celdas.csv")
    s = d[(d["indice"] == "SDII") & (d["periodo"] == "anual")]
    im = s[s["fuente"] == "IMERG"].set_index("celda")
    ch = s[s["fuente"] == "CHIRPS"].set_index("celda")
    assert (im["clase_confianza"] == ch.loc[im.index, "clase_confianza"]).all()
    cls = im["clase_confianza"].to_dict()
    disp = im.index[im["clase_confianza"] == "en disputa"]
    info = {"n_celdas": int(len(im)), "por_clase": im["clase_confianza"].value_counts().to_dict(),
            "disputa_imerg_sube_chirps_baja": int(((im.loc[disp, "pendiente_decada"] > 0)
                                                    & (ch.loc[disp, "pendiente_decada"] < 0)).sum()),
            "disputa_imerg_sig": int(im.loc[disp, "sig_fdr"].astype(bool).sum()),
            "disputa_chirps_sig": int(ch.loc[disp, "sig_fdr"].astype(bool).sum()),
            "mediana_pendiente_imerg_disputa_mm_dia_decada": float(im.loc[disp, "pendiente_decada"].median()),
            "mediana_pendiente_chirps_disputa_mm_dia_decada": float(ch.loc[disp, "pendiente_decada"].median())}
    return cls, info


def color_clase(t: dict) -> dict:
    return {"en disputa": OI["vermillion"], "consistente": OI["sky"], "robusta": OI["blue"],
            "sin señal detectable": t["ink"], None: t["muted"]}


def _cell(lat, lon):
    return f"{np.floor(lat * 10) / 10 + 0.05:.3f}_{np.floor(lon * 10) / 10 + 0.05:.3f}"


def dibujar(t, dem, cls, info, size=SLIDE):
    sq = size == SQUARE
    fig = lienzo(t, size)
    ax = fig.add_axes([0.02, 0.10, 0.96, 0.66] if sq else [0.33, 0.04, 0.66, 0.92])
    Z, lat, lon = dem["Z"], dem["lat"], dem["lon"]
    if lat[0] > lat[-1]:
        Z, lat = Z[::-1], lat[::-1]
    step = 2
    lon_s = lon[::step]
    cc = color_clase(t)
    alpha_cls = {"en disputa": 1.0, "consistente": 1.0, "robusta": 1.0, "sin señal detectable": 0.55, None: 0.30}
    rows = np.arange(19.95, 17.50, -PASO)
    lw = 0.55 if sq else 0.85
    ring, _ = D.yuna_ring()
    for k, la in enumerate(rows):
        i = int(np.argmin(np.abs(lat - la)))
        z = Z[i, ::step].astype(float)
        land = np.isfinite(z) & (z != 0)
        if not land.any():
            continue
        y = la + np.where(land, z, 0) * K
        z_ord = 10 + k
        # tramos de tierra contiguos
        idx = np.flatnonzero(land)
        cuts = np.flatnonzero(np.diff(idx) > 1)
        runs = np.split(idx, cuts + 1)
        keys = [cls.get(_cell(la, x)) for x in lon_s]
        cols = []
        for kk in keys:
            c = cc[kk]
            from matplotlib.colors import to_rgba
            cols.append(to_rgba(c, alpha_cls[kk]))
        for r in runs:
            if r.size < 2:
                continue
            r = np.concatenate([[max(r[0] - 1, 0)], r, [min(r[-1] + 1, len(z) - 1)]])
            xs, ys = lon_s[r], y[r]
            ys[0], ys[-1] = la, la
            ax.fill_between(xs, la - 0.002, ys, color=t["bg"], lw=0, zorder=z_ord)
            pts = np.column_stack([xs, ys])
            segs = np.stack([pts[:-1], pts[1:]], 1)
            lc = LineCollection(segs, colors=[cols[j] for j in r[:-1]], linewidths=lw, zorder=z_ord + 0.5,
                                capstyle="round", joinstyle="round")
            ax.add_collection(lc)
    # cuenca del Yuna elevada sobre el relieve
    ii = np.clip(np.searchsorted(lat, ring[:, 1]), 0, lat.size - 1)
    jj = np.clip(np.searchsorted(lon, ring[:, 0]), 0, lon.size - 1)
    zr = np.nan_to_num(Z[ii, jj].astype(float))
    ax.plot(ring[:, 0], ring[:, 1] + zr * K, color=t["ink"], lw=1.1 if not sq else 0.7, ls=(0, (3, 1.6)),
            zorder=500)
    hy, hx = D.hatillo()
    zh = float(np.nan_to_num(Z[np.searchsorted(lat, hy), np.searchsorted(lon, hx)]))
    ax.plot(hx, hy + zh * K, marker="v", ms=8 if not sq else 5, color=OI["orange"], mec=t["bg"], mew=0.8, zorder=501)
    fs = 6 if sq else 10
    ax.annotate("Hatillo dam", xy=(hx, hy + zh * K), xytext=(hx + 0.28, hy - 0.42), fontsize=fs, color=OI["orange"],
                bbox=dict(boxstyle="square,pad=0.2", fc=t["bg"], ec="none"),
                zorder=502, arrowprops=dict(arrowstyle="-", color=OI["orange"], lw=0.7))
    io = int(np.argmax(ring[:, 0]))
    ax.annotate("Yuna basin (dashed)", xy=(ring[io, 0], ring[io, 1] + zr[io] * K), xytext=(-69.75, 20.12),
                fontsize=fs, color=t["ink"], zorder=502, ha="center",
                arrowprops=dict(arrowstyle="-", color=t["ink"], lw=0.7))
    # Pico Duarte (máximo del DEM) y barra de escala vertical
    imax = np.unravel_index(np.nanargmax(Z), Z.shape)
    ax.annotate(f"Highest DEM sample on this 1/300° grid: {Z[imax]:,.0f} m (Pico Duarte area)", xy=(lon[imax[1]], lat[imax[0]] + Z[imax] * K),
                xytext=(-71.55, 20.22), fontsize=fs * 0.85, color=t["muted"],
                zorder=502, arrowprops=dict(arrowstyle="-", color=t["muted"], lw=0.6))
    bx, by = -68.62, 19.45
    ax.plot([bx, bx], [by, by + 1000 * K], color=t["ink"], lw=1.2, zorder=503)
    ax.text(bx - 0.04, by + 500 * K, "1,000 m\n(vertical ×11)", fontsize=fs * 0.85, color=t["ink"], va="center",
            ha="right", zorder=503)
    ax.text(-71.98, 19.98, "HAITI", fontsize=fs * 0.9, color=t["muted"], zorder=503, alpha=0.8)
    ax.set_xlim(-72.05, -68.30)
    ax.set_ylim(17.45, 20.35)
    ax.set_aspect(1 / np.cos(np.radians(18.9)))
    ax.axis("off")
    n = info["por_clase"]
    leg = [(cc["en disputa"], 1.0, f"Sources disagree: IMERG ↑, CHIRPS ↓ ({n.get('en disputa', 0)} cells)"),
           (cc["consistente"], 1.0, f"Consistent sign, one significant ({n.get('consistente', 0)})"),
           (cc["sin señal detectable"], 0.55, f"No detectable trend ({n.get('sin señal detectable', 0)})"),
           (cc[None], 0.30, "Outside the 442-cell domain")]
    if sq:
        cabecera(fig, t, "Two satellites, two climates",
                 "Ridgelines: Copernicus DEM. Colour: does rain fall harder (SDII) in\n2001–2024? "
                 f"IMERG and CHIRPS disagree in {n.get('en disputa', 0)} of {info['n_celdas']} cells.",
                 x=0.05, y=0.955, ts=15, ss=7.2)
        y0 = 0.085
        for c, a, lab in leg[:3]:
            fig.lines.append(__import__("matplotlib").lines.Line2D([0.05, 0.085], [y0, y0], transform=fig.transFigure,
                                                                    color=c, alpha=a, lw=2))
            fig.text(0.095, y0, lab, fontsize=5.6, va="center", color=t["ink"])
            y0 -= 0.025
        pie(fig, t, "Data: Copernicus GLO-90 DEM · NASA IMERG V07 · CHIRPS v2.0 · HydroSHEDS. Analysis: Stellar Horizons",
            x=0.05, y=0.008, size=4.6)
    else:
        cabecera(fig, t, "Two satellites,\ntwo climates", "", x=0.035, y=0.93, ts=28)
        fig.text(0.035, 0.72,
                 "Each line is an east–west elevation profile of\nHispaniola (Copernicus 90 m DEM), stacked north\n"
                 "to south. Its colour tells whether NASA IMERG\nand CHIRPS agree on how daily rain intensity\n"
                 "(SDII, mm per wet day) changed in 2001–2024.", fontsize=11.2, color=t["muted"], va="top",
                 linespacing=1.45)
        fig.text(0.035, 0.445, f"{n.get('en disputa', 0)} of {info['n_celdas']} cells", fontsize=24,
                 fontweight="bold", color=OI["vermillion"], va="bottom")
        fig.text(0.035, 0.435,
                 f"IMERG says rain got more intense (median\n+{info['mediana_pendiente_imerg_disputa_mm_dia_decada']:.1f}"
                 f" mm/day per decade); CHIRPS says less\nintense (median {info['mediana_pendiente_chirps_disputa_mm_dia_decada']:.1f})."
                 " Opposite signs, at least one\nsignificant after FDR: a product artefact\nuntil a third witness decides.",
                 fontsize=10.2, color=t["muted"], va="top", linespacing=1.4)
        y0 = 0.255
        import matplotlib.lines as mlines
        for c, a, lab in leg:
            fig.lines.append(mlines.Line2D([0.035, 0.065], [y0, y0], transform=fig.transFigure, color=c, alpha=a, lw=2.2))
            fig.text(0.073, y0, lab, fontsize=9.3, va="center", color=t["ink"])
            y0 -= 0.032
        pie(fig, t, "Data: Copernicus GLO-90 DEM (ESA, AWS open data) ·\nNASA GPM IMERG V07 Final · CHC CHIRPS v2.0 "
                    "daily (0.1°) ·\nHydroSHEDS. Trends: Sen slope, Mann-Kendall,\nFDR q ≤ 0.10. Dashed: Yuna basin.  "
                    "Analysis:\nStellar Horizons, NASA Space Apps 2026", x=0.035, y=0.022, size=7.3)
    return fig


def run(temas=None) -> dict:
    cls, info = clases_sdii()
    assert info["n_celdas"] == 442
    dem = D.dem_nativo()
    files = []
    desc = (f"Ridgeline relief map of Hispaniola from Copernicus DEM; line colour = SDII trend agreement IMERG vs "
            f"CHIRPS: {info['por_clase']}")
    for t in theme_list(temas):
        files += guardar(dibujar(t, dem, cls, info), NOMBRE, t, desc, FUENTE)
        files += guardar(dibujar(t, dem, cls, info, SQUARE), NOMBRE, t, desc, FUENTE, "_square")
    n = info["por_clase"]
    alt_en = (f"About 80 stacked east-west elevation profiles of Hispaniola drawn as glowing-free thin lines on a dark "
              f"ground, mountains rising as peaks (Cordillera Central up to Pico Duarte). Line colour per 0.1° cell: "
              f"vermillion where IMERG and CHIRPS disagree on the 2001-2024 trend of daily rain intensity "
              f"({n.get('en disputa', 0)} of 442 cells, mostly IMERG up and CHIRPS down), white where no trend is "
              f"detectable, sky blue where consistent. The Yuna basin is outlined dashed with the Hatillo dam marked.")
    alt_es = (f"Unos 80 perfiles de elevación este-oeste de La Española apilados de norte a sur. Color por celda 0.1°: "
              f"bermellón donde IMERG y CHIRPS discrepan en la tendencia 2001-2024 de la intensidad diaria de la lluvia "
              f"({n.get('en disputa', 0)} de 442 celdas; IMERG sube y CHIRPS baja), blanco sin tendencia detectable, "
              f"celeste consistente. Cuenca del Yuna en discontinua y presa de Hatillo marcada.")
    procedencia(NOMBRE, "Two satellites, two climates (ridgeline relief)", "Dos satélites, dos climas (relieve en crestas)",
                files, [entrada("data/nacional_hr/derivados/nativas.npz", "dem_Z/dem_lat/dem_lon: Copernicus GLO-90 a 1/300°"),
                        entrada("results/tendencias/tendencias_celdas.csv", "clase_confianza SDII anual por celda 0.1°"),
                        entrada("results/yuna/cuencas_yuna.geojson", "cuenca del Yuna"),
                        entrada("results/yuna/hatillo_ficha.json", "coordenada de la presa")],
                f"Perfiles cada {PASO}° de latitud (fila DEM más cercana), muestreo cada 2 columnas; y = lat + elevación × "
                f"{K} °/m (exageración ≈ 11×). Color de cada tramo = clase de la celda 0.1° que contiene el punto.",
                info, alt_en, alt_es,
                ["Clase 'en disputa' = señal de los productos (detección de llovizna, reparto diario), no del clima.",
                 "Exageración vertical ×11 (indicada con barra de 1 000 m)."])
    return {"archivos": files, "numeros": info}
