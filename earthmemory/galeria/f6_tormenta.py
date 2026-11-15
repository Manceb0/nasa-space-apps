"""Pieza 6 · Tormenta de Santo Domingo, 17-19 nov 2023: lluvia IMERG V07 Final de media hora acumulándose sobre la RD.

GIF animado (Pillow, paleta global) + fotogramas clave en 6 paneles (oscuro y claro). Acumulado desde el
17-nov 00:00 UTC. A la derecha, el acumulado en la celda IMERG usada por la auditoría (18.45 N, −69.95) y en la mejor
de sus 9 vecinas, frente a los 431 mm del pluviómetro de Arroyo Hondo Viejo (NHC TCR AL222023: «24-h period ending on
18 November»; ventana exacta y coordenada NO públicas, como advierte la auditoría).
"""

from __future__ import annotations

import io
import json

import matplotlib as mpl
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap

from . import datos as D
from .estilo import OUT, SLIDE, cabecera, entrada, guardar, lienzo, pie, procedencia, theme_list, TEMAS, aplicar, SOFTWARE

NOMBRE = "06_santo_domingo_storm"
OI_V = "#D55E00"
NIVELES = [10, 25, 50, 75, 100, 150, 200, 250, 300]
EST = (18.495, -69.948)          # centroide aproximado del barrio (auditoría); la coordenada exacta no es pública
FUENTE = ("Data: NASA GPM IMERG V07 Final half-hourly (3IMERGHH, 0.1°) · gauge value: NHC Tropical Cyclone Report AL222023 "
          "(Hagen 2024) · geoBoundaries ADM0/ADM1")


def cargar() -> dict:
    from ..auditoria import datos as adatos
    hh = adatos.imerg_halfhour()
    t = pd.DatetimeIndex(hh["t"])
    sel = (t >= "2023-11-17") & (t < "2023-11-20")
    P = np.asarray(hh["P"], float)[sel]
    t = t[sel]
    assert len(t) == 144, len(t)
    lat, lon = np.asarray(hh["lat"], float), np.asarray(hh["lon"], float)
    sd = json.loads((D.R_AUD / "santo_domingo_2023-11-18.json").read_text(encoding="utf-8"))
    i = int(np.argmin(np.abs(lat - sd["celda"]["lat"])))
    j = int(np.argmin(np.abs(lon - sd["celda"]["lon"])))
    A = np.nancumsum(np.nan_to_num(P), 0)
    celda = A[:, i, j]
    vec = A[:, i - 1:i + 2, j - 1:j + 2].reshape(len(t), -1)
    kbest = int(np.argmax(vec[-1]))
    best = vec[:, kbest]
    d18 = (t >= "2023-11-18") & (t < "2023-11-19")
    dia18 = float(np.nansum(P[d18, i, j]))
    ref = sd["imerg_diario"]["celda_dia_utc_18"]
    assert abs(dia18 - ref) < 0.5, (dia18, ref)
    return {"P": P, "A": A, "t": t, "lat": lat, "lon": lon, "i": i, "j": j, "celda": celda, "best": best,
            "dia18": dia18, "sd": sd, "est_mm": sd["descomposicion"]["estacion_mm"],
            "max_region": float(np.nanmax(A[-1]))}


def _cmap(t):
    base = mpl.colormaps["viridis"]
    xs = np.linspace(0.12, 1.0, len(NIVELES) - 1) if t["name"] == "dark" else np.linspace(0.92, 0.0, len(NIVELES) - 1)
    cm = ListedColormap([base(x) for x in xs])
    cm.set_over(base(1.0) if t["name"] == "dark" else base(0.0))
    return cm, BoundaryNorm(NIVELES, cm.N)


