"""Descargas autenticadas de NASA Earthdata (GES DISC) por OPeNDAP, con caché y manifiesto.

Credencial: un token de Earthdata (Bearer). Se lee SOLO de un archivo o de una variable de entorno,
en este orden: $EARTHDATA_TOKEN_FILE, /run/secrets/earthdata_token (montaje de solo lectura de Docker),
.secrets/earthdata_token; o $EARTHDATA_TOKEN. Nunca se imprime, nunca se escribe en el manifiesto,
en los registros ni en la imagen de Docker.

Rutas probadas el 2026-11-14 (resultado exacto en el manifiesto, sección "rutas"):
- IMERG Final V07 mensual, diario y media hora: OPeNDAP de gpm1.gesdisc.eosdis.nasa.gov (Hyrax, DAP2,
  respuesta .nc4 = HDF5). Funciona con Bearer.
- GLDAS Noah 2.1 mensual: el OPeNDAP de hydro1.gesdisc.eosdis.nasa.gov devuelve
  "410 Gone · The OPeNDAP service is no longer available" (retirado). Se usa el OPeNDAP en la nube
  (opendap.earthdata.nasa.gov, DAP4) con el ID de colección de CMR.
Cada archivo es un recorte de la caja del país; se guarda tal cual llegó (HDF5) con su SHA-256.
"""

from __future__ import annotations

import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .power import USER_AGENT, Manifest

TOKEN_PATHS = ("/run/secrets/earthdata_token", ".secrets/earthdata_token")
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"

GPM_OPENDAP = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3"
GPM_DATA = "https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3"
CLOUD_OPENDAP = "https://opendap.earthdata.nasa.gov/collections"
GLDAS_DATA = "https://hydro1.gesdisc.eosdis.nasa.gov/data/GLDAS"

# Colecciones (nombre corto, versión, DOI, ID de CMR en la nube)
DATASETS = {
    "IMERG_M": {"short": "GPM_3IMERGM", "ver": "07", "doi": "10.5067/GPM/IMERG/3B-MONTH/07",
                "cmr": "C2723754851-GES_DISC", "res": 0.1,
                "nombre": "GPM IMERG Final Precipitation L3 1 month 0.1° V07"},
    "IMERG_D": {"short": "GPM_3IMERGDF", "ver": "07", "doi": "10.5067/GPM/IMERGDF/DAY/07",
                "cmr": "C2723754864-GES_DISC", "res": 0.1,
                "nombre": "GPM IMERG Final Precipitation L3 1 day 0.1° V07"},
    "IMERG_HH": {"short": "GPM_3IMERGHH", "ver": "07", "doi": "10.5067/GPM/IMERG/3B-HH/07",
                 "cmr": "C2723754847-GES_DISC", "res": 0.1,
                 "nombre": "GPM IMERG Final Precipitation L3 Half Hourly 0.1° V07"},
    "GLDAS_M": {"short": "GLDAS_NOAH025_M", "ver": "2.1", "doi": "10.5067/SXAVCZFAQLNO",
                "cmr": "C1342986036-GES_DISC", "res": 0.25,
                "nombre": "GLDAS Noah Land Surface Model L4 monthly 0.25° V2.1"},
}
DATASETS["GLDAS_RAIN"] = {**DATASETS["GLDAS_M"], "nombre": DATASETS["GLDAS_M"]["nombre"] + " · Rainf_f_tavg (lluvia de forzamiento)"}
GLDAS_ELEV_URL = "https://ldas.gsfc.nasa.gov/sites/default/files/ldas/gldas/ELEV/GLDASp5_elevation_025d.nc4"
# Lluvia con la que se FORZÓ el modelo (GLDAS-2.1: GDAS + GPCP desagregado; sin asimilación de datos).
GLDAS_RAIN_VARS = ["Rainf_f_tavg"]
GLDAS_VARS = ["SoilMoi0_10cm_inst", "RootMoist_inst", "Tair_f_inst", "Evap_tavg"]


# ------------------------------------------------------------------ credencial

def token_source() -> str | None:
    """Dice DE DÓNDE vendría el token (ruta o 'variable de entorno'), sin leerlo ni mostrarlo."""
    cand = [os.environ.get("EARTHDATA_TOKEN_FILE")] + list(TOKEN_PATHS)
    for p in cand:
        if p and Path(p).is_file() and Path(p).stat().st_size > 20:
            return str(p)
    return "variable de entorno EARTHDATA_TOKEN" if os.environ.get("EARTHDATA_TOKEN") else None


def _token() -> str:
    src = token_source()
    if src is None:
        raise RuntimeError("No hay token de Earthdata (ver earthmemory/earthdata.py para dónde ponerlo)")
    if src.startswith("variable"):
        return os.environ["EARTHDATA_TOKEN"].strip()
    return Path(src).read_text(encoding="utf-8").strip()


