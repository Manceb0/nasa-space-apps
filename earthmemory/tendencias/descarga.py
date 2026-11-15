"""CHIRPS v2.0 DIARIO 0.05° 2001-2024 para la caja de la República Dominicana (recorte en el servidor).

Ruta usada: IRI/LDEO Climate Data Library, conjunto `SOURCES/.UCSB/.CHIRPS/.v2p0/.daily-improved/.global/.0p05/.prcp`,
recortado en el servidor con X/Y RANGEEDGES (bordes 72.10-68.20 O, 17.40-20.10 N = la rejilla común de
`earthmemory.hr.common.GRID`, 78 × 54 celdas) y pedido como netCDF clásico, un archivo por año.

Comprobación de identidad (2026-11-14): noviembre de 2023 bajado por esta ruta es IDÉNTICO (diferencia máxima 0.0 mm
en las 2015 celdas con dato, días 1, 17, 18 y 19) a los GeoTIFF oficiales del CHC/UCSB
`chirps-v2.0.2023.11.DD.tif.gz` ya guardados en data/nacional_hr/chirps/diario. Se repite al descargar (ver
`verificar_contra_tif_oficial`) y el resultado queda en MANIFEST.json.

Disposición de la caché (la lee también el motor `testigos`):
    data/tendencias/chirps_diario/chirps_v2p0_diario_RD_{AAAA}.nc   netCDF-3 clásico, sin modificar
        variables: prcp(T, Y, X) float32 mm/día, missing_value −9999 (mar); X (lon, centros, ascendente),
        Y (lat, centros, ascendente), T (julian_day del CENTRO del día, p. ej. 2451911.0 = 2001-01-01 12 UTC;
        fecha = 2001-01-01 + floor(T − 2451910.5) días)
    data/tendencias/MANIFEST.json   URL exacta, SHA-256, bytes, fecha UTC, licencia y cita por archivo
Leer con `earthmemory.tendencias.descarga.read_nc(path_year(anio))` → {"P" (días, lat, lon) mm/día con NaN en el mar,
"lat", "lon", "fechas"} (scipy.io.netcdf_file; no hace falta xarray).
"""

from __future__ import annotations

import calendar
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ..hr.common import GRID, ROOT, FetchError, Manifest, http_get

DATA = ROOT / "data" / "tendencias"
CHIRPS_DIR = DATA / "chirps_diario"
MANIFEST = DATA / "MANIFEST.json"

IRI = ("https://iridl.ldeo.columbia.edu/SOURCES/.UCSB/.CHIRPS/.v2p0/.daily-improved/.global/.0p05/.prcp/"
       "X/-72.1/-68.2/RANGEEDGES/Y/17.4/20.1/RANGEEDGES/T/(1%20Jan%20{y})/(31%20Dec%20{y})/RANGEEDGES/data.nc")
LICENCIA = "CHIRPS: dominio público / CC0 (Climate Hazards Center, UC Santa Barbara)"
CITA = ("Funk, C. et al. (2015). The climate hazards infrared precipitation with stations—a new environmental "
        "record for monitoring extremes. Scientific Data 2, 150066. doi:10.1038/sdata.2015.66")


def path_year(y: int) -> Path:
    return CHIRPS_DIR / f"chirps_v2p0_diario_RD_{y}.nc"


def read_nc(p: Path) -> dict:
    from scipy.io import netcdf_file
    with netcdf_file(p, "r", mmap=False) as f:
        P = f.variables["prcp"][:].astype(np.float32)
        X = f.variables["X"][:].astype(float)
        Y = f.variables["Y"][:].astype(float)
        T = f.variables["T"][:].astype(float)
    P = np.where(P < 0, np.nan, P)
    if Y[0] > Y[-1]:
        Y, P = Y[::-1], P[:, ::-1]
    dates = np.datetime64("2001-01-01") + np.floor(T - 2451910.5).astype(int).astype("timedelta64[D]")
    return {"P": P, "lat": Y, "lon": X, "fechas": dates}


def validate(p: Path, y: int) -> None:
    d = read_nc(p)
    nd = 366 if calendar.isleap(y) else 365
    if d["P"].shape != (nd, GRID.ny, GRID.nx):
        raise ValueError(f"{p.name}: forma {d['P'].shape}, se esperaba {(nd, GRID.ny, GRID.nx)}")
    if not (np.allclose(d["lon"], GRID.lon, atol=1e-3) and np.allclose(d["lat"], GRID.lat, atol=1e-3)):
        raise ValueError(f"{p.name}: la rejilla no coincide con earthmemory.hr.common.GRID")
    if str(d["fechas"][0]) != f"{y}-01-01" or str(d["fechas"][-1]) != f"{y}-12-31":
        raise ValueError(f"{p.name}: fechas {d['fechas'][0]}..{d['fechas'][-1]}")
    if np.nanmax(d["P"]) > 1500 or np.isfinite(d["P"]).sum() == 0:
        raise ValueError(f"{p.name}: valores fuera de rango")


