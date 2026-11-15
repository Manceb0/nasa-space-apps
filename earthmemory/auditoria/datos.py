"""Carga de productos ya descargados por otros motores (solo lectura) a una rejilla común 0.05°.

Rejilla común = la de CHIRPS (bordes en múltiplos de 0.05°; 54 × 78 celdas, 17.40-20.10 N, 72.10-68.20 O).
Las rejillas de IMERG (0.1°) y GLDAS (0.25°) tienen bordes en múltiplos de 0.05°: cada celda 0.05° cae entera
dentro de una sola celda IMERG o GLDAS. Pasar a 0.05° es solo repetir el valor de la celda gruesa (no se
inventa detalle) y permite medias de provincia exactas con los mismos pesos para todos los productos.
MERRA-2 (NASA POWER, 0.5° × 0.625°): cada celda 0.05° toma la celda POWER que contiene su centro.

Fuentes (solo lectura):
- IMERG V07 Final diario y media hora: data/nacional/gesdisc (motor nacional). Caché propia en data/auditoria/cache.
- CHIRPS v2.0 mensual 0.05° y diario nov-2023: data/nacional_hr/derivados/rejilla_005.npz (motor alta resolución).
- CHIRPS v2.0 diario 2001-2024: data/tendencias/chirps_diario/*.nc (motor tendencias; IRI Data Library).
- GLDAS-2.1 Rainf_f_tavg mensual: data/nacional/gesdisc/GLDAS_NOAH025_M.2.1_Rainf.
- NASA POWER PRECTOTCORR (MERRA-2) mensual regional y diario en 15 puntos: data/nacional/power.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .. import boundaries, grid, gridded, region

D_NAC = Path("data/nacional")
D_HR = Path("data/nacional_hr/derivados")
D_TEN = Path("data/tendencias/chirps_diario")
CACHE = Path("data/auditoria/cache")
MESES = pd.date_range("2001-01-01", "2024-12-01", freq="MS")
DIAS = pd.date_range("2001-01-01", "2024-12-31", freq="D")


class G05:
    """Rejilla común 0.05° + pesos de provincia + relieve."""

    def __init__(self):
        r = np.load(D_HR / "rejilla_005.npz")
        self.lat, self.lon = r["lat"].astype(float), r["lon"].astype(float)
        self.frac_rd = r["frac_rd"]
        self.elev = r["dem_elev_m"]
        self.slope = r["dem_pendiente_grados"]
        self.shape = (self.lat.size, self.lon.size)
        LO, LA = np.meshgrid(self.lon, self.lat)
        self.LA, self.LO = LA, LO
        units = boundaries.load_units(D_NAC / "limites" / "geoBoundaries-DOM-ADM1.geojson")
        self.units = units
        ctry = region.load_country(D_NAC / "natural_earth_10m_DOM_extracto.geojson", "DOM")
        self.others = ctry.others
        g = grid.Grid("CHIRPS 0.05°", 0.05, self.lat, self.lon)
        cache = CACHE / "pesos_provincia_005.parquet"
        if cache.exists():
            w = pd.read_parquet(cache)
            cells = pd.read_parquet(CACHE / "celdas_005.parquet")
        else:
            cells, w = grid.fractions(g, units, ctry.others, n=6)
            CACHE.mkdir(parents=True, exist_ok=True)
            w.to_parquet(cache)
            cells.to_parquet(CACHE / "celdas_005.parquet")
        self.cells = cells
        self.provs = sorted(w["provincia"].unique())
        self.codes = w.drop_duplicates("provincia").set_index("provincia")["codigo"].to_dict()
        idx = {c: k for k, c in enumerate(g.ids())}
        area = grid.cell_area_km2(self.LA.ravel(), 0.05)
        W = np.zeros((len(self.provs), self.lat.size * self.lon.size))
        for k, p in enumerate(self.provs):
            s = w[w["provincia"] == p]
            ii = np.array([idx[c] for c in s["celda"]])
            W[k, ii] = s["fraccion"].to_numpy() * area[ii]
        self.W = W
        # dominante: provincia con mayor fracción en cada celda (para mapas y "celda en provincia")
        self.prov_of = np.full(self.lat.size * self.lon.size, -1)
        fr = W / area[None, :]
        best = fr.max(0)
        self.prov_of[best > 0] = fr.argmax(0)[best > 0]
        self.prov_frac = best
        # tierra (RD + Haití) para la distancia a la costa
        pts = np.column_stack([self.LO.ravel(), self.LA.ravel()])
        land = region.inside(ctry.polygons, pts)
        for polys in ctry.others.values():
            land |= region.inside(polys, pts)
        self.land_any = land.reshape(self.shape)

    def province_mean(self, X: np.ndarray) -> np.ndarray:
        """X: (T, ny, nx) → (T, n_prov), media ponderada por área, ignorando NaN."""
        T = X.shape[0]
        Y = X.reshape(T, -1)
        m = np.isfinite(Y)
        num = np.where(m, Y, 0.0) @ self.W.T
        den = m.astype(float) @ self.W.T
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(den > 0, num / den, np.nan)

    def coast_km(self) -> np.ndarray:
        """Distancia (km) del centro de cada celda al centro de la celda de mar más cercana (aprox. 0.05°)."""
        sea = ~self.land_any
        la, lo = self.LA[sea], self.LO[sea]
        out = np.full(self.shape, np.nan)
        for i in range(self.shape[0]):
            for j in range(self.shape[1]):
                d = 111.2 * np.hypot(la - self.LA[i, j], (lo - self.LO[i, j]) * np.cos(np.radians(self.LA[i, j])))
                out[i, j] = d.min()
        return out


def nest_index(c_lat: np.ndarray, c_lon: np.ndarray, res_lat: float, res_lon: float, g: G05):
    """Índices (I, J) de la celda gruesa que contiene cada centro 0.05° (-1 si cae fuera)."""
    I = np.floor((g.lat - (c_lat[0] - res_lat / 2)) / res_lat + 1e-9).astype(int)
    J = np.floor((g.lon - (c_lon[0] - res_lon / 2)) / res_lon + 1e-9).astype(int)
    I[(I < 0) | (I >= c_lat.size)] = -1
    J[(J < 0) | (J >= c_lon.size)] = -1
    return I, J


def to05(A: np.ndarray, I: np.ndarray, J: np.ndarray) -> np.ndarray:
    out = A[:, np.clip(I, 0, None)][:, :, np.clip(J, 0, None)].astype(float)
    out[:, I < 0, :] = np.nan
    out[:, :, J < 0] = np.nan
    return out


def _df_to_cube(df: pd.DataFrame, g: grid.Grid) -> np.ndarray:
    return df[g.ids()].to_numpy(float).reshape(len(df), g.lat.size, g.lon.size)


_IMD = {}


def imerg_daily() -> dict:
    if "d" in _IMD:
        return _IMD["d"]
    _IMD["d"] = _imerg_daily()
    return _IMD["d"]


def _imerg_daily() -> dict:
    """IMERG V07 Final diario (mm/día UTC) en su rejilla 0.1°. Caché .npz (lectura de 8 766 archivos)."""
    p = CACHE / "imerg_diario.npz"
    if p.exists():
        z = np.load(p, allow_pickle=True)
        return {"P": z["P"], "lat": z["lat"], "lon": z["lon"], "dias": pd.DatetimeIndex(z["dias"].astype(str))}
    g, df = gridded.imerg_daily(D_NAC)
    df = df.loc["2001-01-01":"2024-12-31"]
    P = _df_to_cube(df, g).astype(np.float32)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(p, P=P, lat=g.lat, lon=g.lon, dias=df.index.strftime("%Y-%m-%d").to_numpy().astype("U10"))
    return {"P": P, "lat": g.lat, "lon": g.lon, "dias": df.index}


def imerg_halfhour() -> dict:
    g, df = gridded.imerg_halfhour(D_NAC)
    return {"P": _df_to_cube(df, g), "lat": g.lat, "lon": g.lon, "t": df.index}


def gldas_forcing() -> dict:
    g, df = gridded.gldas_rain(D_NAC)
    df = df.loc["2001-01-01":"2024-12-01"]
    return {"P": _df_to_cube(df, g), "lat": g.lat, "lon": g.lon, "meses": df.index}


def chirps_monthly() -> dict:
    r = np.load(D_HR / "rejilla_005.npz")
    return {"P": r["P_chirps"].astype(float), "meses": pd.DatetimeIndex(pd.to_datetime(r["meses"].astype(str)))}


def chirps_daily_nov2023() -> np.ndarray:
    return np.load(D_HR / "rejilla_005.npz")["Pd_nov2023"].astype(float)


def chirps_daily_status() -> dict:
    # solo los años que el motor tendencias ya registró en su manifiesto (archivo completo, con SHA-256)
    man = D_TEN.parent / "MANIFEST.json"
    rec = json.loads(man.read_text(encoding="utf-8")).get("archivos", {}) if man.exists() else {}
    years = []
    for k, v in rec.items():
        f = D_TEN.parent / k
        if k.startswith("chirps_diario/") and f.exists() and f.stat().st_size == v.get("bytes"):
            years.append(int(Path(k).stem.rsplit("_", 1)[1]))
    years = sorted(years)
    return {"anios": years, "completo": all(y in years for y in range(2001, 2025))}


def chirps_daily(g: G05) -> dict | None:
    """CHIRPS v2.0 diario 0.05° 2001-2024 (motor tendencias). None si aún no están los 24 años."""
    st = chirps_daily_status()
    years = [y for y in st["anios"] if 2001 <= y <= 2024]
    if not years:
        return None
    p = CACHE / f"chirps_diario_{years[0]}_{years[-1]}_{len(years)}.npy"
    dias = pd.DatetimeIndex([d for d in DIAS if d.year in set(years)])
    if p.exists():
        return {"P": np.load(p), "dias": dias, "anios": years, "completo": st["completo"]}
    from scipy.io import netcdf_file
    cubes = []
    for y in years:
        with netcdf_file(D_TEN / f"chirps_v2p0_diario_RD_{y}.nc", "r", mmap=False) as n:
            X = np.asarray(n.variables["X"][:], float)
            Y = np.asarray(n.variables["Y"][:], float)
            a = np.asarray(n.variables["prcp"][:], float)
            fill = getattr(n.variables["prcp"], "missing_value", None)
        if fill is not None:
            a[a == float(fill)] = np.nan
        a[a < 0] = np.nan
        if Y[0] > Y[-1]:
            Y, a = Y[::-1], a[:, ::-1]
        if not (np.allclose(Y, g.lat, atol=1e-3) and np.allclose(X, g.lon, atol=1e-3)):
            raise ValueError(f"CHIRPS diario {y}: rejilla distinta de la 0.05° común")
        nd = 366 if pd.Timestamp(f"{y}-12-31").dayofyear == 366 else 365
        if a.shape[0] != nd:
            raise ValueError(f"CHIRPS diario {y}: {a.shape[0]} días, se esperaban {nd}")
        cubes.append(a.astype(np.float32))
    P = np.concatenate(cubes)
    np.save(p, P)
    return {"P": P, "dias": dias, "anios": years, "completo": st["completo"]}


def merra2_monthly() -> dict:
    """POWER PRECTOTCORR mensual regional (mm/día, media del mes) → mm/mes, en sus centros 0.5° × 0.625°."""
    doc = json.loads((D_NAC / "power" / "mensual_DOM_PRECTOTCORR_2001_2024.json").read_text(encoding="utf-8"))
    pts = {}
    for f in doc["features"]:
        lo, la = f["geometry"]["coordinates"][:2]
        s = f["properties"]["parameter"]["PRECTOTCORR"]
        v = [s.get(f"{d.year}{d.month:02d}", np.nan) for d in MESES]
        pts[(round(la, 3), round(lo, 3))] = np.array(v, float)
    lats = np.array(sorted({k[0] for k in pts}))
    lons = np.array(sorted({k[1] for k in pts}))
    A = np.full((len(MESES), lats.size, lons.size), np.nan)
    for (la, lo), v in pts.items():
        v = np.where(v < 0, np.nan, v)
        A[:, np.searchsorted(lats, la), np.searchsorted(lons, lo)] = v * MESES.days_in_month.to_numpy()
    return {"P": A, "lat": lats, "lon": lons, "meses": MESES}


def merra2_daily_points() -> dict:
    out = {}
    for f in sorted((D_NAC / "power" / "diario").glob("PRECTOTCORR_*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        lo, la = doc["geometry"]["coordinates"][:2]
        s = doc["properties"]["parameter"]["PRECTOTCORR"]
        ser = pd.Series({pd.Timestamp(k): (np.nan if v < 0 else v) for k, v in s.items()}).sort_index()
        out[(float(la), float(lo))] = ser
    return out


def monthly_from_daily(P: np.ndarray, dias: pd.DatetimeIndex) -> np.ndarray:
    key = dias.year * 12 + dias.month - 1
    k0 = key.min()
    n = key.max() - k0 + 1
    out = np.zeros((n,) + P.shape[1:])
    cnt = np.zeros((n,) + P.shape[1:])
    for t in range(P.shape[0]):
        x = P[t]
        m = np.isfinite(x)
        out[key[t] - k0] += np.where(m, x, 0)
        cnt[key[t] - k0] += m
    return np.where(cnt > 0, out, np.nan)
