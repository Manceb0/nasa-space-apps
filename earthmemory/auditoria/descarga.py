"""Descargas crudas de la auditoría (solo lo que falta) → data/auditoria/ + MANIFEST.json.

Qué se baja y por qué:
- NOAA GHCN-Daily: lista de estaciones y CSV por estación de las 5 estaciones con prefijo "DR".
  Cita: Menne et al. (2012) JTECH 29:897-910, doi:10.1175/JTECH-D-11-00103.1; conjunto doi:10.7289/V5D21VHZ.
- NOAA GSOD (resumen diario derivado de ISD) 2001-2024 de las estaciones sinópticas OMM de RD que lista
  WMO OSCAR/Surface (13). Amplía la red: GHCN-D solo trae 4 estaciones dominicanas con datos 2001-2024.
- CHIRPS v2.0, diagnóstico "monthly_station_data/AAAA.MM.csv" (estaciones que entraron a la mezcla de cada
  mes). Se guarda SOLO el extracto dentro de la caja de RD; el SHA-256 del manifiesto es del archivo completo
  tal como se descargó (y se guarda también el del extracto). Sirve para saber qué estaciones son circulares.
- NOAA CPC ONI (fases ENSO).
Licencias: datos de NOAA/NCEI y NWS/CPC = dominio público (obra del gobierno de EE. UU.); CHIRPS = CC0.
Nunca se usa ni se imprime el token de Earthdata aquí (no hace falta: todo es público).
"""

from __future__ import annotations

import hashlib
import io
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

DATA = Path("data/auditoria")
UA = "EarthMemory-auditoria/1.0 (NASA Space Apps 2026; research use)"
BBOX = (-72.1, 17.3, -68.2, 20.2)  # lon0, lat0, lon1, lat1

GHCN_ACCESS = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{id}.csv"
GHCN_STATIONS = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"
GSOD = "https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/{y}/{id}.csv"
CHIRPS_ST = "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/diagnostics/monthly_station_data/{y}.{m:02d}.csv"
ONI = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
OSCAR = "https://oscar.wmo.int/surface/rest/api/search/station?territoryName=DOM"

# Estaciones OMM de RD según WMO OSCAR/Surface (consulta del 2026-11-14, ver OSCAR arriba).
WMO_DOM = {"78451": "Monte Cristi", "78458": "Puerto Plata", "78460": "Santiago", "78464": "Cabrera",
           "78466": "Arroyo Barril", "78467": "Sabana de la Mar", "78473": "Bayaguana", "78479": "Punta Cana",
           "78480": "Jimaní", "78482": "Barahona", "78485": "Las Américas", "78486": "Santo Domingo",
           "78488": "La Romana"}
GHCN_DR = ["DRM00078458", "DRM00078479", "DRM00078482", "DRM00078486", "DRW00011650"]

LIC_NOAA = "Dominio público (obra del gobierno de EE. UU.; NOAA/NCEI)"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def get(url: str, retries: int = 3, timeout: int = 45) -> bytes | None:
    """None si el servidor dice 404 (el archivo no existe); excepción si falla de otro modo."""
    last = None
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
        time.sleep(1.5 * 2 ** k)
    raise RuntimeError(f"{url}: {last}")


class Manifest:
    def __init__(self, path: Path = DATA / "MANIFEST.json"):
        self.path = path
        self.d = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"archivos": {}, "faltantes": {}}

    def has(self, rel: str) -> bool:
        r = self.d["archivos"].get(rel)
        p = self.path.parent / rel
        return bool(r) and p.exists() and sha(p.read_bytes()) == r["sha256_guardado"]

    def add(self, rel: str, url: str, body_full: bytes, body_saved: bytes, **extra):
        self.d["archivos"][rel] = {"url": url, "accedido_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                   "sha256": sha(body_full), "bytes": len(body_full),
                                   "sha256_guardado": sha(body_saved), "bytes_guardado": len(body_saved), **extra}

    def save(self):
        self.d["archivos"] = dict(sorted(self.d["archivos"].items()))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _save(man: Manifest, rel: str, url: str, body: bytes, saved: bytes | None = None, **extra):
    p = DATA / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    saved = body if saved is None else saved
    p.write_bytes(saved)
    man.add(rel, url, body, saved, **extra)


def chirps_extract(body: bytes) -> bytes:
    lines = body.decode("utf-8", "replace").splitlines()
    out = [lines[0]] if lines else []
    for ln in lines[1:]:
        f = ln.split(",")
        try:
            la, lo = float(f[2]), float(f[3])
        except (ValueError, IndexError):
            continue
        if BBOX[1] <= la <= BBOX[3] and BBOX[0] <= lo <= BBOX[2]:
            out.append(ln)
    return ("\n".join(out) + "\n").encode("utf-8")


