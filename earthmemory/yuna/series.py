"""Series diarias por zona de la cuenca (media ponderada por área de la parte de cada celda dentro de la zona).

Variables y su CLASE (se etiqueta en cada figura y tabla):
- IMERG Final V07 diario 0.1°          → RECUPERACIÓN SATELITAL (calibrada con pluviómetros GPCC a escala mensual)
- CHIRPS v2.0 diario 0.05° (si existe)  → RECUPERACIÓN SATELITAL + estaciones
- SMAP L4 v8 (SPL4SMGP) 9 km, 13:30 UTC → MODELO CON ASIMILACIÓN (Catchment + Tb SMAP; su forzante de lluvia se
                                          ajusta a IMERG: NO es independiente de IMERG)
- GLDAS-2.1 Noah mensual 0.25°          → MODELO FORZADO (GDAS + GPCP; sin asimilación de suelo)
- GEOGLOWS v2 retrospectivo diario      → SIMULACIÓN HIDROLÓGICA (forzada con ERA5; sin presas ni aforos)
- JRC GSW mensual 30 m                  → OBSERVACIÓN (clasificación de Landsat; limitada por nubes)
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from shapely.geometry import Point, box
from shapely.prepared import prep

from .common import DATA, HR, NAC, TEND

PX_KM2 = (0.00025 * 110.574) * (0.00025 * 111.32 * np.cos(np.radians(19.15)))  # píxel GSW (0.00025°) en km²

# ------------------------------------------------------------------ pesos

def cell_weights(lat: np.ndarray, lon: np.ndarray, res: float, geom) -> np.ndarray:
    """Área (km²) de cada celda dentro de geom. lat/lon: centros 1D (rejilla regular)."""
    LO, LA = np.meshgrid(lon, lat)
    w = np.zeros(LA.shape)
    x0, y0, x1, y1 = geom.bounds
    pg = prep(geom)
    for i in range(LA.shape[0]):
        if LA[i, 0] + res / 2 < y0 or LA[i, 0] - res / 2 > y1:
            continue
        for j in range(LA.shape[1]):
            if LO[i, j] + res / 2 < x0 or LO[i, j] - res / 2 > x1:
                continue
            b = box(LO[i, j] - res / 2, LA[i, j] - res / 2, LO[i, j] + res / 2, LA[i, j] + res / 2)
            if not pg.intersects(b):
                continue
            frac = b.intersection(geom).area / b.area
            w[i, j] = frac * (111.32 * res * np.cos(np.radians(LA[i, j]))) * (110.574 * res)
    return w


def wmean(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    """X: (t, n) ; w: (n,). Media ponderada ignorando NaN."""
    W = np.where(np.isnan(X), 0.0, w[None, :])
    s = np.nansum(np.nan_to_num(X) * W, axis=1)
    d = W.sum(axis=1)
    return np.where(d > 0.5 * w.sum(), s / np.where(d > 0, d, 1), np.nan)


def wmax(X: np.ndarray, w: np.ndarray, min_frac_km2: float = 2.0) -> np.ndarray:
    sel = w > min_frac_km2
    return np.nanmax(X[:, sel], axis=1) if sel.any() else np.full(X.shape[0], np.nan)


# ------------------------------------------------------------------ IMERG diario

def imerg(zonas: dict) -> pd.DataFrame:
    from .. import gridded
    g, df = gridded.imerg_daily(NAC)
    X = df.to_numpy(float)
    out = {}
    for k, geom in zonas.items():
        w = cell_weights(g.lat, g.lon, 0.1, geom).ravel()
        out[f"imerg_media_{k}"] = wmean(X, w)
        out[f"imerg_max_{k}"] = wmax(X, w)
        X48 = pd.DataFrame(X).rolling(2, min_periods=2).sum().to_numpy()
        out[f"imerg_max48_{k}"] = wmax(X48, w)   # máximo de celda de la suma de 48 h (estilo sEAP, puntual)
    return pd.DataFrame(out, index=df.index)


# ------------------------------------------------------------------ CHIRPS diario (motor tendencias)

def chirps(zonas: dict) -> pd.DataFrame | None:
    from scipy.io import netcdf_file
    files = sorted((TEND / "chirps_diario").glob("chirps_v2p0_diario_RD_*.nc"))
    if not files:
        return None
    parts, w = [], None
    for f in files:
        try:
            with netcdf_file(f, "r", mmap=False) as nc:
                v = nc.variables
                X = np.asarray(v["X"][:], float)
                Y = np.asarray(v["Y"][:], float)
                T = np.asarray(v["T"][:], float)
                units = v["T"].units.decode() if isinstance(v["T"].units, bytes) else v["T"].units
                P = np.asarray(v["prcp"][:], float)
                fv = getattr(v["prcp"], "missing_value", None)
        except Exception as e:  # noqa: BLE001  (archivo a medio bajar por el otro motor)
            print(f"  CHIRPS {f.name}: no legible ({e})", flush=True)
            continue
        if fv is not None:
            P[P == float(fv)] = np.nan
        P[P < 0] = np.nan
        if Y[0] > Y[-1]:
            Y, P = Y[::-1], P[:, ::-1, :]
        if "julian" in units:   # IRI: día juliano centrado a las 12 UTC (2451911 = 2001-01-01)
            dates = pd.to_datetime(T, unit="D", origin="julian").normalize()
        else:
            m = re.search(r"since (\d{4})-(\d{1,2})-(\d{1,2})", units)
            base = pd.Timestamp(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            dates = base + pd.to_timedelta(np.floor(T), unit="D")
        if w is None:
            w = {k: cell_weights(Y, X, 0.05, g).ravel() for k, g in zonas.items()}
        Xf = P.reshape(P.shape[0], -1)
        d = {}
        for k in zonas:
            d[f"chirps_media_{k}"] = wmean(Xf, w[k])
            d[f"chirps_max_{k}"] = wmax(Xf, w[k], 0.5)
        parts.append(pd.DataFrame(d, index=pd.DatetimeIndex(dates, name="fecha")))
    if not parts:
        return None
    return pd.concat(parts).sort_index()


# ------------------------------------------------------------------ SMAP L4

def smap(zonas: dict) -> pd.DataFrame | None:
    import h5py
    files = sorted((HR / "smap" / "diario").glob("*/SPL4SMGP_*_RD.nc4"))
    if not files:
        return None
    sel, rows, idx = None, [], []
    for p in files:
        day = p.name.split("_")[1]
        with h5py.File(p, "r") as f:
            gph = f["Geophysical_Data"]
            rz = gph["sm_rootzone"][:].astype(float)
            sf = gph["sm_surface"][:].astype(float)
            if sel is None:
                lat, lon = f["cell_lat"][:].astype(float), f["cell_lon"][:].astype(float)
                sel = {k: np.array([prep(g).contains(Point(x, y)) for x, y in zip(lon.ravel(), lat.ravel())])
                       for k, g in zonas.items()}
        rz[rz <= -9990] = np.nan
        sf[sf <= -9990] = np.nan
        r = {}
        for k, s in sel.items():
            r[f"smap_raiz_{k}"] = np.nanmean(rz.ravel()[s]) if s.any() else np.nan
            r[f"smap_sup_{k}"] = np.nanmean(sf.ravel()[s]) if s.any() else np.nan
            r[f"smap_ncel_{k}"] = int(s.sum())
        rows.append(r)
        idx.append(pd.Timestamp(day))
    return pd.DataFrame(rows, index=pd.DatetimeIndex(idx, name="fecha"))


# ------------------------------------------------------------------ GLDAS mensual

def gldas(zonas: dict) -> pd.DataFrame:
    from .. import gridded
    g, d = gridded.gldas_monthly(NAC)
    out = {}
    for k, geom in zonas.items():
        w = cell_weights(g.lat, g.lon, 0.25, geom).ravel()
        for v in ("SM_RAIZ", "SM_0_10"):
            out[f"gldas_{v.lower()}_{k}"] = wmean(d[v].to_numpy(float), w)
    return pd.DataFrame(out, index=d["SM_RAIZ"].index)


# ------------------------------------------------------------------ GEOGLOWS

def geoglows(ids: dict) -> pd.DataFrame | None:
    cols = {}
    for nombre, info in ids.items():
        f = DATA / "geoglows" / str(info.get("archivo", ""))
        if not info.get("archivo") or not f.exists():
            continue
        s = pd.read_csv(f)
        tcol = s.columns[0]
        s[tcol] = pd.to_datetime(s[tcol]).dt.tz_localize(None).dt.normalize()
        s = s.set_index(tcol).iloc[:, 0]
        cols[f"q_{nombre}"] = s.groupby(level=0).mean()
    return pd.DataFrame(cols) if cols else None


# ------------------------------------------------------------------ JRC GSW

def gsw(mascaras: dict) -> pd.DataFrame:
    """Por mes: píxeles de agua, válidos y área de agua (km²) dentro de cada máscara (arrays booleanos 2D)."""
    rows = []
    for p in sorted((DATA / "gsw_mensual").glob("gsw_*.npz")):
        y, m = map(int, p.stem.split("_")[1:3])
        a = np.load(p)["agua"]
        r = {"fecha": pd.Timestamp(y, m, 1)}
        for k, msk in mascaras.items():
            mm = msk[: a.shape[0], : a.shape[1]]
            sub = a[mm]
            n = mm.sum()
            agua = int((sub == 2).sum())
            valid = int((sub > 0).sum())
            r[f"gsw_validos_{k}"] = valid / n if n else np.nan
            r[f"gsw_agua_km2_{k}"] = agua * PX_KM2
            r[f"gsw_frac_agua_validos_{k}"] = agua / valid if valid else np.nan
        rows.append(r)
    return pd.DataFrame(rows).set_index("fecha")
