"""Crestas de Puerto Rico y Hawái: el relieve (Copernicus GLO-90) en perfiles este-oeste, como el mapa de la RD.

Color de cada tramo: cambio de IMERG V07 en su celda de 0,1° en la frecuencia de días con >= 1 mm, de 2001-01..2018-01
a 2018-02..2024-12 (el corte registrado en puerto_rico.py y hawaii.py). Encima, cada pluviómetro GHCN-D con registro
completo, coloreado con SU cambio en la misma escala (results/tropical/<isla>/cambio_por_estacion.csv). Si IMERG y los
pluviómetros contaran igual, los círculos tendrían el color de las crestas que los rodean.
No calcula nada nuevo sobre los pluviómetros: usa las tablas ya publicadas. La cifra por celda es descriptiva.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.crestas_islas
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

from ..hr.common import ROOT, write_json  # noqa: E402
from .hawaii import imerg  # noqa: E402

OUT = ROOT / "results" / "tropical" / "crestas_islas"
FIG = ROOT / "figures" / "tropical"
DEM = ROOT / "data" / "tropical" / "dem"
CORTE = "2018-02-01"
BG, INK, MUTED = "#0c0d0f", "#f2f2f2", "#9a9ea6"
# baja (pierde días) = naranja, como «más seco» en la web; sube = azul
CMAP = LinearSegmentedColormap.from_list("dias", ["#ff9f0a", "#6b5a3f", "#5d6168", "#2f5f86", "#28a0f0"])
ESCALA = 12.0   # pp: tope de color

ISLAS = {
    "puerto_rico": {
        "bbox": (-67.30, 17.85, -65.55, 18.55), "lat": (17, 18), "lon": (68, 67, 66),
        "paso": 0.0125, "K": 1.2e-4, "ddir": ROOT / "data" / "tropical" / "puerto_rico",
        "res": ROOT / "results" / "tropical" / "puerto_rico" / "cambio_por_estacion.csv",
        "rotulos": [(-66.06, 18.47, "San Juan"), (-66.75, 18.17, "Cordillera Central"), (-65.79, 18.31, "El Yunque")],
        "nombre": {"es": "Puerto Rico", "en": "Puerto Rico"},
    },
    "hawaii": {
        "bbox": (-160.30, 18.85, -154.75, 22.30), "lat": (18, 19, 20, 21, 22), "lon": (161, 160, 159, 158, 157, 156, 155),
        "paso": 0.03, "K": 0.55e-4, "ddir": ROOT / "data" / "tropical" / "hawaii",
        "res": ROOT / "results" / "tropical" / "hawaii" / "cambio_por_estacion.csv",
        "rotulos": [(-159.55, 22.25, "Kauaʻi"), (-158.0, 21.70, "Oʻahu"), (-157.0, 21.25, "Molokaʻi"),
                    (-156.3, 20.98, "Maui"), (-155.45, 20.33, "Hawaiʻi")],
        "nombre": {"es": "Hawái", "en": "Hawaiʻi"},
        "titulo": {"es": "Hawái: IMERG cuenta menos días de lluvia que 39 de 41 pluviómetros",
                   "en": "Hawaiʻi: IMERG counts fewer rain days than 39 of 41 rain gauges"},
        # Kona y Kaʻū: aquí sí llueve más días; los pluviómetros suben más que IMERG (USC00516304 +11,0 frente a +10,4;
        # USC00513376 +12,1 frente a −0,2). Se dice en el mapa para que el azul no se lea como contradicción.
        "nota": (-156.05, 19.25, {"es": "Kona y Kaʻū: aquí sí llueve más días.|Los pluviómetros suben más que IMERG|(+11 y +12 pp frente a +10 y −0,2)",
                                  "en": "Kona and Kaʻū: more rain days here.|Gauges rise more than IMERG|(+11 and +12 pp vs +10 and −0.2)"}),
    },
}
TXT = {
    "es": {"t": "{n}: IMERG pierde días de lluvia; los pluviómetros no",
           "s": "Crestas: relieve Copernicus GLO-90. Color: cambio de IMERG en días con ≥ 1 mm, 2018-24 frente a 2001-18, "
                "por celda de 0,1°. Círculos: {g} pluviómetros GHCN-D con su propio cambio, en la misma escala.",
           "k": "IMERG cae más que el pluviómetro en {a} de {g} · mediana IMERG {mi:+.1f} pp, pluviómetros {mp:+.1f} pp",
           "lo": "pierde días", "hi": "gana días", "u": "puntos porcentuales de días con lluvia",
           "f": "Datos: NASA GPM IMERG V07 Final diario · NOAA GHCN-D · Copernicus GLO-90 (ESA/Airbus, AWS Open Data). "
                "Predicciones registradas antes de calcular. Stellar Horizons, NASA Space Apps 2026."},
    "en": {"t": "{n}: IMERG loses rain days; the rain gauges don't",
           "s": "Ridges: Copernicus GLO-90 relief. Colour: change in IMERG days with ≥ 1 mm, 2018-24 vs 2001-18, per 0.1° "
                "cell. Circles: {g} GHCN-D rain gauges with their own change, on the same scale.",
           "k": "IMERG falls more than the gauge at {a} of {g} · median IMERG {mi:+.1f} pp, gauges {mp:+.1f} pp",
           "lo": "loses days", "hi": "gains days", "u": "percentage points of rainy days",
           "f": "Data: NASA GPM IMERG V07 Final daily · NOAA GHCN-D · Copernicus GLO-90 (ESA/Airbus, AWS Open Data). "
                "Predictions registered before computing. Stellar Horizons, NASA Space Apps 2026."},
}


def teselas(c):
    import rasterio
    from rasterio.merge import merge
    DEM.mkdir(parents=True, exist_ok=True)
    fs = []
    for la in c["lat"]:
        for lo in c["lon"]:
            n = f"Copernicus_DSM_COG_30_N{la:02d}_00_W{lo:03d}_00_DEM"
            f = DEM / f"{n}.tif"
            if not f.exists():
                try:
                    with urllib.request.urlopen(f"https://copernicus-dem-90m.s3.amazonaws.com/{n}/{n}.tif", timeout=300) as r:
                        f.write_bytes(r.read())
                except Exception as e:  # noqa: BLE001 — teselas solo de mar: el bucket no las publica (404)
                    print("sin tesela", n, getattr(e, "code", e))
                    continue
            fs.append(f)
    src = [rasterio.open(f) for f in fs]
    lon0, lat0, lon1, lat1 = c["bbox"]
    Z, tr = merge(src, bounds=(lon0, lat0, lon1, lat1), res=(1 / 240, 1 / 240), nodata=0)
    for s in src:
        s.close()
    Z = Z[0].astype(float)
    lat = tr.f + tr.e * (np.arange(Z.shape[0]) + 0.5)
    lon = tr.c + tr.a * (np.arange(Z.shape[1]) + 0.5)
    return Z, lat, lon


def cambio_celdas(c):
    P, dias, lat, lon = imerg(c["ddir"], c["bbox"])
    a, b = dias < pd.Timestamp(CORTE), dias >= pd.Timestamp(CORTE)
    fa = np.nanmean(np.where(np.isfinite(P[a]), P[a] >= 1.0, np.nan), axis=0)
    fb = np.nanmean(np.where(np.isfinite(P[b]), P[b] >= 1.0, np.nan), axis=0)
    return 100 * (fb - fa), lat, lon


def dibujar(isla, c, Z, zl, zo, D, il, io, T, lang):
    t = TXT[lang]
    g = len(T)
    d1 = T["cambio_imerg_pp_1.0"] - T["cambio_pluvio_pp_1.0"]
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor=BG)
    ax = fig.add_axes([0.03, 0.12, 0.94, 0.70], facecolor=BG)
    norm = TwoSlopeNorm(vcenter=0, vmin=-ESCALA, vmax=ESCALA)
    lon0, lat0, lon1, lat1 = c["bbox"]
    K, paso = c["K"], c["paso"]
    rows = np.arange(lat1, lat0, -paso)
    step = max(1, int(round(0.004 / (zo[1] - zo[0]))))
    xs_all = zo[::step]
    for k, la in enumerate(rows):
        i = int(np.argmin(np.abs(zl - la)))
        z = Z[i, ::step]
        land = z > 0
        if not land.any():
            continue
        y = la + np.where(land, z, 0) * K
        ri = int(np.argmin(np.abs(il - la)))
        vals = D[ri, np.array([int(np.argmin(np.abs(io - x))) for x in xs_all])]
        cols = CMAP(norm(np.nan_to_num(vals)))
        cols[~np.isfinite(vals), :3] = 0.45
        idx = np.flatnonzero(land)
        runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
        for r in runs:
            if r.size < 2:
                continue
            r = np.concatenate([[max(r[0] - 1, 0)], r, [min(r[-1] + 1, len(z) - 1)]])
            xs, ys = xs_all[r], y[r].copy()
            ys[0], ys[-1] = la, la
            ax.fill_between(xs, la - 0.0015, ys, color=BG, lw=0, zorder=10 + k)
            pts = np.column_stack([xs, ys])
            lc = LineCollection(np.stack([pts[:-1], pts[1:]], 1), colors=cols[r[:-1]], linewidths=1.0,
                                zorder=10.5 + k, capstyle="round")
            ax.add_collection(lc)
    # los pluviómetros, sobre el relieve, con su propio cambio
    for s in T.itertuples():
        zi = int(np.argmin(np.abs(zl - s.lat))); zj = int(np.argmin(np.abs(zo - s.lon)))
        yy = s.lat + max(0.0, Z[zi, zj]) * K
        ax.scatter([s.lon], [yy], s=110, c=[CMAP(norm(T.loc[s.Index, "cambio_pluvio_pp_1.0"]))], edgecolors=INK,
                   linewidths=1.6, zorder=900)
    for x, y, n in c["rotulos"]:
        ax.text(x, y, n, color=INK, fontsize=15, fontweight="600", ha="center", va="bottom", zorder=950,
                path_effects=[__import__("matplotlib.patheffects", fromlist=["x"]).withStroke(linewidth=4, foreground=BG)])
    if "nota" in c:
        x, y, nt = c["nota"]
        ax.annotate(nt[lang].replace("|", chr(10)), xy=(-155.9, 19.2), xytext=(-158.7, 19.3), color="#8fd3ff", fontsize=13.5,
                    ha="left", va="center", zorder=960, linespacing=1.35,
                    arrowprops=dict(arrowstyle="-", color="#8fd3ff", lw=1.0))
    ax.set_xlim(lon0 - 0.05, lon1 + 0.05)
    ax.set_ylim(lat0 - 0.05, lat1 + (0.25 if isla == "hawaii" else 0.12))
    ax.set_aspect(1 / np.cos(np.radians((lat0 + lat1) / 2)))
    ax.axis("off")
    n = c["nombre"][lang]
    fig.text(0.03, 0.93, c.get("titulo", {}).get(lang) or t["t"].format(n=n), color=INK, fontsize=34, fontweight="bold", va="top")
    fig.text(0.03, 0.865, t["k"].format(a=int((d1 < 0).sum()), g=g, mi=T["cambio_imerg_pp_1.0"].median(),
                                        mp=T["cambio_pluvio_pp_1.0"].median()), color="#ffb340", fontsize=18, va="top")
    # leyenda de color
    cax = fig.add_axes([0.03, 0.075, 0.26, 0.018])
    gr = np.linspace(-ESCALA, ESCALA, 256)[None, :]
    cax.imshow(gr, aspect="auto", cmap=CMAP, norm=norm, extent=(-ESCALA, ESCALA, 0, 1))
    cax.set_yticks([]); cax.set_xticks([-ESCALA, -6, 0, 6, ESCALA])
    cax.set_xticklabels([f"−{ESCALA:.0f}", "−6", "0", "+6", f"+{ESCALA:.0f}"], color=MUTED, fontsize=12)
    cax.tick_params(colors=MUTED, length=0)
    for sp in cax.spines.values():
        sp.set_visible(False)
    fig.text(0.03, 0.105, f"← {t['lo']}", color="#ff9f0a", fontsize=13, va="bottom")
    fig.text(0.29, 0.105, f"{t['hi']} →", color="#28a0f0", fontsize=13, va="bottom", ha="right")
    fig.text(0.03, 0.035, t["u"], color=MUTED, fontsize=12)
    import textwrap
    fig.text(0.34, 0.112, chr(10).join(textwrap.wrap(t["s"].format(g=g), 125)), color=MUTED, fontsize=12.5, va="top",
             linespacing=1.4)
    fig.text(0.34, 0.03, chr(10).join(textwrap.wrap(t["f"], 150)), color=MUTED, fontsize=10.5, va="bottom",
             linespacing=1.4)
    FIG.mkdir(parents=True, exist_ok=True)
    f = FIG / f"crestas_{isla}_{lang}.png"
    fig.savefig(f, facecolor=BG)
    plt.close(fig)
    return f


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for isla, c in ISLAS.items():
        Z, zl, zo = teselas(c)
        D, il, io = cambio_celdas(c)
        T = pd.read_csv(c["res"])
        tierra = []
        for la, lo in zip(*np.nonzero(np.isfinite(D))):
            zi = np.abs(zl - il[la]) < 0.05
            zj = np.abs(zo - io[lo]) < 0.05
            if (Z[np.ix_(zi, zj)] > 0).mean() > 0.25:
                tierra.append(float(D[la, lo]))
        res[isla] = {"celdas_tierra": len(tierra), "mediana_cambio_imerg_celdas_tierra_pp": float(np.median(tierra)),
                     "celdas_tierra_que_bajan": int(np.sum(np.array(tierra) < 0)),
                     "pluviometros": int(len(T)), "figuras": []}
        for lang in ("es", "en"):
            res[isla]["figuras"].append(str(dibujar(isla, c, Z, zl, zo, D, il, io, T, lang).relative_to(ROOT)))
        print(isla, json.dumps(res[isla], ensure_ascii=False), flush=True)
    write_json(OUT / "resumen.json", res)


if __name__ == "__main__":
    main()
