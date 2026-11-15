"""SMAP L3 Enhanced (SPL3SMP_E V006): lectura del recorte de la RD, calidad por píxel y series para las pruebas.

Calidad (atributos del propio archivo):
- retrieval_qual_flag: bit 0 'Retrieval_recommended' (0 = calidad recomendada; 1 = no recomendada),
  bit 1 'Retrieval_attempted', bit 2 'Retrieval_success'. El valor 'recomendado' exige, entre otras cosas,
  contenido de agua de la vegetación (VWC) ≤ 5 kg/m² (guía de usuario SPL3SMP_E): en bosque denso de montaña el
  radiómetro de banda L ve poco el suelo y el retrieval se marca como no recomendado.
- surface_flag: bit 9 '9_km_mountainous_terrain', bit 10 '9_km_dense_vegetation', bit 2 coastal, bit 3 urban,
  bit 0 static water, bit 4 precipitation.
Se usa SOLO soil_moisture con bit 0 = 0 (recomendado) en el análisis principal; la sensibilidad usa todos los
retrievals con 'success' (bit 2 = 0 en la convención de SMAP: 0 = sí) aunque no sean recomendados.
Resolución: la rejilla es de 9 km, pero el producto 'Enhanced' interpola temperaturas de brillo de una huella de
~40 km (Backus-Gilbert): dos píxeles vecinos NO son observaciones independientes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .common import DATA, NAC_HR
from .download import AM, PM

FILL = -9999.0
BIT_REC, BIT_ATT, BIT_SUC = 1, 2, 4
SF_BITS = {"agua_estatica": 1, "costa": 4, "urbano": 8, "precipitacion": 16, "montana": 512, "vegetacion_densa": 1024}
CACHE = DATA / "derivados" / "smap_l3e_rd.npz"


def pixel_latlon() -> tuple[np.ndarray, np.ndarray]:
    """Centros (lat, lon) de los píxeles del recorte (filas 532-570, columnas 1155-1197 de la rejilla M09)."""
    import h5py
    from ..hr.download import ease2_xy
    from .download import smap_rows_cols
    r0, r1, c0, c1 = smap_rows_cols()
    with h5py.File(NAC_HR / "smap" / "SPL4SMGP_008_xy.nc4", "r") as f:
        X, Y = f["x"][c0:c1 + 1], f["y"][r0:r1 + 1]
    lat_t = np.linspace(10, 30, 200001)
    _, yt = ease2_xy(np.zeros_like(lat_t), lat_t)
    lat = np.interp(Y, yt, lat_t)
    x1, _ = ease2_xy(np.array([1.0]), np.array([0.0]))
    lon = X / x1[0]
    LO, LA = np.meshgrid(lon, lat)
    return LA, LO


def load(rebuild: bool = False) -> dict:
    """Pila diaria (D, ny, nx) de AM y PM: humedad, banderas y VWC. Se guarda en data/testigos/derivados."""
    if CACHE.exists() and not rebuild:
        z = np.load(CACHE, allow_pickle=False)
        return {k: z[k] for k in z.files}
    import h5py
    files = sorted((DATA / "smap_l3e").rglob("SPL3SMP_E_006_*_RD.nc4"))
    days = np.array([pd.Timestamp(f.name.split("_")[3]).to_datetime64() for f in files], dtype="datetime64[D]")
    out = {}
    for tag, g, suf in (("am", AM, ""), ("pm", PM, "_pm")):
        sm, qf, vwc, sf = [], [], [], []
        for f in files:
            with h5py.File(f, "r") as h:
                sm.append(h[f"{g}/soil_moisture{suf}"][...])
                qf.append(h[f"{g}/retrieval_qual_flag{suf}"][...])
                vwc.append(h[f"{g}/vegetation_water_content{suf}"][...])
                sf.append(h[f"{g}/surface_flag{suf}"][...])
        sm = np.stack(sm).astype("float32")
        sm[sm <= FILL + 1] = np.nan
        vwc = np.stack(vwc).astype("float32")
        vwc[vwc <= FILL + 1] = np.nan
        out[f"sm_{tag}"] = sm
        out[f"qf_{tag}"] = np.stack(qf).astype("uint16")
        out[f"vwc_{tag}"] = vwc
        out[f"sf_{tag}"] = np.stack(sf).astype("uint16")
    LA, LO = pixel_latlon()
    out.update({"dias": days, "lat": LA, "lon": LO})
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE, **out)
    return out


def masked(S: dict, tag: str, mode: str = "recomendado") -> np.ndarray:
    sm = S[f"sm_{tag}"].astype(float)
    qf = S[f"qf_{tag}"]
    if mode == "recomendado":
        ok = (qf != 65534) & ((qf & BIT_REC) == 0)
    else:                               # todos los retrievals con éxito, recomendados o no
        ok = (qf != 65534) & ((qf & BIT_SUC) == 0)
    return np.where(ok & np.isfinite(sm), sm, np.nan)


def quality_table(S: dict, land: np.ndarray | None = None) -> pd.DataFrame:
    """Una fila por píxel 9 km: fracción de días con retrieval intentado, con éxito y recomendado; VWC; banderas."""
    rows = []
    ny, nx = S["lat"].shape
    nd = S["dias"].size
    for i in range(ny):
        for j in range(nx):
            rec = {"fila": i, "col": j, "lat": float(S["lat"][i, j]), "lon": float(S["lon"][i, j])}
            for tag in ("am", "pm"):
                qf = S[f"qf_{tag}"][:, i, j]
                valid = qf != 65534
                rec[f"frac_dias_con_dato_{tag}"] = float(valid.mean())
                rec[f"frac_exito_{tag}"] = float((valid & ((qf & BIT_SUC) == 0)).sum() / nd)
                rec[f"frac_recomendado_{tag}"] = float((valid & ((qf & BIT_REC) == 0)).sum() / nd)
                rec[f"frac_recomendado_de_intentados_{tag}"] = (float((valid & ((qf & BIT_REC) == 0)).sum() / valid.sum())
                                                                if valid.any() else np.nan)
                suc = valid & ((qf & BIT_SUC) == 0)
                v = S[f"vwc_{tag}"][:, i, j]
                vv = v[suc & np.isfinite(v)]
                rec[f"vwc_mediana_{tag}"] = float(np.median(vv)) if vv.size else np.nan
                rec[f"frac_vwc_mayor_5_{tag}"] = float((vv > 5).mean()) if vv.size else np.nan
                sf = S[f"sf_{tag}"][:, i, j]
                sv = suc & (sf != 65534)          # banderas solo en días con retrieval (sin paso: 2047 = todas)
                for k, b in SF_BITS.items():
                    rec[f"bandera_{k}_{tag}"] = float(((sf & b) > 0)[sv].mean()) if sv.any() else np.nan
            rows.append(rec)
    df = pd.DataFrame(rows)
    df["frac_recomendado_am_pm"] = (df["frac_recomendado_am"] + df["frac_recomendado_pm"]) / 2
    if land is not None:
        df["tierra_rd"] = land.ravel()
    return df


def daily_merged(S: dict, mode: str = "recomendado") -> tuple[np.ndarray, np.ndarray]:
    """Serie de retrievals ordenada en el tiempo: AM (10 UTC) y PM (22 UTC) intercalados.
    Devuelve tiempos (2D) en horas UTC desde el primer día y la pila (2D, ny, nx)."""
    am, pm = masked(S, "am", mode), masked(S, "pm", mode)
    d = S["dias"].astype("datetime64[h]")
    t = np.empty(2 * d.size, dtype="datetime64[h]")
    t[0::2] = d + np.timedelta64(10, "h")
    t[1::2] = d + np.timedelta64(22, "h")
    X = np.empty((2 * d.size,) + am.shape[1:], dtype=float)
    X[0::2], X[1::2] = am, pm
    return t, X


def monthly(S: dict, mode: str = "recomendado", min_obs: int = 4) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Media mensual de AM y PM juntos (exige ≥ min_obs retrievals en el mes). Devuelve meses, media y n."""
    t, X = daily_merged(S, mode)
    m = t.astype("datetime64[M]")
    um = np.unique(m)
    M = np.full((um.size,) + X.shape[1:], np.nan)
    N = np.zeros((um.size,) + X.shape[1:], dtype=int)
    for k, mm in enumerate(um):
        s = m == mm
        n = np.isfinite(X[s]).sum(0)
        with np.errstate(invalid="ignore"):
            v = np.nanmean(X[s], axis=0) if s.any() else np.nan
        M[k] = np.where(n >= min_obs, v, np.nan)
        N[k] = n
    return um, M, N


