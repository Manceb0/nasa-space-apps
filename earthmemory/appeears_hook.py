"""Gancho para el pedido nacional de AppEEARS (ID 8ad4ac19-6b4c-4445-8443-2c4a4fc7f928, pendiente el 2026-11-14):
MOD13A3 v061 (NDVI/EVI mensual 1 km + calidad) y MOD17A3HGF v061 (NPP anual 500 m), polígono ADM0 de RD,
2001-2024.

Cuando lleguen, se dejan los GeoTIFF tal cual los entrega AppEEARS en data/appeears/nacional/ (cualquier
subcarpeta). Este módulo:
- reconoce los nombres de AppEEARS: <PRODUCTO>.<versión>_<capa>_doy<AAAADDD>_aid0001.tif;
- MOD13A3: NDVI y EVI (factor 0.0001, relleno −3000) y solo píxeles con pixel_reliability 0 (bueno) o
  1 (marginal); el resto queda NaN;
- agrega los píxeles de 1 km a cada celda GLDAS 0.25° (media de los píxeles cuyo centro cae en la celda,
  exige ≥ 30 % de píxeles válidos) → tabla mes × celda; así NDVI/EVI entran como respuestas más.
NPP anual (MOD17A3HGF) se lee aparte con annual_npp() para contexto (no entra al motor mensual).
Si no hay archivos, devuelve {} y el motor sigue sin vegetación (queda escrito en corrida.json).
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from .grid import Grid

PAT = re.compile(r"(?P<prod>MOD13A3|MOD17A3HGF)\.(?P<ver>\d{3})_(?P<layer>.+?)_doy(?P<y>\d{4})(?P<d>\d{3})_aid\d+\.tif$")
MIN_VALID = 0.30


def _index(root: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(Path(root).rglob("*.tif")) if Path(root).exists() else []:
        m = PAT.search(f.name)
        if m:
            t = pd.Timestamp(int(m["y"]), 1, 1) + pd.Timedelta(days=int(m["d"]) - 1)
            rows.append({"archivo": f, "producto": m["prod"], "capa": m["layer"], "fecha": t.to_period("M").to_timestamp()})
    return pd.DataFrame(rows)


def _read(path: Path):
    import rasterio
    with rasterio.open(path) as src:
        a = src.read(1).astype("float64")
        nod = src.nodata
        tr = src.transform
    if nod is not None:
        a[a == nod] = np.nan
    rows, cols = np.indices(a.shape)
    xs = tr.c + (cols + 0.5) * tr.a + (rows + 0.5) * tr.b
    ys = tr.f + (cols + 0.5) * tr.d + (rows + 0.5) * tr.e
    return a, ys, xs


def _to_cells(a, ys, xs, g: Grid) -> dict:
    out = {}
    half = g.res / 2
    for cid, (la, lo) in zip(g.ids(), zip(*g.mesh())):
        m = (np.abs(ys - la) <= half) & (np.abs(xs - lo) <= half)
        n = int(m.sum())
        if n == 0:
            continue
        v = a[m]
        ok = np.isfinite(v)
        if ok.mean() >= MIN_VALID:
            out[cid] = float(v[ok].mean())
    return out


def load_monthly(root: Path, g: Grid, index: pd.DatetimeIndex) -> dict:
    idx = _index(root)
    if idx.empty:
        return {}
    out = {}
    v = idx[idx["producto"] == "MOD13A3"]
    for var, layer in (("NDVI", "1_km_monthly_NDVI"), ("EVI", "1_km_monthly_EVI")):
        sel = v[v["capa"] == layer]
        rel = v[v["capa"] == "1_km_monthly_pixel_reliability"].set_index("fecha")["archivo"]
        recs = {}
        for _, r in sel.iterrows():
            a, ys, xs = _read(r["archivo"])
            a = np.where(a == -3000, np.nan, a * 0.0001)
            if r["fecha"] in rel.index:
                q, _, _ = _read(rel.loc[r["fecha"]])
                a = np.where(np.isin(q, [0, 1]), a, np.nan)
            recs[r["fecha"]] = _to_cells(a, ys, xs, g)
        if recs:
            out[var] = pd.DataFrame(recs).T.sort_index().reindex(index)
    return out


def annual_npp(root: Path, g: Grid) -> pd.DataFrame:
    idx = _index(root)
    sel = idx[(idx["producto"] == "MOD17A3HGF") & (idx["capa"] == "Npp_500m")] if not idx.empty else idx
    recs = {}
    for _, r in sel.iterrows():
        a, ys, xs = _read(r["archivo"])
        a = np.where(a >= 32700, np.nan, a * 0.0001)  # kg C m-2 año-1; 32761-32767 = clases de relleno
        recs[r["fecha"].year] = _to_cells(a, ys, xs, g)
    return pd.DataFrame(recs).T.sort_index() if recs else pd.DataFrame()
