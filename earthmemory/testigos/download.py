"""Descargas de los testigos, con caché y manifiesto (URL, fecha de acceso, SHA-256, cita).

    python -m earthmemory.testigos.download [--solo smap hansen appeears] [--hilos 12] [--probar]

- SMAP L3 Enhanced (SPL3SMP_E V006, NSIDC): recorte por OPeNDAP en la nube (DAP4) de la caja de la RD, un
  granulo por día, retrievals AM (6:00 local, descendente) y PM (18:00, ascendente) con sus banderas de calidad,
  contenido de agua de la vegetación (VWC) y bandera de superficie. Token de Earthdata leído SOLO de archivo.
- Hansen Global Forest Change v1.13: teselas completas 20N_080W (lossyear, treecover2000), públicas.
- AppEEARS: SOLO consulta el estado del pedido del usuario con el token como Bearer; si la API pide otro login,
  se detiene y lo anota (no se usan contraseñas).
El token nunca se imprime ni se escribe: los errores llevan URL y código, nunca cabeceras.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from ..hr.common import USER_AGENT, FetchError
from .common import BBOX, CITAS, DATA, NAC_HR, earthdata_token, http_get, manifest

SMAP_CMR = "C2938664763-NSIDC_CPRD"           # SPL3SMP_E versión 006 (la última en CMR el 2026-11-14)
SMAP_OPENDAP = "https://opendap.earthdata.nasa.gov/collections/" + SMAP_CMR + "/granules/"
SMAP_DOI = "10.5067/M20OXIZHY3RJ"
AM, PM = "Soil_Moisture_Retrieval_Data_AM", "Soil_Moisture_Retrieval_Data_PM"
SMAP_VARS = {AM: ["soil_moisture", "retrieval_qual_flag", "vegetation_water_content", "surface_flag"],
             PM: ["soil_moisture_pm", "retrieval_qual_flag_pm", "vegetation_water_content_pm", "surface_flag_pm"]}
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"
TIF_MAGIC = (b"II*\x00", b"MM\x00*")

HANSEN_VER = "GFC-2025-v1.13"
HANSEN_URL = "https://storage.googleapis.com/earthenginepartners-hansen/{v}/Hansen_{v}_{layer}_20N_080W.tif"

APPEEARS_API = "https://appeears.earthdatacloud.nasa.gov/api"
APPEEARS_TASK = "8ad4ac19-6b4c-4445-8443-2c4a4fc7f928"


# ------------------------------------------------------------------ EASE-Grid 2.0 (9 km)

def smap_rows_cols() -> tuple[int, int, int, int]:
    """Filas/columnas EASE-2 9 km que cubren la caja, a partir de las coordenadas x, y del archivo de SMAP L4
    (misma rejilla M09 global, 3856 × 1624) ya guardado por el motor de alta resolución."""
    import h5py
    from ..hr.download import ease2_xy
    with h5py.File(NAC_HR / "smap" / "SPL4SMGP_008_xy.nc4", "r") as f:
        X, Y = f["x"][:], f["y"][:]
    lon0, lat0, lon1, lat1 = BBOX
    bx, by = ease2_xy(np.array([lon0, lon1]), np.array([lat0, lat1]))
    cols = np.flatnonzero((X >= bx[0] - 4600) & (X <= bx[1] + 4600))
    rows = np.flatnonzero((Y >= by[0] - 4600) & (Y <= by[1] + 4600))
    return int(rows[0]), int(rows[-1]), int(cols[0]), int(cols[-1])


def _cmr_all(concept: str, t0: str, t1: str) -> list[str]:
    urs, page = [], 1
    while True:
        u = (f"https://cmr.earthdata.nasa.gov/search/granules.json?collection_concept_id={concept}"
             f"&temporal={t0},{t1}&page_size=2000&page_num={page}")
        ent = json.loads(http_get(u))["feed"]["entry"]
        urs += [e["title"] for e in ent]
        if len(ent) < 2000:
            break
        page += 1
    return sorted(set(urs))


def _save(dest: Path, body: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(body)
    tmp.replace(dest)


def smap_constraint(r0, r1, c0, c1) -> str:
    parts = [f"/{g}/{v}[{r0}:1:{r1}][{c0}:1:{c1}]" for g, vs in SMAP_VARS.items() for v in vs]
    return urllib.parse.quote(";".join(parts), safe="/:;")


def probe_smap() -> None:
    """Lista los nombres de variables de un granulo (DMR) para confirmar la estructura. No imprime el token."""
    tok = earthdata_token()
    g = "SMAP_L3_SM_P_E_20200615_R19240_001.h5"
    body = http_get(SMAP_OPENDAP + g + ".dmr.xml", headers={"Authorization": "Bearer " + tok}).decode("utf-8", "ignore")
    import re
    names = re.findall(r'<(?:Float32|Float64|UInt16|UInt8|Int32|Int16|String)\s+name="([^"]+)"', body)
    print(len(names), "variables;", [n for n in names if "moisture" in n or "flag" in n or "water_content" in n][:40])


def smap(man, workers: int = 12) -> dict:
    tok = earthdata_token()
    if not tok:
        st = {"estado": "omitido", "motivo": "no hay token de Earthdata en archivo"}
        man.note("SMAP_L3E", st)
        return st
    hdr = {"Authorization": "Bearer " + tok}
    r0, r1, c0, c1 = smap_rows_cols()
    ce = smap_constraint(r0, r1, c0, c1)
    best = {}
    for ur in _cmr_all(SMAP_CMR, "2015-03-31T00:00:00Z", "2024-12-31T23:59:59Z"):
        day = ur.split("_")[5]
        best[day] = max(best.get(day, ur), ur)      # si hay dos procesos del mismo día, el más reciente
    jobs = [(SMAP_OPENDAP + urllib.parse.quote(ur) + ".dap.nc4?dap4.ce=" + ce,
             DATA / "smap_l3e" / day[:4] / f"SPL3SMP_E_006_{day}_RD.nc4", ur) for day, ur in sorted(best.items())]
    man.note("SMAP_L3E_indices", {"filas": [r0, r1], "columnas": [c0, c1], "rejilla": "EASE-Grid 2.0 global 9 km (M09)",
                                  "variables": SMAP_VARS, "granulos_cmr": len(jobs), "coleccion_cmr": SMAP_CMR})
    todo = [(u, d, g) for u, d, g in jobs if not man.has(d)]
    errors = []

    def one(u, d):
        b = http_get(u, headers=hdr, retries=5, timeout=240)
        if not b.startswith(HDF5_MAGIC):
            raise FetchError(f"{u.split('?')[0]} -> firma inesperada {b[:60]!r}")
        _save(d, b)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one, u, d): (u, d, g) for u, d, g in todo}
        for k, f in enumerate(as_completed(futs), 1):
            u, d, g = futs[f]
            try:
                f.result()
                man.add(d, u, save=False, dataset="SPL3SMP_E", version="006", doi=SMAP_DOI, granulo=g,
                        cita=CITAS["SMAP_L3E"], nota="recorte OPeNDAP (DAP4) de la caja de la RD")
            except FetchError as e:
                errors.append(str(e))
            if k % 250 == 0:
                print(f"  [SMAP L3E] {k}/{len(todo)}", flush=True)
                man.save()
    man.save()
    st = {"estado": "ok" if not errors else ("parcial" if len(errors) < len(jobs) else "falló"),
          "pedidos": len(jobs), "ya_en_cache": len(jobs) - len(todo), "descargados": len(todo) - len(errors),
          "n_errores": len(errors), "errores_muestra": errors[:5]}
    man.note("SMAP_L3E", st)
    print("[SMAP L3E]", json.dumps({k: v for k, v in st.items() if k != "errores_muestra"}), flush=True)
    return st


# ------------------------------------------------------------------ Hansen GFC

def hansen(man) -> dict:
    out = {}
    for layer in ("lossyear", "treecover2000"):
        u = HANSEN_URL.format(v=HANSEN_VER, layer=layer)
        d = DATA / "hansen" / Path(u).name
        if not man.has(d):
            b = http_get(u, timeout=900)
            if not any(b.startswith(m) for m in TIF_MAGIC):
                raise FetchError(f"{u} -> no es GeoTIFF")
            _save(d, b)
            man.add(d, u, dataset="Hansen GFC", version=HANSEN_VER, cita=CITAS["HANSEN"], licencia="CC BY 4.0",
                    nota="tesela completa 10° × 10° (20N-10N, 80W-70W)")
        out[layer] = "ok"
    man.note("HANSEN", {"estado": "ok", "version": HANSEN_VER, "teselas": ["20N_080W"]})
    return out


# ------------------------------------------------------------------ AppEEARS (solo con el token Bearer)

def _api(url: str, tok: str, timeout: int = 120) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400]


def appeears(man, fetch: bool = True) -> dict:
    tok = earthdata_token()
    if not tok:
        st = {"estado": "omitido", "motivo": "sin token"}
        man.note("APPEEARS", st)
        return st
    code, body = _api(f"{APPEEARS_API}/task/{APPEEARS_TASK}", tok)
    st = {"tarea": APPEEARS_TASK, "http_estado_tarea": code}
    if code != 200:
        st.update({"estado": "no accesible con el token de Earthdata",
                   "respuesta": body.decode("utf-8", "ignore")[:300],
                   "nota": "La API de AppEEARS pide su propio token (POST /login con usuario y contraseña); no se "
                           "usan contraseñas. El usuario debe descargar el pedido desde la web de AppEEARS."})
        man.note("APPEEARS", st)
        print("[AppEEARS]", json.dumps({k: v for k, v in st.items() if k != "respuesta"}, ensure_ascii=False))
        return st
    task = json.loads(body)
    st.update({"estado_tarea": task.get("status"), "nombre": task.get("task_name"),
               "creada": task.get("created"), "completada": task.get("completed")})
    if task.get("status") != "done":
        st["estado"] = f"pedido no terminado ({task.get('status')})"
        man.note("APPEEARS", st)
        return st
    code, body = _api(f"{APPEEARS_API}/bundle/{APPEEARS_TASK}", tok)
    if code != 200:
        st.update({"estado": "lista de archivos no accesible", "http_estado_bundle": code})
        man.note("APPEEARS", st)
        return st
    files = json.loads(body).get("files", [])
    want = [f for f in files if f["file_name"].endswith(".tif")
            and any(k in f["file_name"] for k in ("_NDVI_", "_EVI_", "pixel_reliability", "Npp_500m"))]
    st["archivos_en_pedido"] = len(files)
    st["archivos_tif_utiles"] = len(want)
    if fetch:
        ok = 0
        for f in want:
            d = DATA / "appeears" / Path(f["file_name"]).name
            if man.has(d):
                ok += 1
                continue
            u = f"{APPEEARS_API}/bundle/{APPEEARS_TASK}/{f['file_id']}"
            from ..earthdata import get_follow  # Bearer solo en el primer salto
            try:
                b = get_follow(u)
            except Exception as e:  # noqa: BLE001
                st.setdefault("errores", []).append(str(e)[:200])
                continue
            _save(d, b)
            man.add(d, u, save=False, dataset="AppEEARS", tarea=APPEEARS_TASK, cita=CITAS["MOD13A3"])
            ok += 1
        man.save()
        st["descargados"] = ok
    st["estado"] = "ok"
    man.note("APPEEARS", st)
    return st


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", nargs="*", default=["smap", "hansen", "appeears"])
    ap.add_argument("--hilos", type=int, default=12)
    ap.add_argument("--probar", action="store_true")
    a = ap.parse_args(argv)
    if a.probar:
        probe_smap()
        print("filas/columnas", smap_rows_cols())
        return
    man = manifest()
    if "appeears" in a.solo:
        print("[AppEEARS]", json.dumps(appeears(man), ensure_ascii=False)[:600], flush=True)
    if "hansen" in a.solo:
        print("[Hansen]", hansen(man), flush=True)
    if "smap" in a.solo:
        smap(man, a.hilos)


if __name__ == "__main__":
    main()