def gldas_cell_mean(S: dict, X: np.ndarray, lat: float, lon: float, res: float = 0.25, land=None) -> np.ndarray:
    """Media de los píxeles 9 km cuyo centro cae en la celda (lat ± res/2, lon ± res/2). X: (T, ny, nx)."""
    m = (np.abs(S["lat"] - lat) <= res / 2) & (np.abs(S["lon"] - lon) <= res / 2)
    if land is not None:
        m &= land
    with np.errstate(invalid="ignore"):
        return np.nanmean(X[:, m], axis=1), int(m.sum())


def nearest_pixel(S: dict, lat: float, lon: float) -> tuple[int, int]:
    d = (S["lat"] - lat) ** 2 + ((S["lon"] - lon) * np.cos(np.radians(lat))) ** 2
    i, j = np.unravel_index(np.argmin(d), d.shape)
    return int(i), int(j)


def land_mask(S: dict) -> np.ndarray:
    """Píxeles cuyo centro cae en tierra dominicana (geoBoundaries ADM0 del motor de alta resolución)."""
    import json
    from ..region import _polys, inside
    gj = json.loads((NAC_HR / "limites" / "geoBoundaries-DOM-ADM1.geojson").read_text(encoding="utf-8"))
    pts = np.column_stack([S["lon"].ravel(), S["lat"].ravel()])
    ok = np.zeros(pts.shape[0], bool)
    for f in gj["features"]:
        ok |= inside(_polys(f["geometry"]), pts)
    return ok.reshape(S["lat"].shape)


def path_exists() -> bool:
    return any((DATA / "smap_l3e").rglob("*.nc4")) if (DATA / "smap_l3e").exists() else False


__all__ = ["load", "masked", "quality_table", "daily_merged", "monthly", "gldas_cell_mean", "nearest_pixel",
           "land_mask", "Path"]
