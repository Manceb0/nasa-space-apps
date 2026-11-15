"""Lectura de la lluvia diaria de los dos productos en la rejilla común de 0.1° (la de IMERG) y de los pesos.

- IMERG V07 Final diario (GPM_3IMERGDF.07, mm/día; el "día" es 00-24 UTC = 20:00-20:00 hora de RD), desde la
  caché del motor nacional (data/nacional/gesdisc, solo lectura). Rejilla nativa 0.1°: 26 × 39 celdas,
  bordes 17.4-20.0 N, 72.1-68.2 O.
- CHIRPS v2.0 diario 0.05° (data/tendencias/chirps_diario, ver descarga.py) AGREGADO a 0.1° por remapeo
  conservativo (media ponderada por área de las sub-celdas 0.05° con dato; CHIRPS no tiene dato sobre el mar, así
  que en celdas costeras es la media de la parte de tierra). Se agrega la LLUVIA DIARIA y después se calculan los
  índices, nunca al revés. La rejilla 0.05° de CHIRPS cae exactamente dentro de la de 0.1° (2 × 2 sub-celdas).
- Celdas analizadas: las 442 celdas IMERG con ≥ 25 % del área en RD y más RD que Haití
  (results/nacional/celdas_imerg.csv, columna `incluida`, motor nacional).
- Pesos de provincia: results/nacional/pesos_provincia_imerg.csv (fracción de la celda en la provincia × área).

Los arreglos apilados se guardan en data/tendencias/derivados/*.npz (caché derivada; se regenera si falta).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..hr.common import GRID as GRID005
from ..hr.common import ROOT, RGrid, conservative_regrid
from . import descarga

DATA = ROOT / "data" / "tendencias"
DER = DATA / "derivados"
RES_NAC = ROOT / "results" / "nacional"
YEARS = (2001, 2024)
GRID01 = RGrid(lon0=-72.10, lat0=17.40, res=0.1, nx=39, ny=26)
DAYS = np.arange(np.datetime64(f"{YEARS[0]}-01-01"), np.datetime64(f"{YEARS[1] + 1}-01-01"))


def cell_ids(g: RGrid = GRID01) -> np.ndarray:
    LO, LA = g.mesh()
    return np.array([f"{a:.3f}_{b:.3f}" for a, b in zip(LA.ravel(), LO.ravel())])


def imerg_daily(force: bool = False) -> np.ndarray:
    """(días, 26, 39) mm/día, lat ascendente."""
    cache = DER / "imerg_diario_01.npz"
    if cache.exists() and not force:
        return np.load(cache)["P"]
    import h5py
    d = ROOT / "data" / "nacional" / "gesdisc" / "GPM_3IMERGDF.07"
    files = {f.name.split("3IMERG.")[1][:8]: f for f in d.glob("*/3B-DAY.MS.MRG.3IMERG.*.nc4")}
    out = np.full((DAYS.size, GRID01.ny, GRID01.nx), np.nan, np.float32)
    lat_ref = lon_ref = None
    for k, day in enumerate(DAYS):
        key = str(day).replace("-", "")
        f = files.get(key)
        if f is None:
            continue
        with h5py.File(f, "r") as h:
            v = h["precipitation"]
            units = v.attrs.get("units", b"")
            units = units.decode() if isinstance(units, bytes) else str(units)
            if "mm" not in units:
                raise ValueError(f"{f.name}: unidades {units!r}")
            x = v[0].astype(np.float32).T  # [lon][lat] -> [lat][lon]
            lat = np.round(h["lat"][:].astype(float), 3)
            lon = np.round(h["lon"][:].astype(float), 3)
        if lat_ref is None:
            lat_ref, lon_ref = lat, lon
            if not (np.allclose(lat, GRID01.lat, atol=1e-3) and np.allclose(lon, GRID01.lon, atol=1e-3)):
                raise ValueError("La rejilla IMERG no coincide con GRID01")
        x[x < 0] = np.nan
        out[k] = x
    DER.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, P=out)
    return out


def chirps_daily_01(force: bool = False) -> np.ndarray | None:
    """CHIRPS diario agregado a 0.1° (días, 26, 39). None si la caché diaria no está completa."""
    cache = DER / "chirps_diario_01.npz"
    if cache.exists() and not force:
        return np.load(cache)["P"]
    if not all(descarga.path_year(y).exists() for y in range(YEARS[0], YEARS[1] + 1)):
        return None
    out = np.full((DAYS.size, GRID01.ny, GRID01.nx), np.nan, np.float32)
    k = 0
    for y in range(YEARS[0], YEARS[1] + 1):
        d = descarga.read_nc(descarga.path_year(y))
        P = d["P"].astype(float)
        agg = conservative_regrid(P, GRID005.lat_edges, GRID005.lon_edges, GRID01, min_cover=0.2)
        out[k:k + P.shape[0]] = agg
        k += P.shape[0]
    assert k == DAYS.size
    DER.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, P=out)
    return out


def cells_table() -> pd.DataFrame:
    c = pd.read_csv(RES_NAC / "celdas_imerg.csv")
    ids = cell_ids()
    c = c.set_index("celda").reindex(ids).reset_index()
    return c


def province_weights() -> pd.DataFrame:
    """(celda, provincia, codigo, peso) con peso = fracción de la celda en la provincia × área de la celda (km²)."""
    w = pd.read_csv(RES_NAC / "pesos_provincia_imerg.csv")
    a = pd.read_csv(RES_NAC / "celdas_imerg.csv").set_index("celda")["area_km2"]
    w["peso"] = w["fraccion"] * w["celda"].map(a)
    return w


def adm1_geojson() -> dict:
    return json.loads((ROOT / "data" / "nacional" / "limites" / "geoBoundaries-DOM-ADM1.geojson").read_text(encoding="utf-8"))


def to_cells(P: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """(días, ny, nx) → (días, n_celdas_incluidas) en el orden de cell_ids()[mask]."""
    return P.reshape(P.shape[0], -1)[:, mask]