def run(y0: int = 2001, y1: int = 2024, workers: int = 6) -> dict:
    man = Manifest()
    jobs = []
    # 1) GHCN-D
    for sid in GHCN_DR:
        jobs.append((f"ghcnd/{sid}.csv", GHCN_ACCESS.format(id=sid), None,
                     {"dataset": "NOAA GHCN-Daily v3", "licencia": LIC_NOAA,
                      "cita": "Menne et al. 2012, doi:10.1175/JTECH-D-11-00103.1; doi:10.7289/V5D21VHZ"}))
    jobs.append(("ghcnd/ghcnd-stations_DR.txt", GHCN_STATIONS,
                 lambda b: ("\n".join(l for l in b.decode("latin-1").splitlines() if l.startswith("DR")) + "\n").encode(),
                 {"dataset": "GHCN-Daily lista de estaciones (extracto: prefijo DR)", "licencia": LIC_NOAA}))
    # 2) GSOD por estación y año
    for w in WMO_DOM:
        for y in range(y0, y1 + 1):
            jobs.append((f"gsod/{w}/{y}.csv", GSOD.format(y=y, id=f"{w}099999"), None,
                         {"dataset": "NOAA GSOD (ISD)", "licencia": LIC_NOAA, "estacion_omm": w}))
    # 3) Estaciones usadas por CHIRPS v2 (extracto RD). Si el servidor del CHC no responde, se salta y se anota.
    try:
        chc_ok = get(CHIRPS_ST.format(y=2001, m=1), retries=1, timeout=20) is not None
    except Exception as e:  # noqa: BLE001
        chc_ok = False
        man.d["chc_inalcanzable"] = {"utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "error": str(e)[:200]}
    for y in (range(y0, y1 + 1) if chc_ok else []):
        for m in range(1, 13):
            jobs.append((f"chirps_estaciones/{y}.{m:02d}_RD.csv", CHIRPS_ST.format(y=y, m=m), chirps_extract,
                         {"dataset": "CHIRPS v2.0 diagnostics/monthly_station_data (extracto caja RD)",
                          "licencia": "CC0 (Climate Hazards Center, UCSB)"}))
    # 4) ONI y OSCAR
    jobs.append(("enso/oni.ascii.txt", ONI, None, {"dataset": "NOAA CPC ONI (ERSSTv5)", "licencia": "Dominio público (NWS/CPC)"}))
    jobs.append(("oscar/oscar_DOM.json", OSCAR, None, {"dataset": "WMO OSCAR/Surface estaciones DOM",
                                                       "licencia": "WMO OSCAR (metadatos públicos)"}))

    jobs = jobs[-2:] + jobs[:-2]  # ONI y OSCAR primero (pequeños)
    todo = [j for j in jobs if not man.has(j[0]) and j[0] not in man.d.get("faltantes", {})]
    print(f"[descarga] {len(jobs)} archivos en la lista; faltan {len(todo)}", flush=True)

    def work(j):
        rel, url, filt, extra = j
        try:
            b = get(url)
        except Exception as e:  # noqa: BLE001
            return rel, url, None, None, extra, str(e)
        if b is None:
            return rel, url, None, None, extra, "HTTP 404"
        return rel, url, b, (filt(b) if filt else None), extra, None

    errors = {}
    with ThreadPoolExecutor(workers) as ex:
        from concurrent.futures import as_completed
        futs = [ex.submit(work, j) for j in todo]
        for k, fu in enumerate(as_completed(futs)):
            rel, url, b, saved, extra, err = fu.result()
            if err:
                if err == "HTTP 404":
                    man.d.setdefault("faltantes", {})[rel] = {"url": url, "motivo": err}
                else:
                    errors[rel] = err
                continue
            _save(man, rel, url, b, saved, **extra)
            if k % 10 == 0:
                man.save()
                print(f"[descarga] {k + 1}/{len(todo)}", flush=True)
    man.d["errores_ultima_corrida"] = errors
    # extractos guardados en una corrida interrumpida antes de registrarse: se registran con el SHA del extracto
    for p in sorted((DATA / "chirps_estaciones").glob("*_RD.csv")):
        rel = p.relative_to(DATA).as_posix()
        if rel not in man.d["archivos"]:
            y, m = p.stem.split("_")[0].split(".")
            b = p.read_bytes()
            man.d["archivos"][rel] = {"url": CHIRPS_ST.format(y=int(y), m=int(m)), "sha256": None, "bytes": None,
                                      "sha256_guardado": sha(b), "bytes_guardado": len(b),
                                      "nota": "descarga interrumpida antes de registrar el SHA del archivo completo; "
                                              "se registra el del extracto guardado",
                                      "dataset": "CHIRPS v2.0 diagnostics/monthly_station_data (extracto caja RD)",
                                      "licencia": "CC0 (Climate Hazards Center, UCSB)"}
    man.save()
    print(f"[descarga] listo; errores {len(errors)}; 404 acumulados {len(man.d.get('faltantes', {}))}", flush=True)
    return {"errores": errors, "faltantes": man.d.get("faltantes", {})}


if __name__ == "__main__":
    run()