def _mapa(ax, t, S, k, cm, norm, rings1, rings0, fs=7):
    lon, lat = S["lon"], S["lat"]
    X = np.where(S["A"][k] >= NIVELES[0], S["A"][k], np.nan)
    dl = 0.05
    ax.pcolormesh(np.r_[lon - dl, lon[-1] + dl], np.r_[lat - dl, lat[-1] + dl], X, cmap=cm, norm=norm, shading="flat",
                  zorder=1)
    for _, rr in rings1:
        for e in rr:
            ax.plot(e[:, 0], e[:, 1], color=t["muted"], lw=0.3, alpha=0.7, zorder=2)
    for e in rings0:
        ax.plot(e[:, 0], e[:, 1], color=t["ink"], lw=0.6, alpha=0.9, zorder=3)
    ax.plot(EST[1], EST[0], marker="o", ms=4, mfc="none", mec=t["ink"], mew=0.9, zorder=4)
    ax.set_xlim(-72.1, -68.25)
    ax.set_ylim(17.45, 20.0)
    ax.set_aspect(1 / np.cos(np.radians(18.8)))
    ax.axis("off")


def _serie(ax, t, S, k, fs=8):
    tt = (S["t"] - S["t"][0]).total_seconds() / 3600 + 0.5
    ax.plot(tt[:k + 1], S["celda"][:k + 1], color=t["ink"], lw=1.6)
    ax.plot(tt[:k + 1], S["best"][:k + 1], color=t["ink"], lw=0.9, ls=(0, (2, 1.5)), alpha=0.8)
    ax.axhline(S["est_mm"], color=OI_V, lw=1.2,
               ls=(0, (5, 2)))
    ax.text(1, S["est_mm"] + 8, f"{S['est_mm']:.0f} mm: gauge, 24 h ending 18 Nov (NHC)", fontsize=fs * 0.9,
            color=t["ink"], va="bottom")
    ax.set_xlim(0, 72)
    ax.set_ylim(0, 470)
    ax.set_xticks([0, 24, 48, 72])
    ax.set_xticklabels(["17 Nov", "18 Nov", "19 Nov", "20 Nov"], fontsize=fs * 0.85)
    ax.tick_params(labelsize=fs * 0.85, length=2, colors=t["muted"])
    ax.set_ylabel("mm since 17 Nov 00 UTC", fontsize=fs * 0.9, color=t["muted"])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(t["faint"])
    ax.spines["bottom"].set_color(t["faint"])
    if k >= 0:
        ax.text(tt[k] + 1, S["celda"][k], f"{S['celda'][k]:.0f}", fontsize=fs, color=t["ink"], va="center")
        ax.text(tt[k] + 1, S["best"][k] + 14, f"{S['best'][k]:.0f}", fontsize=fs * 0.85, color=t["muted"], va="center")


def frame_fig(t, S, k, cm, norm, rings1, rings0):
    aplicar(t)
    fig = mpl.figure.Figure(figsize=(9.6, 5.4), dpi=100)
    fig.patch.set_facecolor(t["bg"])
    ax = fig.add_axes([0.01, 0.175, 0.60, 0.655])
    _mapa(ax, t, S, k, cm, norm, rings1, rings0)
    ts = S["t"][k] + pd.Timedelta(minutes=30)
    loc = ts - pd.Timedelta(hours=4)
    fig.text(0.03, 0.93, "Santo Domingo storm, 17–19 Nov 2023: rain piling up, seen by NASA IMERG", fontsize=13,
             fontweight="bold", color=t["ink"], va="top")
    fig.text(0.03, 0.865, f"{ts:%a %d %b %H:%M} UTC   ·   {loc:%H:%M} local (AST, UTC−4)", fontsize=11,
             color=t["ink"], va="top", family="DejaVu Sans Mono")
    sx = fig.add_axes([0.68, 0.30, 0.29, 0.50])
    sx.set_facecolor(t["bg"])
    _serie(sx, t, S, k, fs=8)
    fig.text(0.68, 0.84, "Accumulated rain at Santo Domingo", fontsize=9.5, color=t["ink"], va="bottom")
    fig.text(0.68, 0.205, "— IMERG cell 18.45 N, 69.95 W\n- - wettest of its 9 neighbouring cells", fontsize=7.5,
             color=t["muted"], va="top", linespacing=1.4)
    cax = fig.add_axes([0.06, 0.075, 0.45, 0.025])
    cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cm), cax=cax, orientation="horizontal", ticks=NIVELES,
                      extend="max")
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7, length=0, colors=t["muted"])
    cb.ax.set_title("mm accumulated since 17 Nov 00:00 UTC (IMERG V07 Final, 0.1°)", fontsize=7.5, color=t["ink"],
                    loc="left", pad=3)
    fig.text(0.03, 0.012, "Gauge window and exact coordinate are not public (audit verdict: inconclusive on the gap; "
             "a 10 km product does not reproduce this point extreme). ○ = approx. gauge site.\n"
             "Data: NASA GPM IMERG V07 Final · NHC TCR AL222023 · Analysis: Stellar Horizons, NASA Space Apps 2026",
             fontsize=5.6, color=t["muted"], va="bottom")
    return fig


