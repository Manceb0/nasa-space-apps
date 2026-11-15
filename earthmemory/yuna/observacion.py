"""Agua observada (JRC GSW Monthly Water History v1.4, Landsat 30 m, 2001-2020) en el embalse de Hatillo y en la
llanura del Bajo Yuna. Es OBSERVACIÓN (clasificación de imágenes), independiente de la lluvia, pero:
- un mes con nubes deja píxeles «sin dato» (0); se informa la fracción válida y solo se usan meses con ≥ 30 %;
- el arroz inundado por riego es agua «normal» de temporada: la anomalía se mide contra la climatología del mismo mes;
- 30 m y paso de Landsat cada 16 días (8 con dos satélites): una crecida de 2-4 días puede no quedar registrada.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .common import DATA, HR
from .download import GSW_WIN

RES_GSW = 0.00025
# Caja del embalse de Hatillo (aguas arriba de la cortina; se intersecta con la zona alto_hatillo)
CAJA_EMBALSE = (-70.40, 18.92, -70.185, 19.08)


def grid_shape() -> tuple[int, int]:
    lon0, lat0, lon1, lat1 = GSW_WIN
    return int(round((lat1 - lat0) / RES_GSW)), int(round((lon1 - lon0) / RES_GSW))


def transform():
    from rasterio.transform import from_origin
    lon0, lat0, lon1, lat1 = GSW_WIN
    return from_origin(lon0, lat1, RES_GSW, RES_GSW)


def ocurrencia() -> tuple[np.ndarray, np.ndarray]:
    files = sorted((DATA / "gsw_mensual").glob("gsw_*.npz"))
    h, w = grid_shape()
    agua = np.zeros((h, w), np.int32)
    val = np.zeros((h, w), np.int32)
    for p in files:
        a = np.load(p)["agua"][:h, :w]
        agua[: a.shape[0], : a.shape[1]] += a == 2
        val[: a.shape[0], : a.shape[1]] += a > 0
    return agua, val


def dem_window() -> np.ndarray:
    import rasterio
    from rasterio.warp import Resampling, reproject
    h, w = grid_shape()
    dst = np.full((h, w), np.nan, np.float32)
    for f in sorted((HR / "dem").glob("Copernicus_DSM_COG_30_*_DEM.tif")):
        with rasterio.open(f) as s:
            b = s.bounds
            lon0, lat0, lon1, lat1 = GSW_WIN
            if b.right < lon0 or b.left > lon1 or b.top < lat0 or b.bottom > lat1:
                continue
            tmp = np.full((h, w), np.nan, np.float32)
            reproject(s.read(1).astype(np.float32), tmp, src_transform=s.transform, src_crs=s.crs,
                      dst_transform=transform(), dst_crs="EPSG:4326", resampling=Resampling.nearest,
                      src_nodata=s.nodata, dst_nodata=np.nan)
            dst = np.where(np.isnan(dst), tmp, dst)
    return dst


def mascaras(zonas: dict) -> dict:
    from rasterio.features import rasterize
    from shapely.geometry import box
    h, w = grid_shape()
    tr = transform()
    agua, val = ocurrencia()
    occ = np.where(val > 0, agua / np.maximum(val, 1), np.nan)
    dem = dem_window()
    alto = rasterize([(zonas["alto_hatillo"].intersection(box(*CAJA_EMBALSE)), 1)], out_shape=(h, w), transform=tr) == 1
    bajo = rasterize([(zonas["bajo_yuna"], 1)], out_shape=(h, w), transform=tr) == 1
    embalse = alto & (occ >= 0.05)
    # llanura: Bajo Yuna bajo 20 m, sin agua permanente (mar, lagunas, cauce: ocurrencia ≥ 50 %)
    llanura = bajo & (dem < 20) & ~(occ >= 0.5)
    meta = {"embalse_px": int(embalse.sum()), "embalse_km2_max_posible": float(embalse.sum() * px_km2()),
            "llanura_px": int(llanura.sum()), "llanura_km2": float(llanura.sum() * px_km2()),
            "meses_gsw": int(len(list((DATA / "gsw_mensual").glob("gsw_*.npz"))))}
    return {"embalse": embalse, "llanura": llanura, "occ": occ, "dem": dem, "meta": meta}


def px_km2() -> float:
    return (RES_GSW * 110.574) * (RES_GSW * 111.32 * np.cos(np.radians(19.15)))


def anomalias(g: pd.DataFrame, k: str = "llanura", min_valid: float = 0.30) -> pd.DataFrame:
    """Fracción de agua entre píxeles válidos de la máscara k, contra la climatología del mismo mes (2001-2020)."""
    d = g[[f"gsw_validos_{k}", f"gsw_frac_agua_validos_{k}", f"gsw_agua_km2_{k}"]].copy()
    d.columns = ["validos", "frac", "km2_visto"]
    # área estimada = fracción de agua entre píxeles VÁLIDOS × área de la máscara (no castiga los meses con nubes)
    import json
    from .common import RES
    meta = json.loads((RES / "gsw_mascaras.json").read_text(encoding="utf-8"))
    area = meta["embalse_km2_max_posible"] if k == "embalse" else meta["llanura_km2"]
    d["km2"] = d["frac"] * area
    ok = d["validos"] >= min_valid
    d["usable"] = ok
    clim = d[ok].groupby(d[ok].index.month)["frac"]
    d["clim_mediana"] = d.index.month.map(clim.median())
    d["clim_p90"] = d.index.month.map(clim.quantile(0.9))
    d["anomalia"] = np.where(ok, d["frac"] - d["clim_mediana"], np.nan)
    # señal = sobre el p90 del mes Y al menos 1 punto porcentual más agua que la mediana (≈ 3.7 km² en la llanura)
    d["sobre_p90"] = ok & (d["frac"] > d["clim_p90"]) & (d["anomalia"] >= 0.01)
    return d
