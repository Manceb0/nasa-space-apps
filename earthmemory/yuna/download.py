"""Descargas del caso Yuna, con manifiesto (URL, fecha de acceso, SHA-256, licencia) en data/yuna/MANIFEST.json.

- HydroSHEDS HydroBASINS v1c (Norteamérica y Caribe, niveles 6-10) y HydroRIVERS v1.0 (Norteamérica).
  Lehner, B. y Grill, G. (2013) Hydrol. Process. 27(15): 2171-2186. doi:10.1002/hyp.9740.
  Licencia: HydroSHEDS License Agreement (uso libre no comercial y comercial con atribución; ver
  https://www.hydrosheds.org/terms-of-use y el PDF dentro de cada zip).
- JRC Global Surface Water, Monthly Water History v1.4 (1984-2021), 30 m (Pekel et al. 2016, Nature 540:418-422,
  doi:10.1038/nature20584). Licencia: Copernicus/JRC, uso libre con atribución. Se leen SOLO ventanas
  (lectura HTTP por rangos de los GeoTIFF en mosaicos de 256x256); se guarda el recorte con su SHA-256.
- GEOGLOWS v2, caudal diario retrospectivo (simulación hidrológica forzada con ERA5; no son aforos).
  API pública https://geoglows.ecmwf.int/api/v2/ . Licencia: CC BY 4.0 (ECMWF/GEOGLOWS).
- MODIS MCDWD_L3 (archivo reprocesado 2003-2025, LAADS): se intenta y se registra el resultado exacto.
"""

from __future__ import annotations

import io
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .common import DATA, USER_AGENT, earthdata_token, ensure_dirs, http_get, manifest

HYDROSHEDS = "https://data.hydrosheds.org/file"
LIC_HS = ("HydroSHEDS License Agreement (https://www.hydrosheds.org/terms-of-use): uso libre con atribución; "
          "cita Lehner & Grill (2013) doi:10.1002/hyp.9740")
GSW_BASE = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GSWE/MonthlyHistory/LATEST/tiles"
LIC_GSW = "JRC Global Surface Water (EC JRC/Google): uso libre con atribución; cita Pekel et al. (2016) doi:10.1038/nature20584"
GEOGLOWS = "https://geoglows.ecmwf.int/api/v2"
LIC_GG = "GEOGLOWS v2 (ECMWF/BYU/Aquaveo): CC BY 4.0"

# Ventana de lectura de JRC GSW: embalse de Hatillo + Bajo Yuna hasta la bahía de Samaná
GSW_WIN = (-70.42, 18.92, -69.30, 19.42)  # lon0, lat0, lon1, lat1
GSW_TILES = {  # mosaico -> límites (lon0, lon1); fila 240000 = 20N..10N
    "0000240000-0000400000": (-80.0, -70.0),
    "0000240000-0000440000": (-70.0, -60.0),
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ------------------------------------------------------------------ HydroSHEDS

def hydrosheds(man) -> None:
    out = DATA / "hydrosheds"
    out.mkdir(parents=True, exist_ok=True)
    files = [f"HydroBASINS/standard/hybas_na_lev{lv:02d}_v1c.zip" for lv in range(6, 11)]
    files.append("HydroRIVERS/HydroRIVERS_v10_na_shp.zip")
    for f in files:
        dest = out / Path(f).name
        if man.has(dest):
            continue
        url = f"{HYDROSHEDS}/{f}"
        body = http_get(url, timeout=900)
        dest.write_bytes(body)
        man.add(dest, url, dataset="HydroSHEDS", accedido=_now(), licencia=LIC_HS,
                cita="Lehner, B., Grill, G. (2013). Global river hydrography and network routing: baseline data and "
                     "new approaches to study the world's large river systems. Hydrol. Process. 27, 2171-2186.")
        print(f"  {dest.name}: {len(body) / 1e6:.1f} MB", flush=True)


# ------------------------------------------------------------------ JRC GSW mensual (ventanas)

def _gsw_month(y: int, m: int) -> tuple[np.ndarray, dict]:
    import rasterio
    from rasterio.windows import from_bounds
    lon0, lat0, lon1, lat1 = GSW_WIN
    parts, urls = [], []
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                      GDAL_HTTP_USERAGENT=USER_AGENT, GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="3"):
        for tile, (t0, t1) in GSW_TILES.items():
            a0, a1 = max(lon0, t0), min(lon1, t1)
            if a0 >= a1:
                continue
            url = f"{GSW_BASE}/{y}/{y}_{m:02d}/{y}_{m:02d}-{tile}.tif"
            with rasterio.open("/vsicurl/" + url) as s:
                w = from_bounds(a0, lat0, a1, lat1, s.transform).round_offsets().round_lengths()
                parts.append(s.read(1, window=w))
                tr = s.window_transform(w)
            urls.append(url)
            if len(parts) == 1:
                tr0 = tr
    arr = np.concatenate(parts, axis=1) if len(parts) > 1 else parts[0]
    return arr, {"urls": urls, "transform": list(tr0)[:6]}