def _rgb(fig):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    c = FigureCanvasAgg(fig)
    c.draw()
    return np.asarray(c.buffer_rgba())[..., :3].copy()


def gif(S, rings1, rings0) -> str:
    from PIL import Image
    t = TEMAS["dark"]
    cm, norm = _cmap(t)
    n = len(S["t"])
    frames = [_rgb(frame_fig(t, S, k, cm, norm, rings1, rings0)) for k in range(n)]
    pal_img = Image.fromarray(frames[-1]).quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    ims = [Image.fromarray(f).quantize(palette=pal_img, dither=Image.Dither.NONE) for f in frames]
    ims += [ims[-1]] * 18
    p = OUT / "dark" / f"{NOMBRE}.gif"
    p.parent.mkdir(parents=True, exist_ok=True)
    ims[0].save(p, save_all=True, append_images=ims[1:], duration=110, loop=0, optimize=True,
                comment=f"NASA GPM IMERG V07 Final half-hourly, 17-19 Nov 2023. {SOFTWARE}".encode())
    size = p.stat().st_size
    assert size <= 8 * 2**20, size
    return str(p).replace("\\", "/")


def keyframes(t, S, rings1, rings0):
    fig = lienzo(t, SLIDE)
    cm, norm = _cmap(t)
    ends = [pd.Timestamp(x) for x in ("2023-11-17 18:00", "2023-11-18 06:00", "2023-11-18 12:00", "2023-11-18 18:00",
                                       "2023-11-19 00:00", "2023-11-20 00:00")]
    tend = S["t"] + pd.Timedelta(minutes=30)
    for n_, e in enumerate(ends):
        k = int(np.flatnonzero(tend == e)[0])
        r, c = divmod(n_, 3)
        ax = fig.add_axes([0.035 + c * 0.315, 0.50 - r * 0.335, 0.30, 0.285])
        _mapa(ax, t, S, k, cm, norm, rings1, rings0)
        loc = e - pd.Timedelta(hours=4)
        ax.set_title(f"to {e:%d Nov %H:%M} UTC ({loc:%d Nov %H:%M} local)", fontsize=10, color=t["ink"], loc="left")
        ax.text(0.98, 0.04, f"cell: {S['celda'][k]:.0f} mm", transform=ax.transAxes, ha="right", fontsize=9,
                color=t["ink"])
    cax = fig.add_axes([0.035, 0.075, 0.36, 0.022])
    cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cm), cax=cax, orientation="horizontal", ticks=NIVELES,
                      extend="max")
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8.5, length=0, colors=t["muted"])
    cb.ax.set_title("mm accumulated since 17 Nov 2023 00:00 UTC", fontsize=9.5, color=t["ink"], loc="left", pad=4)
    d = S["sd"]["descomposicion"]
    cabecera(fig, t, "Santo Domingo, 18 Nov 2023: what a 10 km satellite saw",
             f"NASA IMERG V07 Final, half-hourly, accumulated over 72 h. In the UTC day of 18 Nov the cell over the "
             f"gauge got {S['dia18']:.0f} mm; the wettest 24 h window\nof the best of 9 neighbouring cells reached "
             f"{d['imerg_mejor_vecina_mejor_ventana_mm']:.0f} mm. The gauge (○) reported {S['est_mm']:.0f} mm in 24 h.",
             ts=21, ss=11, y=0.955)
    pie(fig, t, "Data: NASA GPM IMERG V07 Final half-hourly (3IMERGHH, 0.1°) · gauge: NHC Tropical Cyclone Report\n"
                "AL222023 (Hagen 2024) · geoBoundaries. The gauge's exact 24 h window and coordinate are not public: the "
                f"audit\nleaves the {d['brecha_restante_mm']:.0f} mm gap unattributed, but no window or neighbouring cell "
                "brings IMERG close to the point value.\nAnalysis: Stellar Horizons, NASA Space Apps 2026",
        x=0.45, y=0.02, size=7.0)
    return fig


