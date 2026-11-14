"""Descargas de alta resolución para la República Dominicana, con caché y manifiesto (URL + SHA-256).

    python -m earthmemory.hr.download [--sin-smap] [--hilos 12]

Todo es público y sin login, salvo SMAP L4 (NASA, token de Earthdata leído SOLO de archivo; si no hay token
se salta y queda anotado). Cada ruta anota en MANIFEST.json["rutas"] su estado y el error exacto si falló.
Los archivos se guardan como llegaron (tif.gz, NetCDF, GeoTIFF); los recortes se describen con su URL.
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from .common import BBOX, DATA, ROOT, YEARS, FetchError, Manifest, earthdata_token, http_get, http_head

CHIRPS = "https://data.chc.ucsb.edu/products/CHIRPS/v2.0"
TC_NCSS = "http://thredds.northwestknowledge.net:8080/thredds/ncss/TERRACLIMATE_ALL/data"
TC_VARS = ("soil", "PDSI", "aet", "def", "ppt", "pet")
SG_WCS = "https://maps.isric.org/mapserv?map=/map/{prop}.map"
SG_PROPS = ("clay", "sand")
SG_DEPTHS = ("0-5cm", "5-15cm", "15-30cm")
DEM = "https://copernicus-dem-90m.s3.amazonaws.com"
WC = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"
WC_TILES = ("N15W072", "N18W072", "N18W069")
GB_API = "https://www.geoboundaries.org/api/current/gbOpen/DOM/{adm}/"
ADM0_URL = ("https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/DOM/ADM0/"
            "geoBoundaries-DOM-ADM0_simplified.geojson")
SMAP_CMR = "C3480440870-NSIDC_CPRD"
SMAP_OPENDAP = "https://opendap.earthdata.nasa.gov/collections/" + SMAP_CMR + "/granules/"
SMAP_VARS = ("sm_rootzone", "sm_surface", "precipitation_total_surface_flux")
GZ_MAGIC = b"\x1f\x8b"
TIF_MAGIC = (b"II*\x00", b"MM\x00*")
CDF_MAGIC = b"CDF"
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"


def _save(dest: Path, body: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(body)
    tmp.replace(dest)


def _batch(man: Manifest, key: str, jobs: list, magic, workers: int, headers: dict | None = None,
           meta: dict | None = None) -> dict:
    """jobs: [(url, dest)]. Descarga lo que falta, valida la firma del archivo y registra en el manifiesto."""
    # pendiente = falta, tamaño distinto o registrado con OTRA URL (p. ej. otra versión de proceso del granulo)
    todo = [(u, d) for u, d in jobs
            if not man.has(d) or man.data["archivos"].get(man.rel(d), {}).get("url") != u]
    errors = []

    def one(u, d):
        b = http_get(u, headers=headers)
        if not any(b.startswith(m) for m in (magic if isinstance(magic, tuple) else (magic,))):
            raise FetchError(f"{u} -> firma inesperada {b[:60]!r}")
        _save(d, b)
        return u, d

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one, u, d): (u, d) for u, d in todo}
        for k, f in enumerate(as_completed(futs), 1):
            try:
                u, d = f.result()
                man.add(d, u, save=False, dataset=key, **(meta or {}))
            except FetchError as e:
                errors.append(str(e))
            if k % 250 == 0:
                print(f"  [{key}] {k}/{len(todo)}", flush=True)
    man.save()
    st = {"estado": "ok" if not errors else ("parcial" if len(errors) < len(jobs) else "falló"),
          "pedidos": len(jobs), "ya_en_cache": len(jobs) - len(todo), "descargados": len(todo) - len(errors),
          "n_errores": len(errors), "errores_muestra": errors[:5]}
    man.note(key, st)
    print(f"[{key}] {json.dumps({k: v for k, v in st.items() if k != 'errores_muestra'})}", flush=True)
    return st


# ------------------------------------------------------------------ límites

def boundaries(man: Manifest) -> None:
    d = DATA / "limites"
    adm0 = d / "geoBoundaries-DOM-ADM0_simplified.geojson"
    if not man.has(adm0):
        src = ROOT / "appeears" / "rd-adm0.geojson"
        d.mkdir(parents=True, exist_ok=True)
        try:
            body = http_get(ADM0_URL)
            json.loads(body)
            _save(adm0, body)
            origen = "descargado"
        except FetchError:
            shutil.copyfile(src, adm0)
            origen = "copiado de appeears/rd-adm0.geojson (misma URL según appeears/METODO.md)"
        man.add(adm0, ADM0_URL, dataset="GEOBOUNDARIES", boundaryID="DOM-ADM0-20870125",
                licencia="CC BY 4.0", origen=origen)
    for adm in ("ADM0", "ADM1"):
        mp = d / f"geoBoundaries-DOM-{adm}.api.json"
        if not man.has(mp):
            body = http_get(GB_API.format(adm=adm))
            _save(mp, body)
            man.add(mp, GB_API.format(adm=adm), dataset="GEOBOUNDARIES")
    meta = json.loads((d / "geoBoundaries-DOM-ADM1.api.json").read_text(encoding="utf-8"))
    gj = d / "geoBoundaries-DOM-ADM1.geojson"
    if not man.has(gj):
        body = http_get(meta["gjDownloadURL"])
        json.loads(body)
        _save(gj, body)
        man.add(gj, meta["gjDownloadURL"], dataset="GEOBOUNDARIES", boundaryID=meta.get("boundaryID"),
                licencia=meta.get("boundaryLicense"), fuente_original=meta.get("boundarySource"))
    man.note("LIMITES", {"estado": "ok", "adm1": meta.get("boundaryID"), "licencia_adm1": meta.get("boundaryLicense")})


# ------------------------------------------------------------------ CHIRPS

def chirps(man: Manifest, workers: int) -> None:
    y0, y1 = YEARS
    jobs = [(f"{CHIRPS}/camer-carib_monthly/tifs/chirps-v2.0.{y}.{m:02d}.tif.gz",
             DATA / "chirps" / "mensual" / f"chirps-v2.0.{y}.{m:02d}.tif.gz")
            for y in range(y0, y1 + 1) for m in range(1, 13)]
    _batch(man, "CHIRPS_M", jobs, GZ_MAGIC, workers, meta={"version": "2.0", "dominio": "camer-carib"})
    jobs = [(f"{CHIRPS}/whem_daily/tifs/p05/2023/chirps-v2.0.2023.11.{d:02d}.tif.gz",
             DATA / "chirps" / "diario" / f"chirps-v2.0.2023.11.{d:02d}.tif.gz") for d in range(1, 31)]
    _batch(man, "CHIRPS_D", jobs, GZ_MAGIC, workers, meta={"version": "2.0", "dominio": "whem p05"})


# ------------------------------------------------------------------ TerraClimate (NCSS)

def tc_url(var: str, year: int) -> str:
    lon0, lat0, lon1, lat1 = BBOX
    return (f"{TC_NCSS}/TerraClimate_{var}_{year}.nc?var={var}&north={lat1}&west={lon0}&east={lon1}&south={lat0}"
            f"&horizStride=1&temporal=all&accept=netcdf")


def terraclimate(man: Manifest, workers: int) -> None:
    y0, y1 = YEARS
    jobs = [(tc_url(v, y), DATA / "terraclimate" / v / f"TerraClimate_{v}_{y}_RD.nc")
            for v in TC_VARS for y in range(y0, y1 + 1)]
    # El THREDDS es un servidor universitario: pocos hilos
    _batch(man, "TERRACLIMATE", jobs, CDF_MAGIC, min(workers, 4),
           meta={"servicio": "THREDDS NCSS (recorte de caja, NetCDF-3)"})


# ------------------------------------------------------------------ SoilGrids (WCS)

def sg_url(prop: str, depth: str, res: float = 0.0025) -> str:
    lon0, lat0, lon1, lat1 = BBOX
    crs = "http://www.opengis.net/def/crs/EPSG/0/4326"
    q = (f"&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID={prop}_{depth}_mean&FORMAT=image/tiff"
         f"&SUBSET=long({lon0},{lon1})&SUBSET=lat({lat0},{lat1})&SUBSETTINGCRS={crs}&OUTPUTCRS={crs}"
         f"&RESOLUTION=long({res})&RESOLUTION=lat({res})")
    return SG_WCS.format(prop=prop) + q


def soilgrids(man: Manifest) -> None:
    jobs = [(sg_url(p, d), DATA / "soilgrids" / f"{p}_{d}_mean_RD_0.0025deg.tif") for p in SG_PROPS for d in SG_DEPTHS]
    _batch(man, "SOILGRIDS", jobs, TIF_MAGIC, 2, meta={"unidades": "g/kg (valor/10 = %)", "licencia": "CC BY 4.0"})


# ------------------------------------------------------------------ Copernicus DEM GLO-90

def dem_tiles() -> list[tuple[str, str]]:
    out = []
    for lat in (17, 18, 19):
        for lon in (72, 71, 70, 69):
            name = f"Copernicus_DSM_COG_30_N{lat:02d}_00_W{lon:03d}_00_DEM"
            out.append((f"{DEM}/{name}/{name}.tif", name))
    return out


def dem(man: Manifest, workers: int) -> None:
    jobs = [(u, DATA / "dem" / f"{n}.tif") for u, n in dem_tiles()]
    st = _batch(man, "COPDEM", jobs, TIF_MAGIC, workers,
                meta={"licencia": "Copernicus DEM GLO-90 (uso libre con atribución)"})
    if st["n_errores"]:
        st["nota"] = ("Las 404 son las teselas 17-18 N entre 71 y 68 O: solo mar al sur de la isla (el bucket no "
                      "publica teselas sin tierra). Beata y Alto Velo caen en N17 W072, que sí se descargó.")
        man.note("COPDEM", st)


# ------------------------------------------------------------------ ESA WorldCover (lectura de la vista 1/8)

def worldcover(man: Manifest, ov_level: int = 2) -> None:
    """Lee por HTTP (rangos de bytes del COG) la vista general 1/8 (~80 m) de las 3 teselas que tocan la RD y
    guarda un único GeoTIFF de la caja. Además guarda una ventana de validación a 10 m (0.25°×0.25°) para medir
    el error de usar la vista general en las fracciones por celda 0.05°."""
    import rasterio
    from rasterio.windows import from_bounds

    out = DATA / "worldcover" / "ESA_WorldCover_10m_2021_v200_RD_vista8.tif"
    val = DATA / "worldcover" / "ESA_WorldCover_10m_2021_v200_validacion_10m.tif"
    if man.has(out) and man.has(val):
        return
    lon0, lat0, lon1, lat1 = BBOX
    res = 8.333333333333333e-05 * 8
    nx, ny = int(round((lon1 - lon0) / res)), int(round((lat1 - lat0) / res))
    mosaic = np.zeros((ny, nx), np.uint8)
    heads = {}
    env = rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="3",
                       CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")
    with env:
        for t in WC_TILES:
            url = f"{WC}/ESA_WorldCover_10m_2021_v200_{t}_Map.tif"
            heads[t] = http_head(url)
            with rasterio.open("/vsicurl/" + url, overview_level=ov_level) as r:
                tb = r.bounds
                b = (max(lon0, tb.left), max(lat0, tb.bottom), min(lon1, tb.right), min(lat1, tb.top))
                if b[0] >= b[2] or b[1] >= b[3]:
                    continue
                w = from_bounds(*b, transform=r.transform).round_offsets().round_lengths()
                a = r.read(1, window=w)
                c0 = int(round((b[0] - lon0) / res))
                r0 = int(round((lat1 - b[3]) / res))
                hh, ww = min(a.shape[0], ny - r0), min(a.shape[1], nx - c0)
                sub = mosaic[r0:r0 + hh, c0:c0 + ww]
                np.copyto(sub, a[:hh, :ww], where=a[:hh, :ww] > 0)
                tags = r.tags()
        prof = {"driver": "GTiff", "dtype": "uint8", "width": nx, "height": ny, "count": 1, "crs": "EPSG:4326",
                "transform": rasterio.transform.from_origin(lon0, lat1, res, res), "nodata": 0,
                "compress": "deflate", "tiled": True}
        out.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(out, "w", **prof) as dst:
            dst.write(mosaic, 1)
            dst.update_tags(fuente="ESA WorldCover 10m 2021 v200", vista_general="1/8 (overview_level=2)",
                            licencia=tags.get("license", "CC-BY 4.0"))
        man.add(out, f"{WC}/ESA_WorldCover_10m_2021_v200_{{{','.join(WC_TILES)}}}_Map.tif", dataset="WORLDCOVER",
                metodo="lectura por rangos HTTP (GDAL /vsicurl/) de la vista general 1/8 del COG; mosaico de 3 teselas",
                cabeceras_remotas=heads, version=tags.get("algorithm_version"), licencia=tags.get("license"))
        # Ventana de validación a 10 m (zona mixta del Cibao: 70.75-70.50 O, 19.25-19.50 N)
        vb = (-70.75, 19.25, -70.50, 19.50)
        url = f"{WC}/ESA_WorldCover_10m_2021_v200_N18W072_Map.tif"
        with rasterio.open("/vsicurl/" + url) as r:
            w = from_bounds(*vb, transform=r.transform).round_offsets().round_lengths()
            a = r.read(1, window=w)
            prof2 = {**prof, "width": a.shape[1], "height": a.shape[0],
                     "transform": rasterio.windows.transform(w, r.transform)}
        with rasterio.open(val, "w", **prof2) as dst:
            dst.write(a, 1)
        man.add(val, url, dataset="WORLDCOVER", metodo=f"ventana a resolución completa {vb}", cabeceras_remotas=heads)
    man.note("WORLDCOVER", {"estado": "ok", "teselas": list(WC_TILES), "vista_general": "1/8 (~80 m)"})


# ------------------------------------------------------------------ SMAP L4 (NASA, token)

R_EASE = 6378137.0
E2_EASE = 0.0066943799901413165


def ease2_xy(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """EASE-Grid 2.0 global (EPSG:6933): Lambert cilíndrica equivalente, elipsoide WGS84, paralelo estándar 30°."""
    e = np.sqrt(E2_EASE)
    p0 = np.radians(30.0)
    k0 = np.cos(p0) / np.sqrt(1 - E2_EASE * np.sin(p0) ** 2)
    phi = np.radians(lat)
    s = np.sin(phi)
    q = (1 - E2_EASE) * (s / (1 - E2_EASE * s ** 2) - (1 / (2 * e)) * np.log((1 - e * s) / (1 + e * s)))
    return R_EASE * k0 * np.radians(lon), R_EASE * q / (2 * k0)


def _cmr_granules(year: int, token: str) -> list[str]:
    """GranuleUR de las ventanas 12-15 UTC (etiqueta T133000) del año, desde CMR (público)."""
    urs, page = [], 1
    while True:
        u = (f"https://cmr.earthdata.nasa.gov/search/granules.json?collection_concept_id={SMAP_CMR}"
             f"&temporal={year}-01-01T00:00:00Z,{year}-12-31T23:59:59Z&page_size=2000&page_num={page}"
             f"&readable_granule_name=*T133000*&options[readable_granule_name][pattern]=true")
        d = json.loads(http_get(u))
        ent = d["feed"]["entry"]
        urs += [e["title"] for e in ent]
        if len(ent) < 2000:
            break
        page += 1
    return sorted(set(urs))


def smap(man: Manifest, workers: int) -> None:
    token = earthdata_token()
    if not token:
        man.note("SMAP_L4", {"estado": "omitido", "motivo": "no hay token de Earthdata en archivo"})
        return
    import h5py
    hdr = {"Authorization": "Bearer " + token}
    ddir = DATA / "smap"
    xy = ddir / "SPL4SMGP_008_xy.nc4"
    probe = "SMAP_L4_SM_gph_20200615T133000_Vv8010_001.h5"
    if not man.has(xy):
        u = SMAP_OPENDAP + urllib.parse.quote(probe) + ".dap.nc4?dap4.ce=" + urllib.parse.quote("/x;/y", safe="/:;")
        _save(xy, http_get(u, headers=hdr))
        man.add(xy, u, dataset="SMAP_L4", nota="coordenadas EASE-Grid 2.0 (x, y) de la rejilla 9 km")
    with h5py.File(xy, "r") as f:
        X, Y = f["x"][:], f["y"][:]
    lon0, lat0, lon1, lat1 = BBOX
    bx, by = ease2_xy(np.array([lon0, lon1]), np.array([lat0, lat1]))
    cols = np.flatnonzero((X >= bx[0] - 4600) & (X <= bx[1] + 4600))
    rows = np.flatnonzero((Y >= by[0] - 4600) & (Y <= by[1] + 4600))
    c0, c1, r0, r1 = int(cols[0]), int(cols[-1]), int(rows[0]), int(rows[-1])
    ce = ";".join([f"/Geophysical_Data/{v}[{r0}:1:{r1}][{c0}:1:{c1}]" for v in SMAP_VARS]
                  + [f"/cell_lat[{r0}:1:{r1}][{c0}:1:{c1}]", f"/cell_lon[{r0}:1:{r1}][{c0}:1:{c1}]"])
    ce_q = urllib.parse.quote(ce, safe="/:;")
    # Un granulo por día; si CMR lista dos versiones de proceso del mismo día (p. ej. Vv8010 y Vv8011), se usa
    # la más reciente (orden lexicográfico de la etiqueta), para que la corrida sea determinista.
    best = {}
    for y in range(2015, YEARS[1] + 1):
        for ur in _cmr_granules(y, token):
            day = ur.split("_")[4][:8]
            best[day] = max(best.get(day, ur), ur)
    jobs = [(SMAP_OPENDAP + urllib.parse.quote(ur) + ".dap.nc4?dap4.ce=" + ce_q,
             ddir / "diario" / day[:4] / f"SPL4SMGP_{day}_T1330_RD.nc4") for day, ur in sorted(best.items())]
    man.note("SMAP_L4_indices", {"filas": [r0, r1], "columnas": [c0, c1], "ventana": "12-15 UTC (T133000)",
                                 "variables": list(SMAP_VARS)})
    _batch(man, "SMAP_L4", jobs, HDF5_MAGIC, workers, headers=hdr,
           meta={"version": "V008", "doi": "10.5067/T5RUATAQREF8"})


def run(args) -> None:
    man = Manifest(DATA / "MANIFEST.json")
    steps = [("límites", lambda: boundaries(man)), ("CHIRPS", lambda: chirps(man, args.hilos)),
             ("TerraClimate", lambda: terraclimate(man, args.hilos)), ("SoilGrids", lambda: soilgrids(man)),
             ("DEM", lambda: dem(man, args.hilos)), ("WorldCover", lambda: worldcover(man))]
    if not args.sin_smap:
        steps.append(("SMAP", lambda: smap(man, args.hilos)))
    only = set(args.solo or [])
    for name, fn in steps:
        if only and name not in only:
            continue
        print(f"== {name}", flush=True)
        try:
            fn()
        except Exception as e:  # una fuente caída no detiene las demás; queda anotada
            man.note(name.upper(), {"estado": "falló", "error": f"{type(e).__name__}: {e}"[:500]})
            print(f"  ERROR {name}: {type(e).__name__}: {e}"[:500], flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hilos", type=int, default=12)
    ap.add_argument("--sin-smap", dest="sin_smap", action="store_true")
    ap.add_argument("--solo", nargs="*", help="límites CHIRPS TerraClimate SoilGrids DEM WorldCover SMAP")
    run(ap.parse_args(argv))


if __name__ == "__main__":
    main()