def gsw(man, workers: int = 8, years=(2001, 2020)) -> None:
    # v1.4 «LATEST» en el FTP del JRC: 2021 devuelve 404 para estos mosaicos (probado 2026-11-14) → 2001-2020
    out = DATA / "gsw_mensual"
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(y, m) for y in range(years[0], years[1] + 1) for m in range(1, 13)
            if not man.has(out / f"gsw_{y}_{m:02d}.npz")]
    if not jobs:
        return

    def one(y, m):
        for k in range(4):
            try:
                return _gsw_month(y, m)
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(3 * (k + 1))
        raise RuntimeError(f"GSW {y}-{m:02d}: {last}")

    errs = []
    with ThreadPoolExecutor(workers) as ex:
        fut = {ex.submit(one, y, m): (y, m) for y, m in jobs}
        for i, f in enumerate(as_completed(fut)):
            y, m = fut[f]
            try:
                arr, meta = f.result()
            except Exception as e:  # noqa: BLE001
                errs.append(str(e))
                continue
            dest = out / f"gsw_{y}_{m:02d}.npz"
            np.savez_compressed(dest, agua=arr.astype(np.uint8), transform=np.array(meta["transform"]))
            man.add(dest, " | ".join(meta["urls"]), save=False, dataset="JRC_GSW_MonthlyHistory_v1.4",
                    accedido=_now(), licencia=LIC_GSW, ventana_lonlat=list(GSW_WIN),
                    nota="recorte de ventana por lectura HTTP por rangos; 0 = sin dato, 1 = no agua, 2 = agua")
            if i % 24 == 0:
                print(f"  GSW {i + 1}/{len(jobs)}", flush=True)
    man.save()
    man.note("JRC_GSW", {"estado": "ok" if not errs else "parcial", "errores": errs[:20], "meses_pedidos": len(jobs)})


# ------------------------------------------------------------------ GEOGLOWS v2

def geoglows_river_id(lat: float, lon: float) -> int:
    u = f"{GEOGLOWS}/getriverid?lat={lat}&lon={lon}"
    return int(json.loads(http_get(u, timeout=120))["river_id"])


def geoglows_main_id(lat: float, lon: float, paso: float = 0.003, n: int = 4) -> tuple[int, dict]:
    """getriverid devuelve el tramo MÁS CERCANO, que a menudo es un arroyo lateral (probado: caudales medios de
    0.04-4 m³/s donde HydroRIVERS da 24-90). Se buscan los tramos en una rejilla de ±n·paso grados alrededor del
    punto y se elige el de mayor caudal medio retrospectivo (serie mensual), que es el cauce principal."""
    import pandas as pd
    cand = set()
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            try:
                cand.add(geoglows_river_id(round(lat + i * paso, 5), round(lon + j * paso, 5)))
            except Exception:  # noqa: BLE001
                pass
    medias = {}
    for rid in cand:
        try:
            s = pd.read_csv(io.BytesIO(http_get(f"{GEOGLOWS}/retrospectivemonthly/{rid}?format=csv", timeout=120)))
            medias[rid] = float(s.iloc[:, 1].mean())
        except Exception:  # noqa: BLE001
            pass
    best = max(medias, key=medias.get)
    return best, {str(k): round(v, 2) for k, v in sorted(medias.items(), key=lambda kv: -kv[1])}