def run(temas=None) -> dict:
    S = cargar()
    rings1 = D.adm1_rings()
    rings0 = D.adm0_rings()
    files = []
    for t in theme_list(temas):
        files += guardar(keyframes(t, S, rings1, rings0), NOMBRE + "_keyframes", t,
                         "IMERG half-hourly rain accumulated 17-19 Nov 2023 over the Dominican Republic, six key frames.",
                         FUENTE)
    files.append(gif(S, rings1, rings0))
    d = S["sd"]["descomposicion"]
    numeros = {"imerg_celda_dia_utc_18_mm": S["dia18"], "imerg_celda_72h_mm": float(S["celda"][-1]),
               "imerg_mejor_vecina_72h_mm": float(S["best"][-1]), "maximo_region_72h_mm": S["max_region"],
               "estacion_mm": S["est_mm"], "imerg_mejor_vecina_mejor_ventana_mm": d["imerg_mejor_vecina_mejor_ventana_mm"],
               "brecha_restante_mm": d["brecha_restante_mm"], "celda": S["sd"]["celda"],
               "gif_bytes": (OUT / "dark" / f"{NOMBRE}.gif").stat().st_size, "fotogramas": len(S["t"]) + 18,
               "ms_por_fotograma": 110}
    alt_en = (f"Animated dark map of the Dominican Republic: NASA IMERG half-hourly rain accumulating from 17 to 19 November "
              f"2023, with a UTC and local clock. A side chart grows the accumulated rain at the Santo Domingo cell to "
              f"{S['celda'][-1]:.0f} mm in 72 h, below the dashed 431 mm line reported by the gauge in 24 h. Six key "
              f"frames are provided as a still.")
    alt_es = (f"Mapa animado de la RD: lluvia IMERG de media hora acumulándose del 17 al 19 de noviembre de 2023, con reloj "
              f"UTC y local. Un gráfico lateral muestra el acumulado en la celda de Santo Domingo hasta {S['celda'][-1]:.0f} "
              f"mm en 72 h, por debajo de la línea de 431 mm del pluviómetro en 24 h. Seis fotogramas clave como imagen fija.")
    procedencia(NOMBRE, "Santo Domingo storm, 17-19 Nov 2023", "Tormenta de Santo Domingo, 17-19 nov 2023", files,
                [entrada("data/nacional/gesdisc/GPM_3IMERGHH.07", "144 archivos IMERG V07 Final de media hora"),
                 entrada("results/auditoria/santo_domingo_2023-11-18.json", "celda, 431 mm, descomposición de la brecha")],
                "Acumulado = cumsum de mm por media hora (auditoria.datos.imerg_halfhour, ya en mm por 30 min). Control: suma "
                "del día UTC 18 en la celda = imerg_diario.celda_dia_utc_18 de la auditoría (±0.5 mm).", numeros, alt_en,
                alt_es, ["Ventana de 24 h y coordenada del pluviómetro no públicas: veredicto inconcluso para repartir la brecha.",
                         "El 431 mm es un valor de 24 h; la curva IMERG es un acumulado de 72 h (comparación generosa con IMERG)."])
    return {"archivos": files, "numeros": numeros}