# ------------------------------------------------------------------ HTTP

class EarthdataError(RuntimeError):
    pass


def get(url: str, retries: int = 6, timeout: int = 180, auth: bool = True) -> bytes:
    """GET con Bearer. Los mensajes de error contienen la URL y el código, nunca la cabecera."""
    last = None
    for k in range(retries):
        try:
            headers = {"User-Agent": USER_AGENT}
            if auth:
                headers["Authorization"] = "Bearer " + _token()
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code} {e.reason}"
            if e.code in (400, 401, 403, 404, 410):
                break  # no tiene sentido reintentar
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(min(60.0, 3.0 * (2 ** k)))
    raise EarthdataError(f"{url} -> {last}")


def list_dir(url: str, pattern: str) -> list[str]:
    body = get(url).decode("utf-8", errors="ignore")
    return sorted(set(re.findall(r'href="(' + pattern + r')"', body)))


# ------------------------------------------------------------------ rejillas e índices

@dataclass(frozen=True)
class GridSpec:
    """Rejilla global regular: centro de la celda i = lon0 + (i + 0.5)·res, igual en latitud."""
    res: float
    lon_edge0: float
    lat_edge0: float

    def index_range(self, lo: float, hi: float, axis: str) -> tuple[int, int]:
        e0 = self.lon_edge0 if axis == "lon" else self.lat_edge0
        i0 = int(np.floor((lo - e0) / self.res + 1e-9))
        i1 = int(np.ceil((hi - e0) / self.res - 1e-9)) - 1
        return i0, i1

    def centers(self, i0: int, i1: int, axis: str) -> np.ndarray:
        e0 = self.lon_edge0 if axis == "lon" else self.lat_edge0
        return np.round(e0 + (np.arange(i0, i1 + 1) + 0.5) * self.res, 6)


IMERG_GRID = GridSpec(0.1, -180.0, -90.0)
GLDAS_GRID = GridSpec(0.25, -180.0, -60.0)


def bbox_to_edges(bbox: tuple, grid: GridSpec) -> tuple:
    """Amplía la caja (lon0, lat0, lon1, lat1) a bordes de celda de la rejilla."""
    lon0, lat0, lon1, lat1 = bbox
    i0, i1 = grid.index_range(lon0, lon1, "lon")
    j0, j1 = grid.index_range(lat0, lat1, "lat")
    return i0, i1, j0, j1


# ------------------------------------------------------------------ URLs

def imerg_subset_url(product: str, rel_path: str, i0, i1, j0, j1) -> str:
    """DAP2 en gpm1: precipitation[time][lon][lat]."""
    ce = f"precipitation[0:0][{i0}:{i1}][{j0}:{j1}],lat[{j0}:{j1}],lon[{i0}:{i1}]"
    return f"{GPM_OPENDAP}/{product}/{rel_path}.nc4?{ce}"


def imerg_cloud_url(key: str, granule: str, i0, i1, j0, j1) -> str:
    ds = DATASETS[key]
    gid = urllib.parse.quote(f"{ds['short']}.{ds['ver']}:{granule}")
    g = "/Grid" if granule.endswith(".HDF5") else ""  # los HDF5 de IMERG guardan todo en el grupo /Grid
    ce = f"{g}/precipitation[0:1:0][{i0}:1:{i1}][{j0}:1:{j1}];{g}/lat[{j0}:1:{j1}];{g}/lon[{i0}:1:{i1}]"
    return f"{CLOUD_OPENDAP}/{ds['cmr']}/granules/{gid}.dap.nc4?dap4.ce={urllib.parse.quote(ce, safe='/:;')}"


def gldas_cloud_url(granule: str, i0, i1, j0, j1, variables=GLDAS_VARS) -> str:
    """DAP4 en la nube: variable[time][lat][lon]."""
    ds = DATASETS["GLDAS_M"]
    gid = urllib.parse.quote(f"{ds['short']}.{ds['ver']}:{granule}")
    parts = [f"/{v}[0:1:0][{j0}:1:{j1}][{i0}:1:{i1}]" for v in variables] + [f"/lat[{j0}:1:{j1}]",
                                                                            f"/lon[{i0}:1:{i1}]"]
    ce = ";".join(parts)
    return f"{CLOUD_OPENDAP}/{ds['cmr']}/granules/{gid}.dap.nc4?dap4.ce={urllib.parse.quote(ce, safe='/:;')}"


# ------------------------------------------------------------------ descarga en lote

