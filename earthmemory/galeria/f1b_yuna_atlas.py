"""Pieza 1b · «Where the water was»: atlas de inundación OBSERVADA (MODIS MCDWD) en la cuenca del Yuna.

(a) Pequeños múltiplos, uno por evento del catálogo (results/yuna/catalogo_eventos.csv, 15), en el orden del tiempo:
    cuenca sobre sombreado de relieve (Copernicus DEM), ríos HydroRIVERS, presa de Hatillo, Cotuí, Villa Riva y
    Arenoso, y los píxeles de 250 m de Flood_2Day_250m del día de máxima extensión (dia_max_yuna del motor Yuna).
    Clase 3 (inundación inusual) = color fuerte; 2 (recurrente) = tenue; 1 (agua de referencia) = muy tenue;
    255 ese día (nube, sin pasada) = trama; 255 en TODOS los días bajados (máscara fija del producto: sombra de
    relieve / filtro de terreno alto) = velo gris liso. Etiqueta: fecha, km² de clase 3 y % sin ver (de
    results/yuna/mcdwd_por_evento.csv y mcdwd_diario_zonas.csv; los km² se recalculan y se comprueban).
(b) Pieza hermana: en cuántos eventos fue «inundación inusual» cada píxel, en cualquier día de su ventana.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.colors import LightSource, ListedColormap, BoundaryNorm
import matplotlib as mpl

from . import datos as D
from .estilo import OI, SLIDE, cabecera, entrada, guardar, lienzo, pie, procedencia, theme_list

NOMBRE_A = "01b_yuna_flood_atlas"
NOMBRE_B = "01c_yuna_flood_recurrence"
DMC = Path("data/yuna/mcdwd")
CAPA = "Flood_2Day_250m"
FUENTE = ("Data: NASA LANCE/LAADS MODIS MCDWD_L3 C6.1 Flood_2Day_250m (doi:10.5067/MODIS/MCDWD_L3.061) · Copernicus "
          "GLO-90 DEM · HydroSHEDS/HydroRIVERS · event catalogue and basin from the Stellar Horizons Yuna engine.")
PUEBLOS = ("Cotuí", "Villa Riva", "Arenoso")


def _yuna():
    from ..yuna import common as yc
    from ..yuna import mcdwd as ym
    return yc, ym


def mascara_cuenca(ym, geom: dict) -> np.ndarray:
    from rasterio.features import rasterize
    h, w = ym.shape()
    return rasterize([(geom, 1)], out_shape=(h, w), transform=ym.transform(), all_touched=False) == 1


def cargar() -> dict:
    yc, ym = _yuna()
    gj = json.loads((D.R_YUNA / "cuencas_yuna.geojson").read_text(encoding="utf-8"))
    geom = next(f["geometry"] for f in gj["features"] if f["properties"]["zona"] == "yuna")
    M = mascara_cuenca(ym, geom)
    cat = pd.read_csv(D.R_YUNA / "catalogo_eventos.csv")
    pe = pd.read_csv(D.R_YUNA / "mcdwd_por_evento.csv").set_index("id")
    dz = pd.read_csv(D.R_YUNA / "mcdwd_diario_zonas.csv", parse_dates=["fecha"])
    dz = dz[dz["capa"] == CAPA].set_index("fecha")
    dp = pd.read_csv(D.R_YUNA / "mcdwd_dias_pedidos.csv", parse_dates=["fecha"])
    dp = dp[dp["motivo"] == "evento"]
    files = sorted(DMC.glob("mcdwd_*.npz"))
    fijo = None
    for p in files:                       # misma definición que yuna.mcdwd.siempre_enmascarado
        a = np.load(p)[CAPA] == 255
        fijo = a if fijo is None else (fijo & a)
    ids = [i for i in cat["id"] if i in pe.index]
    ev = []
    for i in ids:
        r = pe.loc[i]
        dias = [d for d in dp.loc[dp["id"] == i, "fecha"] if (DMC / f"mcdwd_{d:%Y%m%d}.npz").exists()]
        if isinstance(r["dia_max_yuna"], str):
            dia = pd.Timestamp(r["dia_max_yuna"])
        else:                              # sin observación útil: el día con menos píxeles sin ver
            dia = min(dias, key=lambda d: dz.loc[d, "insuf_yuna"] if d in dz.index else 9)
        A = np.load(DMC / f"mcdwd_{dia:%Y%m%d}.npz")[CAPA]
        km2 = float(((A == 3) & M).sum() * ym.PX_KM2)
        ref = r["inund_km2_max_yuna"]
        if np.isfinite(ref):
            assert abs(km2 - ref) <= max(0.02 * ref, 2 * ym.PX_KM2), (i, km2, ref)
        unseen = float(dz.loc[dia, "insuf_yuna"]) if dia in dz.index else np.nan
        # recurrencia: ¿clase 3 en algún día de la ventana? ¿se vio alguna vez el píxel?
        any3 = np.zeros(M.shape, bool)
        seen = np.zeros(M.shape, bool)
        for d in dias:
            B = np.load(DMC / f"mcdwd_{d:%Y%m%d}.npz")[CAPA]
            any3 |= B == 3
            seen |= B != 255
        nombre = cat.loc[cat["id"] == i, "nombre"].iloc[0]
        ev.append({"id": i, "dia": dia, "A": A, "km2_clase3": km2, "km2_ref_csv": ref, "sin_ver": unseen,
                   "any3": any3, "seen": seen, "n_dias": len(dias), "nombre": nombre})
    lon0, lat0, lon1, lat1 = ym.WIN
    rivers = json.loads((D.R_YUNA / "rios_hydrorivers.geojson").read_text(encoding="utf-8"))["features"]
    ring, _ = D.yuna_ring()
    pts = {k: yc.PUNTOS[k] for k in PUEBLOS}
    return {"M": M, "fijo": fijo, "ev": ev, "win": ym.WIN, "px_km2": ym.PX_KM2, "rivers": rivers, "ring": ring,
            "pts": pts, "hatillo": (yc.HATILLO["lat"], yc.HATILLO["lon"]), "n_archivos": len(files)}


def hillshade(win) -> tuple[np.ndarray, tuple]:
    dem = D.dem_nativo()
    lon0, lat0, lon1, lat1 = win
    i = (dem["lat"] >= lat0) & (dem["lat"] <= lat1)
    j = (dem["lon"] >= lon0) & (dem["lon"] <= lon1)
    Z = dem["Z"][np.ix_(i, j)]
    Z = np.where(np.isfinite(Z), Z, 0)
    lat = dem["lat"][i]
    if lat[0] < lat[-1]:
        Z = Z[::-1]
    ls = LightSource(azdeg=315, altdeg=40)
    dy = 110574 / 300
    dx = 111320 * np.cos(np.radians(19.15)) / 300
    hs = ls.hillshade(Z, vert_exag=2.0, dx=dx, dy=dy)
    return hs, (dem["lon"][j][0], dem["lon"][j][-1], min(lat), max(lat)), Z


def veil(t):
    return (0.02, 0.025, 0.03, 0.66) if t["name"] == "dark" else (1.0, 1.0, 1.0, 0.68)


def veil_swatch(t):
    return "#1f2227" if t["name"] == "dark" else "#eef0f2"


def _fondo(ax, t, H, win, ring, rivers, dim=1.0):
    hs, ext, Z = H
    lo = (0.10 if t["name"] == "dark" else 0.55) * dim
    hi = (0.42 if t["name"] == "dark" else 0.97) * (dim if t["name"] == "dark" else 1)
    g = lo + (hi - lo) * hs
    g = np.where(Z <= 0, np.nan, g)
    cm = mpl.colors.LinearSegmentedColormap.from_list("hs", [(0, 0, 0), (1, 1, 1)])
    ax.imshow(g, extent=ext, cmap=cm, vmin=0, vmax=1, interpolation="bilinear", zorder=0)
    ax.set_facecolor(t["bg"])
    for f in rivers:
        p = f["properties"]
        if p.get("UPLAND_SKM", 0) < 150:
            continue
        c = np.array(f["geometry"]["coordinates"])
        lw = 0.25 + 0.55 * min(1, np.log10(p["UPLAND_SKM"] / 150) / np.log10(40))
        ax.plot(c[:, 0], c[:, 1], color="#c3c8cf" if t["name"] == "dark" else "#59606b", lw=lw, alpha=0.55, zorder=3)
    ax.plot(ring[:, 0], ring[:, 1], color=t["ink"], lw=0.7, zorder=5)
    lon0, lat0, lon1, lat1 = win
    ax.set_xlim(lon0, lon1)
    ax.set_ylim(lat0, lat1)
    ax.set_aspect(1 / np.cos(np.radians(19.15)))
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def colores(t):
    base = OI["sky"] if t["name"] == "dark" else OI["blue"]
    rgb = mpl.colors.to_rgb(base)
    return {3: (*rgb, 1.0), 2: (*rgb, 0.45), 1: (*rgb, 0.22)}


def _capa(ax, t, A, M, fijo, win):
    lon0, lat0, lon1, lat1 = win
    ext = (lon0, lon1, lat0, lat1)
    col = colores(t)
    rgba = np.zeros(A.shape + (4,))
    for k in (1, 2, 3):
        rgba[(A == k) & M] = col[k]
    veil_ = np.zeros(A.shape + (4,))
    veil_[fijo & M] = veil(t)
    ax.imshow(veil_, extent=ext, interpolation="nearest", zorder=1)
    nub = (A == 255) & ~fijo & M
    if nub.any():
        ny, nx = A.shape
        X = np.linspace(lon0, lon1, nx)
        Y = np.linspace(lat1, lat0, ny)
        mpl.rcParams["hatch.color"] = "#b9bec6" if t["name"] == "dark" else "#7a808a"
        mpl.rcParams["hatch.linewidth"] = 0.35
        ax.contourf(X, Y, nub.astype(float), levels=[0.5, 1.5], colors="none", hatches=["//////"], zorder=2)
    ax.imshow(rgba, extent=ext, interpolation="nearest", zorder=4)


def _marcas(ax, t, S, etiquetas: bool, fs=6.0):
    hy, hx = S["hatillo"]
    ax.plot(hx, hy, marker="v", ms=4.2 if etiquetas else 3, color=OI["orange"], mec=t["bg"], mew=0.4, zorder=7)
    for k, (la, lo) in S["pts"].items():
        ax.plot(lo, la, "o", ms=2.6 if etiquetas else 1.8, color=t["ink"], mec=t["bg"], mew=0.4, zorder=7)
    if etiquetas:
        big = fs >= 8
        ax.text(hx - (0.03 if big else 0.02), hy - (0.03 if big else 0.025), "Hatillo dam", fontsize=fs, color=OI["orange"],
                ha="center" if big else "right", va="top", zorder=8)
        off = {"Cotuí": (0.02, -0.04, "left"), "Villa Riva": (-0.02, 0.035, "right"), "Arenoso": (0.02, 0.035, "left")}
        for k, (la, lo) in S["pts"].items():
            dx, dy, ha = off[k]
            ax.text(lo + dx, la + dy, k, fontsize=fs, color=t["ink"], ha=ha, va="center", zorder=8)


def _escala(ax, t, win, km=20, fs=6, derecha=False):
    lon0, lat0, lon1, lat1 = win
    dlon = km / (111.32 * np.cos(np.radians(19.15)))
    x0, y0 = ((lon1 - 0.04 - dlon) if derecha else (lon0 + 0.04)), lat0 + 0.05
    ax.plot([x0, x0 + dlon], [y0, y0], color=t["ink"], lw=1.2, solid_capstyle="butt", zorder=9)
    ax.text(x0 + dlon / 2, y0 + 0.02, f"{km} km", ha="center", va="bottom", fontsize=fs, color=t["ink"], zorder=9)


def _clave(fig, t, x, y, fs=9.5, dx=0.0):
    col = colores(t)
    items = [(col[3], "Unusual flood (class 3)"), (col[2], "Recurrent flood (2)"), (col[1], "Reference water (1)")]
    from matplotlib.patches import Rectangle
    for c, lab in items:
        fig.patches.append(Rectangle((x, y - 0.011), 0.013, 0.022, transform=fig.transFigure, fc=c, ec="none"))
        tt = fig.text(x + 0.018, y, lab, fontsize=fs, va="center", color=t["ink"])
        fig.canvas.draw()
        x = tt.get_window_extent().transformed(fig.transFigure.inverted()).x1 + 0.02
    vc = veil_swatch(t)
    fig.patches.append(Rectangle((x, y - 0.011), 0.013, 0.022, transform=fig.transFigure, fc="none",
                                 ec="#b9bec6" if t["name"] == "dark" else "#7a808a", hatch="//////", lw=0.4))
    tt = fig.text(x + 0.018, y, "Not seen that day (cloud / no pass)", fontsize=fs, va="center", color=t["ink"])
    fig.canvas.draw()
    x = tt.get_window_extent().transformed(fig.transFigure.inverted()).x1 + 0.02
    fig.patches.append(Rectangle((x, y - 0.011), 0.013, 0.022, transform=fig.transFigure, fc=vc, ec=t["muted"], lw=0.4))
    tt = fig.text(x + 0.018, y, "Never mapped (product's fixed terrain mask)", fontsize=fs, va="center", color=t["ink"])
    fig.canvas.draw()
    return tt.get_window_extent().transformed(fig.transFigure.inverted()).x1


def atlas(t, S, H):
    fig = lienzo(t, SLIDE)
    ev = S["ev"]
    nc, nr = 5, 3
    x0, x1, y0, y1 = 0.03, 0.985, 0.095, 0.79
    gw, gh = (x1 - x0) / nc, (y1 - y0) / nr
    for k, e in enumerate(ev):
        r, c = divmod(k, nc)
        ax = fig.add_axes([x0 + c * gw + 0.003, y1 - (r + 1) * gh + 0.028, gw - 0.006, gh - 0.034])
        _fondo(ax, t, H, S["win"], S["ring"], S["rivers"])
        _capa(ax, t, e["A"], S["M"], S["fijo"], S["win"])
        _marcas(ax, t, S, etiquetas=(k == 0), fs=5.6)
        if k == 0:
            _escala(ax, t, S["win"], fs=5.6)
        sv = e["sin_ver"]
        no_obs = (not np.isfinite(e["km2_ref_csv"]))
        top = f"{e['dia']:%d %b %Y}"
        ax.text(0.0, 1.015, top, transform=ax.transAxes, fontsize=8.6, fontweight="bold", color=t["ink"],
                ha="left", va="bottom")
        ax.text(1.0, 1.015, f"event {e['id']}", transform=ax.transAxes, fontsize=6.8, color=t["muted"],
                ha="right", va="bottom")
        if no_obs:
            msg = f"no clear view · {sv * 100:.1f}% unseen"
        else:
            k2 = e['km2_clase3']
            ks = '<1' if 0 < k2 < 1 else f'{k2:.0f}'
            msg = f"{ks} km² unusual · {sv * 100:.0f}% unseen"
        ax.text(0.985, 0.04, msg, transform=ax.transAxes, fontsize=7.4, color=t["ink"], ha="right", va="bottom",
                zorder=10, bbox=dict(boxstyle="square,pad=0.25", fc=t["bg"], ec="none", alpha=0.78))
    cabecera(fig, t, "Where the water was: 15 floods in the Yuna basin, seen from orbit",
             "MODIS 250 m flood map (2-day composite) on the day of largest unusual-flood extent in each catalogued "
             "event, 2003–2025.\nSame frame and scale in every panel; hatching shows where the satellite could not "
             "look that day.", ts=21, ss=11.5, y=0.955)
    _clave(fig, t, 0.045, 0.815, fs=9.2)
    pie(fig, t, FUENTE + "\nkm² = class-3 pixels inside the basin; % unseen = share of the basin's mappable pixels "
                "flagged 'insufficient data' that day. Optical sensor: it cannot see under cloud or dense canopy,\nand "
                "floods shorter than the composite can be missed. Orange ▼ = Hatillo dam; dots = towns.  ·  Analysis: "
                "Stellar Horizons, NASA Space Apps 2026", size=7.0, y=0.012)
    return fig


def recurrencia(t, S, H):
    fig = lienzo(t, SLIDE)
    ev = S["ev"]
    M = S["M"]
    cnt = np.sum([e["any3"] for e in ev], 0)
    seen = np.sum([e["seen"] for e in ev], 0)
    ax = fig.add_axes([0.355, 0.06, 0.63, 0.88])
    ZOOM = (-70.30, 18.93, -69.33, 19.45)          # bajo Yuna: Hatillo → desembocadura (mismo píxel, más grande)
    _fondo(ax, t, H, ZOOM, S["ring"], S["rivers"], dim=0.75)
    lon0, lat0, lon1, lat1 = S["win"]
    vc = veil_swatch(t)
    veil_ = np.zeros(M.shape + (4,))
    veil_[S["fijo"] & M] = veil(t)
    ax.imshow(veil_, extent=(lon0, lon1, lat0, lat1), interpolation="nearest", zorder=1)
    ax.set_xlim(ZOOM[0], ZOOM[2])
    ax.set_ylim(ZOOM[1], ZOOM[3])
    kmax = int(cnt[M].max())
    base = mpl.colormaps["viridis"]
    xs = np.linspace(0.30, 1.0, kmax) if t["name"] == "dark" else np.linspace(0.85, 0.0, kmax)
    cm = ListedColormap([base(x) for x in xs])
    norm = BoundaryNorm(np.arange(0.5, kmax + 1.5), cm.N)
    C = np.where((cnt >= 1) & M, cnt, np.nan)
    ax.imshow(C, extent=(lon0, lon1, lat0, lat1), cmap=cm, norm=norm, interpolation="nearest", zorder=4)
    _marcas(ax, t, S, etiquetas=True, fs=9)
    _escala(ax, t, ZOOM, km=10, fs=8.5, derecha=True)
    mapp = M & ~S["fijo"]
    frac_vista = [float(e["seen"][mapp].mean()) for e in ev]
    n_ev_obs = sum(f >= 0.5 for f in frac_vista)
    px = S["px_km2"]
    area = {k: float(((cnt >= k) & M).sum() * px) for k in range(1, kmax + 1)}
    # textos
    cabecera(fig, t, "The plain that floods\nagain and again", "", x=0.035, y=0.93, ts=24)
    fig.text(0.035, 0.735,
             f"Each 250 m pixel of the lower Yuna basin,\ncoloured by how many of the {len(ev)} catalogued\n"
             f"flood events (2003–2025) MODIS flagged it\nas unusual flood (class 3) on any day of the\n"
             f"event window (2-day composite).", fontsize=11.2, color=t["muted"], va="top", linespacing=1.45)
    y = 0.445
    fig.text(0.035, y, f"{area[1]:.0f} km²", fontsize=26, fontweight="bold", color=t["ink"], va="bottom")
    fig.text(0.035, y - 0.012, "of the basin flagged in at least one event", fontsize=10.5, color=t["muted"], va="top")
    k3 = min(3, kmax)
    fig.text(0.035, y - 0.1, f"{area[k3]:.0f} km²", fontsize=26, fontweight="bold", color=t["ink"], va="bottom")
    fig.text(0.035, y - 0.112, f"in {k3} or more events (maximum {kmax} of {len(ev)})", fontsize=10.5,
             color=t["muted"], va="top")
    cax = fig.add_axes([0.035, 0.225, 0.25, 0.026])
    cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cm), cax=cax, orientation="horizontal",
                      ticks=list(range(1, kmax + 1)))
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=9, length=0, colors=t["muted"])
    cb.ax.set_title("events with unusual flood at the pixel", fontsize=9.5, color=t["ink"], loc="left", pad=5)
    from matplotlib.patches import Rectangle
    fig.patches.append(Rectangle((0.035, 0.148), 0.014, 0.024, transform=fig.transFigure, fc=vc, ec=t["muted"], lw=0.4))
    fig.text(0.054, 0.16, "never mapped by the product (fixed terrain mask)", fontsize=9, color=t["ink"], va="center")
    pie(fig, t, "Data: NASA MODIS MCDWD_L3 C6.1 Flood_2Day_250m · Copernicus GLO-90 DEM · HydroRIVERS.\n"
                f"Only {n_ev_obs} of {len(ev)} events had ≥ 50% of the mappable basin seen at least once:\n"
                "cloud hides floods, so each pixel's count is a lower bound. Lower basin shown;\nkm² over the whole "
                "basin.  ·  Analysis: Stellar Horizons, NASA Space Apps 2026", x=0.035, y=0.022, size=7.3)
    return fig, {"km2_por_umbral_eventos": area, "max_eventos": kmax, "eventos_con_50pc_vistos": n_ev_obs,
                 "fraccion_vista_por_evento": dict(zip([e["id"] for e in ev], frac_vista)),
                 "pixeles_vistos_alguna_vez": int(((seen > 0) & M).sum())}


def run(temas=None) -> dict:
    S = cargar()
    H = hillshade(S["win"])
    files = []
    nums = None
    for t in theme_list(temas):
        files += guardar(atlas(t, S, H), NOMBRE_A, t,
                         "Small multiples of MODIS MCDWD 250 m flood maps for 15 catalogued Yuna basin flood events.",
                         FUENTE)
        fig, nums = recurrencia(t, S, H)
        files += guardar(fig, NOMBRE_B, t, "Per-pixel count of events with MODIS unusual flood (class 3), Yuna basin.",
                         FUENTE)
    tab = pd.DataFrame([{k: e[k] for k in ("id", "dia", "km2_clase3", "km2_ref_csv", "sin_ver", "n_dias")} for e in S["ev"]])
    tab.to_csv(D.DATOS / "yuna_atlas_eventos.csv", index=False)
    numeros = {"eventos": tab.assign(dia=tab["dia"].astype(str)).to_dict(orient="records"), **(nums or {}),
               "fraccion_cuenca_siempre_enmascarada": float((S["fijo"] & S["M"]).sum() / S["M"].sum())}
    ent = [entrada("data/yuna/mcdwd", "recortes diarios MCDWD (npz) del motor Yuna"),
           entrada("results/yuna/mcdwd_por_evento.csv", "día de máxima extensión y km² de control"),
           entrada("results/yuna/mcdwd_diario_zonas.csv", "% sin ver por día"),
           entrada("results/yuna/mcdwd_dias_pedidos.csv", "días de cada ventana de evento"),
           entrada("results/yuna/catalogo_eventos.csv", "catálogo de 15 eventos"),
           entrada("results/yuna/cuencas_yuna.geojson", "cuenca"),
           entrada("results/yuna/rios_hydrorivers.geojson", "ríos (UPLAND ≥ 150 km²)"),
           entrada("data/nacional_hr/derivados/nativas.npz", "DEM Copernicus 1/300° para sombreado")]
    big = max(S["ev"], key=lambda e: e["km2_clase3"])
    alt_en = (f"Fifteen small maps of the Yuna basin (5 by 3, in time order 2003-2025) over shaded relief, each showing "
              f"MODIS 250 m flood classes on the day of largest extent; unusual flood in strong blue, cloud-hidden areas "
              f"hatched, permanently unmapped mountains veiled grey. The largest is {big['dia']:%d %b %Y} with "
              f"{big['km2_clase3']:.0f} km² of unusual flood, concentrated in the lower Yuna plain near Villa Riva and "
              f"Arenoso. A companion map counts, per pixel, how many events flagged unusual flood.")
    alt_es = (f"Quince mapas pequeños de la cuenca del Yuna (5 × 3, en orden 2003-2025) sobre sombreado de relieve con las "
              f"clases de inundación MODIS de 250 m del día de máxima extensión; inundación inusual en azul fuerte, lo "
              f"tapado por nubes con trama y las montañas que el producto nunca mapea con velo gris. El mayor es el "
              f"{big['dia']:%d-%m-%Y} con {big['km2_clase3']:.0f} km² de inundación inusual, en la llanura del Bajo Yuna "
              f"(Villa Riva, Arenoso). Un mapa hermano cuenta en cuántos eventos cada píxel fue inundación inusual.")
    procedencia(NOMBRE_A, "Where the water was (Yuna flood atlas + recurrence)", "Dónde estuvo el agua (atlas del Yuna)",
                files, ent, "Para cada evento: npz del día dia_max_yuna (o, sin observación, el día con menos píxeles sin "
                "ver), capa Flood_2Day_250m; máscara de cuenca = rasterize(cuenca 'yuna', all_touched=False) en la rejilla "
                "MCDWD (yuna.mcdwd.transform); km² = nº clase 3 × PX_KM2, comprobado contra mcdwd_por_evento.csv (±2 %). "
                "Máscara fija = 255 en todos los npz descargados (yuna.mcdwd.siempre_enmascarado). Recurrencia = nº de "
                "eventos con clase 3 en cualquier día de la ventana pedida.", numeros, alt_en, alt_es,
                ["Sensor óptico: no ve bajo nubes ni dosel; una crecida más corta que el compuesto puede perderse.",
                 "El recuento por píxel es un mínimo (días nublados).",
                 "Eventos 2025 fuera del periodo 2001-2024 del resto del análisis (están en el catálogo del motor Yuna)."])
    return {"archivos": files, "numeros": numeros}