def _one(y: int) -> tuple[int, str]:
    p = path_year(y)
    url = IRI.format(y=y)
    tmp = p.with_suffix(".part")
    if tmp.exists():  # descarga previa completa pero no validada (p. ej. corrida interrumpida)
        try:
            validate(tmp, y)
            tmp.replace(p)
            return y, url
        except Exception:  # noqa: BLE001
            tmp.unlink()
    body = http_get(url, timeout=900, retries=5)
    tmp.write_bytes(body)
    validate(tmp, y)
    tmp.replace(p)
    return y, url


def verificar_contra_tif_oficial() -> dict:
    """Compara noviembre de 2023 de la caché con los GeoTIFF oficiales del CHC (si están en data/nacional_hr)."""
    from rasterio.io import MemoryFile
    d = read_nc(path_year(2023))
    tif_dir = ROOT / "data" / "nacional_hr" / "chirps" / "diario"
    out = {"dias_comparados": 0, "celdas_comparadas": 0, "dif_max_mm": None}
    difs = []
    for day in range(1, 31):
        f = tif_dir / f"chirps-v2.0.2023.11.{day:02d}.tif.gz"
        if not f.exists():
            continue
        with MemoryFile(gzip.decompress(f.read_bytes())) as m, m.open() as ds:
            a = ds.read(1).astype(float)
            tr = ds.transform
        cols = np.floor((d["lon"] - tr.c) / tr.a).astype(int)
        rows = np.floor((d["lat"] - tr.f) / tr.e).astype(int)
        sub = a[np.ix_(rows, cols)]
        sub[sub < 0] = np.nan
        k = int(np.flatnonzero(d["fechas"] == np.datetime64(f"2023-11-{day:02d}"))[0])
        q = d["P"][k].astype(float)
        ok = np.isfinite(q) & np.isfinite(sub)
        difs.append(np.abs(q[ok] - sub[ok]).max())
        out["dias_comparados"] += 1
        out["celdas_comparadas"] += int(ok.sum())
    if difs:
        out["dif_max_mm"] = float(np.max(difs))
    out["referencia"] = "data/nacional_hr/chirps/diario/chirps-v2.0.2023.11.DD.tif.gz (CHC, data.chc.ucsb.edu)"
    return out


def ensure_chirps_daily(years=range(2001, 2025), workers: int = 5) -> dict:
    CHIRPS_DIR.mkdir(parents=True, exist_ok=True)
    man = Manifest(MANIFEST)
    man.data["descripcion"] = __doc__.strip().splitlines()[0]
    man.data["disposicion"] = {
        "archivos": "chirps_diario/chirps_v2p0_diario_RD_{AAAA}.nc, un año por archivo, 2001-2024, tal como los sirve el servidor",
        "formato": "netCDF-3 clásico (leer con scipy.io.netcdf_file; h5py NO lo lee)",
        "variables": "prcp(T, Y, X) float32 mm/día, missing_value -9999 = mar; X lon centros -72.075..-68.225 (78); "
                     "Y lat centros 17.425..20.075 (54), ascendentes; T julian_day del centro del día",
        "fecha": "2001-01-01 + floor(T - 2451910.5) días",
        "rejilla": "idéntica a earthmemory.hr.common.GRID (bordes 72.10-68.20 O, 17.40-20.10 N, 0.05°)",
        "lector": "earthmemory.tendencias.descarga.read_nc(path_year(anio)) -> {P, lat, lon, fechas}",
        "derivados": "derivados/chirps_diario_01.npz (P: días × 26 × 39, agregado a 0.1° por media de área) y "
                     "derivados/imerg_diario_01.npz (IMERG V07 diario apilado); cachés regenerables, no fuente primaria",
    }
    missing = [y for y in years if not man.has(path_year(y))]
    errors = {}
    if missing:
        print(f"[descarga] CHIRPS diario: faltan {len(missing)} años -> IRI Data Library", flush=True)
        with ThreadPoolExecutor(workers) as ex:
            futs = {ex.submit(_one, y): y for y in missing}
            for fu in as_completed(futs):
                y = futs[fu]
                try:
                    _, url = fu.result()
                    man.add(path_year(y), url, dataset="CHIRPS v2.0 diario 0.05° (recorte RD)", anio=y,
                            accedido_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                            licencia=LICENCIA, cita=CITA, servidor="IRI/LDEO Climate Data Library")
                    print(f"[descarga] {y} ok", flush=True)
                except (FetchError, ValueError, OSError) as e:
                    errors[y] = str(e)
                    print(f"[descarga] {y} ERROR {e}", flush=True)
    have = [y for y in years if man.has(path_year(y))]
    estado = {"estado": "completo" if len(have) == len(list(years)) else "incompleto", "anios": len(have),
              "errores": errors, "ruta": "IRI/LDEO daily-improved global 0p05, X/Y RANGEEDGES, netCDF por año"}
    if 2023 in have:
        estado["identidad_con_tif_oficial_nov2023"] = verificar_contra_tif_oficial()
    man.note("chirps_diario", estado)
    man.save()
    return estado


if __name__ == "__main__":
    print(ensure_chirps_daily())