def _fetch_one(url: str, dest: Path) -> tuple[Path, str, int]:
    body = get(url)
    if not body.startswith(HDF5_MAGIC):
        raise EarthdataError(f"{url} -> respuesta no es HDF5/NetCDF4: {body[:120]!r}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(body)
    tmp.replace(dest)
    return dest, url, len(body)


def fetch_many(jobs: list[tuple[str, Path, dict]], manifest: Manifest, workers: int = 8,
               log_every: int = 500, fallback=None) -> dict:
    """jobs: [(url, destino, extra)]. Salta los que ya están y coinciden con el manifiesto.
    fallback(url, dest) -> url alternativa (o None) si la ruta principal falla."""
    adopted = 0
    for u, d, x in jobs:  # archivo completo ya en disco (de una corrida interrumpida) pero sin registrar
        d = Path(d)
        if d.exists() and manifest.rel(d) not in manifest.data["archivos"]:
            with d.open("rb") as fh:
                ok = fh.read(8) == HDF5_MAGIC
            if ok:
                manifest.add(d, u, save=False, **x, nota="registrado tras una corrida interrumpida (mismo pedido)")
                adopted += 1
    if adopted:
        manifest.save()
    todo = [(u, Path(d), x) for u, d, x in jobs if not manifest.verify(Path(d))]
    errors = []
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_fetch_one, u, d): (u, d, x) for u, d, x in todo}
        for f in as_completed(futs):
            u, d, x = futs[f]
            try:
                dest, url, _ = f.result()
            except EarthdataError as e:
                alt = fallback(u, d) if fallback else None
                if alt is None:
                    errors.append(str(e))
                    continue
                try:
                    dest, url, _ = _fetch_one(alt, d)
                    x = {**x, "ruta": "fallback", "error_ruta_principal": str(e)}
                except EarthdataError as e2:
                    errors.append(f"{e} | fallback: {e2}")
                    continue
            manifest.add(dest, url, save=False, **x)
            done += 1
            if done % log_every == 0:
                manifest.save()
                print(f"  {done}/{len(todo)} archivos", flush=True)
    manifest.save()
    return {"pedidos": len(jobs), "descargados_ahora": done, "ya_en_cache": len(jobs) - len(todo),
            "errores": errors}


# ------------------------------------------------------------------ catálogos de archivos

def _months(y0: int, y1: int):
    return [(y, m) for y in range(y0, y1 + 1) for m in range(1, 13)]


def imerg_monthly_jobs(ddir: Path, bbox: tuple, y0: int, y1: int) -> list:
    i0, i1, j0, j1 = bbox_to_edges(bbox, IMERG_GRID)
    jobs = []
    for y in range(y0, y1 + 1):
        names = list_dir(f"{GPM_DATA}/GPM_3IMERGM.07/{y}/", r"3B-MO\.MS\.MRG\.3IMERG\.[^\"]+\.HDF5")
        for n in names:
            jobs.append((imerg_subset_url("GPM_3IMERGM.07", f"{y}/{n}", i0, i1, j0, j1),
                         ddir / "gesdisc" / "GPM_3IMERGM.07" / f"{n}.nc4",
                         {"dataset": "IMERG_M", "doi": DATASETS["IMERG_M"]["doi"], "granulo": n}))
    return jobs


def imerg_daily_jobs(ddir: Path, bbox: tuple, y0: int, y1: int) -> list:
    """Nombres de archivo construidos (3B-DAY.MS.MRG.3IMERG.AAAAMMDD-S000000-E235959.V07B.nc4) en vez de listar
    288 carpetas (cada listado tarda ~2.6 s). Ruta principal: OPeNDAP en la nube (gpm1 devolvía 503 bajo carga
    el 2026-11-14); respaldo: gpm1."""
    i0, i1, j0, j1 = bbox_to_edges(bbox, IMERG_GRID)
    jobs = []
    for day in pd.date_range(f"{y0}-01-01", f"{y1}-12-31", freq="D"):
        n = f"3B-DAY.MS.MRG.3IMERG.{day:%Y%m%d}-S000000-E235959.V07B.nc4"
        jobs.append((imerg_cloud_url("IMERG_D", n, i0, i1, j0, j1),
                     ddir / "gesdisc" / "GPM_3IMERGDF.07" / str(day.year) / n,
                     {"dataset": "IMERG_D", "doi": DATASETS["IMERG_D"]["doi"], "granulo": n,
                      "url_respaldo": imerg_subset_url("GPM_3IMERGDF.07", f"{day:%Y/%m}/{n}", i0, i1, j0, j1)}))
    return jobs


