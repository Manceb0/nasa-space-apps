"""Pérdida de cobertura arbórea (Hansen et al. 2013, Global Forest Change v1.13), solo descriptiva.

Bosque en 2000 = píxel (1″ ≈ 30 m) con treecover2000 ≥ 30 % (umbral habitual). Pérdida = lossyear 1..23
(2001-2023) sobre ese bosque. Área de cada píxel = (R·Δφ)·(R·Δλ·cos φ). Ninguna relación causal con la respuesta
del suelo: solo se describe qué pasó en los territorios comparados.
"""

from __future__ import annotations

import numpy as np

from .common import DATA

R = 6371.0088
TC_MIN = 30


def tile_paths():
    d = DATA / "hansen"
    ly = sorted(d.glob("*_lossyear_20N_080W.tif"))
    tc = sorted(d.glob("*_treecover2000_20N_080W.tif"))
    return (ly[-1], tc[-1]) if ly and tc else (None, None)


def read_box(lat0, lat1, lon0, lon1, decim: int = 1):
    import rasterio
    from rasterio.windows import from_bounds
    ly_p, tc_p = tile_paths()
    with rasterio.open(ly_p) as a, rasterio.open(tc_p) as b:
        w = from_bounds(lon0, lat0, lon1, lat1, a.transform).round_offsets().round_lengths()
        ly = a.read(1, window=w)[::decim, ::decim]
        tc = b.read(1, window=w)[::decim, ::decim]
        tr = a.window_transform(w)
    rows = np.arange(ly.shape[0]) * decim
    lat = tr.f + (rows + 0.5) * tr.e
    lon = tr.c + (np.arange(ly.shape[1]) * decim + 0.5) * tr.a
    return ly, tc, lat, lon, abs(tr.e) * decim, abs(tr.a) * decim


def summary(lat0, lat1, lon0, lon1, year1: int = 23) -> dict:
    ly, tc, lat, lon, dy, dx = read_box(lat0, lat1, lon0, lon1)
    area = (R * np.radians(dy)) * (R * np.radians(dx) * np.cos(np.radians(lat)))[:, None] * np.ones((1, lon.size))
    forest = tc >= TC_MIN
    lost = forest & (ly >= 1) & (ly <= year1)
    by_year = {2000 + y: float((area * (forest & (ly == y))).sum()) for y in range(1, year1 + 1)}
    f_km2 = float((area * forest).sum())
    l_km2 = float((area * lost).sum())
    return {"area_caja_km2": float(area.sum()), "bosque_2000_km2": f_km2,
            "cobertura_media_2000_pct": float((tc * area).sum() / area.sum()),
            "perdida_2001_2023_km2": l_km2, "perdida_pct_del_bosque_2000": 100 * l_km2 / f_km2 if f_km2 > 0 else np.nan,
            "perdida_por_anio_km2": by_year}


def loss_map(lat0, lat1, lon0, lon1, decim: int = 10):
    """Fracción de píxeles con pérdida 2001-2023 y cobertura 2000, a 10″ (~300 m) para el mapa."""
    ly, tc, lat, lon, dy, dx = read_box(lat0, lat1, lon0, lon1, decim=1)
    ny, nx = ly.shape[0] // decim, ly.shape[1] // decim
    L = ((ly[:ny * decim, :nx * decim] >= 1) & (ly[:ny * decim, :nx * decim] <= 23)
         & (tc[:ny * decim, :nx * decim] >= TC_MIN)).reshape(ny, decim, nx, decim).mean((1, 3))
    T = tc[:ny * decim, :nx * decim].reshape(ny, decim, nx, decim).mean((1, 3))
    la = lat[:ny * decim].reshape(ny, decim).mean(1)
    lo = lon[:nx * decim].reshape(nx, decim).mean(1)
    return L, T, la, lo