def geoglows(man, puntos: dict[str, tuple[float, float]]) -> dict:
    out = DATA / "geoglows"
    out.mkdir(parents=True, exist_ok=True)
    ids = {}
    for nombre, (lat, lon) in puntos.items():
        try:
            rid, cand = geoglows_main_id(lat, lon)
        except Exception as e:  # noqa: BLE001
            ids[nombre] = {"error": str(e)}
            continue
        ids.setdefault("_candidatos", {})[nombre] = cand
        dest = out / f"retro_diario_{rid}.csv"
        url = f"{GEOGLOWS}/retrospectivedaily/{rid}?format=csv"
        if not man.has(dest):
            try:
                dest.write_bytes(http_get(url, timeout=600))
                man.add(dest, url, dataset="GEOGLOWS_v2_retrospectivo_diario", accedido=_now(), licencia=LIC_GG,
                        clase="SIMULACIÓN HIDROLÓGICA (forzada con ERA5; no aforos)", punto=[lat, lon], nombre=nombre)
            except Exception as e:  # noqa: BLE001
                ids[nombre] = {"river_id": rid, "error": str(e)}
                continue
        ids[nombre] = {"river_id": rid, "lat": lat, "lon": lon, "archivo": dest.name}
    man.note("GEOGLOWS", ids)
    return ids


# ------------------------------------------------------------------ MODIS MCDWD_L3 (intento documentado)

def mcdwd_probe(man) -> dict:
    """Intenta UN archivo del archivo reprocesado MCDWD_L3 (LAADS). Registra el resultado exacto, sin token."""
    import requests
    tok = earthdata_token()
    res = {"coleccion": "MCDWD_L3 C61 (reprocesado 2003-2025, LAADS)", "fecha_prueba": _now()}
    listing = ("https://ladsweb.modaps.eosdis.nasa.gov/api/v2/content/details/allData/61/MCDWD_L3/2016/322/"
               "?fields=all&format=json")
    try:
        d = json.loads(http_get(listing, timeout=120))
        sel = [c for c in d["content"] if ".h10v07." in c["name"] or ".h11v07." in c["name"]]
        res["listado"] = {c["name"]: c["size"] for c in sel}
        if tok and sel:
            u = f"https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3/2016/322/{sel[0]['name']}"
            r = requests.get(u, headers={"Authorization": "Bearer " + tok, "User-Agent": USER_AGENT},
                             timeout=120, allow_redirects=False)
            loc = r.headers.get("Location", "")
            res["descarga"] = {"url": u, "http": r.status_code,
                               "redirige_a": loc.split("?")[0][:120] if loc else None}
            if r.status_code in (302, 303) and "/profiles/licenses/" in loc:
                res["estado"] = ("bloqueado: LAADS exige aceptar una licencia de datos en el perfil de Earthdata "
                                 "(acción de cuenta que debe hacer la persona usuaria)")
            elif r.status_code == 200:
                res["estado"] = "descargable"
        res.setdefault("estado", "sin token" if not tok else "desconocido")
    except Exception as e:  # noqa: BLE001
        res["estado"] = f"error: {e}"
    res["formato"] = ("HDF (probablemente HDF4/HDF-EOS2, como el resto de MODIS C61); la imagen Docker trae GDAL "
                      "con HDF5 y netCDF pero sin HDF4, así que además haría falta pyhdf o un GDAL con HDF4")
    man.note("MCDWD_L3", res)
    return res


def run(puntos_geoglows: dict | None = None, sin_gsw: bool = False) -> dict:
    ensure_dirs()
    man = manifest()
    print("· HydroSHEDS", flush=True)
    hydrosheds(man)
    if not sin_gsw:
        print("· JRC GSW mensual (ventanas)", flush=True)
        gsw(man)
    print("· MCDWD_L3 (prueba)", flush=True)
    mcdwd_probe(man)
    ids = {}
    if puntos_geoglows:
        print("· GEOGLOWS v2", flush=True)
        ids = geoglows(man, puntos_geoglows)
    return ids


if __name__ == "__main__":
    run()
