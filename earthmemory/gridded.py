"""Lectura de los recortes IMERG y GLDAS ya descargados → tablas tiempo × celda (pandas).

Unidades de salida:
- IMERG mensual (mm/h, media del mes) → mm en el mes (× 24 × días del mes).
- IMERG diario (mm/día, día UTC 00:00-23:59) → mm en el día.
- IMERG media hora (mm/h) → mm en la media hora (× 0.5); índice = inicio de la media hora en UTC.
- GLDAS: RootMoist (kg m-2 = mm de agua en 0-100 cm), SoilMoi0_10cm (mm en 0-10 cm),
  Tair (K → °C), Evap (kg m-2 s-1 → mm/día, × 86400). Fuera de tierra GLDAS → NaN.
Cada archivo se valida: la rejilla debe coincidir con la del primer archivo y las unidades con las esperadas.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import earthdata
from .grid import Grid

GLDAS_OUT = {"SoilMoi0_10cm_inst": ("SM_0_10", "mm (kg m-2) en 0-10 cm", lambda x: x),
             "RootMoist_inst": ("SM_RAIZ", "mm (kg m-2) en la zona de raíces 0-100 cm", lambda x: x),
             "Tair_f_inst": ("TAIRE", "°C", lambda x: x - 273.15),
             "Evap_tavg": ("ET", "mm/día", lambda x: x * 86400.0)}


def _grid_from(lat: np.ndarray, lon: np.ndarray, name: str, res: float) -> Grid:
    return Grid(name, res, np.round(lat.astype(float), 4), np.round(lon.astype(float), 4))


def _stack(files: list[Path], var: str, units: str, name: str, res: float, when) -> tuple[Grid, np.ndarray, list]:
    grid, arrs, times = None, [], []
    for f in files:
        a, lat, lon, attrs = earthdata.read_subset(f, var)
        u = attrs.get("units")
        if units and u != units:
            raise ValueError(f"{f}: unidades {u!r}, se esperaba {units!r}")
        if grid is None:
            grid = _grid_from(lat, lon, name, res)
        elif not (np.allclose(lat, grid.lat, atol=1e-3) and np.allclose(lon, grid.lon, atol=1e-3)):
            raise ValueError(f"{f}: la rejilla no coincide con la del primer archivo")
        arrs.append(a.ravel())  # orden fila = latitud ascendente, columna = longitud (como Grid.ids())
        times.append(when(f.name))
    return grid, np.vstack(arrs), times


def _imerg_date(name: str) -> pd.Timestamp:
    return pd.Timestamp(re.search(r"3IMERG\.(\d{8})-", name).group(1))


def _imerg_hh_time(name: str) -> pd.Timestamp:
    m = re.search(r"3IMERG\.(\d{8})-S(\d{6})-", name)
    return pd.Timestamp(m.group(1) + "T" + m.group(2))


def _gldas_date(name: str) -> pd.Timestamp:
    m = re.search(r"\.A(\d{4})(\d{2})\.", name)
    return pd.Timestamp(int(m.group(1)), int(m.group(2)), 1)


def imerg_monthly(ddir: Path) -> tuple[Grid, pd.DataFrame]:
    files = sorted((Path(ddir) / "gesdisc" / "GPM_3IMERGM.07").glob("*.nc4"))
    g, X, t = _stack(files, "precipitation", "mm/hr", "IMERG 0.1°", 0.1, _imerg_date)
    df = pd.DataFrame(X, index=pd.DatetimeIndex(t, name="fecha"), columns=g.ids()).sort_index()
    df = df.mul(24.0 * df.index.days_in_month, axis=0)
    full = pd.date_range(df.index.min(), df.index.max(), freq="MS", name="fecha")
    return g, df.reindex(full)  # meses que no se pudieron descargar quedan como NaN (visibles)


def imerg_daily(ddir: Path, g_ref: Grid | None = None) -> tuple[Grid, pd.DataFrame]:
    files = sorted((Path(ddir) / "gesdisc" / "GPM_3IMERGDF.07").glob("*/*.nc4"))
    if not files:
        return g_ref, pd.DataFrame()
    g, X, t = _stack(files, "precipitation", "", "IMERG 0.1°", 0.1, _imerg_date)
    df = pd.DataFrame(X, index=pd.DatetimeIndex(t, name="fecha"), columns=g.ids()).sort_index()
    full = pd.date_range(df.index.min(), df.index.max(), freq="D", name="fecha")
    return g, df.reindex(full)


def imerg_halfhour(ddir: Path) -> tuple[Grid | None, pd.DataFrame]:
    files = sorted((Path(ddir) / "gesdisc" / "GPM_3IMERGHH.07").glob("*.nc4"))
    if not files:
        return None, pd.DataFrame()
    g, X, t = _stack(files, "precipitation", "mm/hr", "IMERG 0.1°", 0.1, _imerg_hh_time)
    df = pd.DataFrame(X * 0.5, index=pd.DatetimeIndex(t, name="inicio_utc"), columns=g.ids()).sort_index()
    full = pd.date_range(df.index.min(), df.index.max(), freq="30min", name="inicio_utc")
    return g, df.reindex(full)


def gldas_monthly(ddir: Path) -> tuple[Grid, dict]:
    files = sorted((Path(ddir) / "gesdisc" / "GLDAS_NOAH025_M.2.1").glob("*.nc4"))
    out, grid = {}, None
    units = {"SoilMoi0_10cm_inst": "kg m-2", "RootMoist_inst": "kg m-2", "Tair_f_inst": "K", "Evap_tavg": "kg m-2 s-1"}
    for v, (short, _, conv) in GLDAS_OUT.items():
        g, X, t = _stack(files, v, units[v], "GLDAS 0.25°", 0.25, _gldas_date)
        grid = grid or g
        df = pd.DataFrame(conv(X), index=pd.DatetimeIndex(t, name="fecha"), columns=g.ids()).sort_index()
        out[short] = df
    return grid, out


def gldas_elevation(ddir: Path, grid: Grid) -> pd.Series:
    """Elevación (m) de cada celda GLDAS 0.25° según el archivo de constantes del modelo; NaN si falta."""
    f = Path(ddir) / "gldas" / "GLDASp5_elevation_025d.nc4"
    if not f.exists():
        return pd.Series(np.nan, index=grid.ids())
    import h5py
    with h5py.File(f, "r") as h:
        var = next(k for k in h.keys() if "elev" in k.lower())
        a = np.asarray(h[var][...], float)
        lat = np.asarray(h["lat"][...], float)
        lon = np.asarray(h["lon"][...], float)
    a = a[0] if a.ndim == 3 else a
    a = np.where(a < -9000, np.nan, a)
    vals = {}
    for cid, (la, lo) in zip(grid.ids(), zip(*grid.mesh())):
        i = int(np.argmin(np.abs(lat - la)))
        j = int(np.argmin(np.abs(lon - lo)))
        vals[cid] = a[i, j] if abs(lat[i] - la) < 0.01 and abs(lon[j] - lo) < 0.01 else np.nan
    return pd.Series(vals)


def gldas_rain(ddir: Path) -> tuple[Grid | None, pd.DataFrame]:
    """Lluvia de forzamiento de GLDAS-2.1 (Rainf_f_tavg, kg m-2 s-1, media del mes) → mm en el mes.
    Es la lluvia que 'vio' el modelo de suelo (GPCP desagregado), no IMERG."""
    files = sorted((Path(ddir) / "gesdisc" / "GLDAS_NOAH025_M.2.1_Rainf").glob("*.nc4"))
    if not files:
        return None, pd.DataFrame()
    g, X, t = _stack(files, "Rainf_f_tavg", "kg m-2 s-1", "GLDAS 0.25°", 0.25, _gldas_date)
    df = pd.DataFrame(X, index=pd.DatetimeIndex(t, name="fecha"), columns=g.ids()).sort_index()
    return g, df.mul(86400.0 * df.index.days_in_month, axis=0)