def imerg_hh_jobs(ddir: Path, bbox: tuple, days: list[str]) -> list:
    i0, i1, j0, j1 = bbox_to_edges(bbox, IMERG_GRID)
    jobs = []
    for day in days:
        t = pd.Timestamp(day)
        doy = t.dayofyear
        names = list_dir(f"{GPM_DATA}/GPM_3IMERGHH.07/{t.year}/{doy:03d}/", r"3B-HHR\.MS\.MRG\.3IMERG\.[^\"]+\.HDF5")
        for n in names:
            jobs.append((imerg_subset_url("GPM_3IMERGHH.07", f"{t.year}/{doy:03d}/{n}", i0, i1, j0, j1),
                         ddir / "gesdisc" / "GPM_3IMERGHH.07" / f"{n}.nc4",
                         {"dataset": "IMERG_HH", "doi": DATASETS["IMERG_HH"]["doi"], "granulo": n}))
    return jobs


def gldas_monthly_jobs(ddir: Path, bbox: tuple, y0: int, y1: int, variables=GLDAS_VARS,
                       sub: str = "GLDAS_NOAH025_M.2.1") -> list:
    i0, i1, j0, j1 = bbox_to_edges(bbox, GLDAS_GRID)
    jobs = []
    for y, m in _months(y0, y1):
        n = f"GLDAS_NOAH025_M.A{y}{m:02d}.021.nc4"
        jobs.append((gldas_cloud_url(n, i0, i1, j0, j1, variables), ddir / "gesdisc" / sub / n,
                     {"dataset": "GLDAS_M", "doi": DATASETS["GLDAS_M"]["doi"], "granulo": n,
                      "variables": list(variables)}))
    return jobs


def imerg_fallback(key: str, bbox: tuple):
    i0, i1, j0, j1 = bbox_to_edges(bbox, IMERG_GRID)

    def fb(url: str, dest: Path):
        if key == "IMERG_D":  # principal = nube; respaldo = gpm1
            day = re.search(r"3IMERG\.(\d{4})(\d{2})\d{2}-", dest.name)
            return imerg_subset_url("GPM_3IMERGDF.07", f"{day.group(1)}/{day.group(2)}/{dest.name}", i0, i1, j0, j1)
        gran = dest.name[:-4] if dest.name.endswith(".HDF5.nc4") else dest.name
        return imerg_cloud_url(key, gran, i0, i1, j0, j1)
    return fb


# ------------------------------------------------------------------ lectura (h5py)

def read_subset(path: Path, var: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Devuelve (valores[lat, lon], lat, lon, atributos). IMERG viene [time][lon][lat]; GLDAS [time][lat][lon]."""
    import h5py
    with h5py.File(path, "r") as h:
        def find(name):
            if name in h:
                return h[name]
            for k in h.keys():
                if k.split("/")[-1] == name or k.endswith("_" + name):
                    return h[k]
            raise KeyError(f"{name} no está en {path}: {list(h.keys())}")
        ds = find(var)
        a = np.asarray(ds[...], dtype="float64")
        attrs = {k: (v.decode() if isinstance(v, bytes) else (v.tolist() if hasattr(v, "tolist") else v))
                 for k, v in ds.attrs.items() if k not in ("DIMENSION_LIST", "REFERENCE_LIST")}
        lat = np.asarray(find("lat")[...], dtype="float64")
        lon = np.asarray(find("lon")[...], dtype="float64")
    a = a[0] if a.ndim == 3 else a
    if a.shape == (lon.size, lat.size) and lon.size != lat.size:
        a = a.T
    elif a.shape == (lon.size, lat.size):  # caja cuadrada: decide por el nombre de la variable
        if var == "precipitation":
            a = a.T
    fill = None
    for k in ("_FillValue", "missing_value", "CodeMissingValue"):
        if k in attrs:
            v = attrs[k]
            fill = float(v[0] if isinstance(v, list) else v)
            break
    if fill is not None:
        a = np.where(np.isclose(a, fill) | (a <= -9000), np.nan, a)
    return a, lat, lon, attrs


# ------------------------------------------------------------------ GRACE/GRACE-FO (contexto nacional)

GRACE_URL = ("https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-protected/"
             "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4/GRCTellus.JPL.200204_202609.GLO.RL06.3M.MSCNv04CRI.nc")
GRACE_DOI = "10.5067/TEMSC-3JC634"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get_follow(url: str, timeout: int = 600) -> bytes:
    """GET con Bearer SOLO en el primer salto; si el servidor redirige (p. ej. a una URL firmada de S3),
    la URL nueva se pide SIN la cabecera (S3 rechaza dos mecanismos de autenticación y el token no debe
    salir de Earthdata)."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Authorization": "Bearer " + _token()})
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303, 307, 308):
            raise EarthdataError(f"{url} -> HTTP {e.code} {e.reason}") from None
        loc = e.headers.get("Location")
    for _ in range(5):
        try:
            with opener.open(urllib.request.Request(loc, headers={"User-Agent": USER_AGENT}), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                loc = e.headers.get("Location")
                continue
            raise EarthdataError(f"{url} (redirigida) -> HTTP {e.code} {e.reason}") from None
    raise EarthdataError(f"{url} -> demasiadas redirecciones")
