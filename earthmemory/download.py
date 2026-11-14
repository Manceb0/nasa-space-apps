"""Descarga (con caché) de todo lo que usa Earth Memory para un país.

    python -m earthmemory.download --pais DOM --anio0 2001 --anio1 2024 [--sin-diario]

Orden: límites geoBoundaries ADM1 (y Natural Earth para vecinos) → IMERG mensual → GLDAS mensual →
IMERG media hora del evento → IMERG diario (lo más largo: ~8 800 recortes). Cada ruta que falla queda
anotada con el error exacto en MANIFEST.json["rutas"] y la corrida sigue con lo que sí funciona.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from . import boundaries, earthdata, power, region


def country_bbox(units, margin: float = 0.05) -> tuple:
    return tuple(round(v, 4) for v in boundaries.bounds(units, margin))


def run(args) -> dict:
    ddir = Path(args.datos)
    man = power.Manifest(ddir / "MANIFEST.json")
    adm1_p, adm1_meta = boundaries.ensure_adm(ddir, args.pais, "ADM1", man)
    region.ensure_boundaries(ddir, args.pais, man)  # Natural Earth: vecinos (p. ej. Haití)
    units = boundaries.load_units(adm1_p)
    bbox = tuple(args.bbox) if args.bbox else country_bbox(units)
    man.note("rutas", "caja_lon0_lat0_lon1_lat1", list(bbox))
    src = earthdata.token_source()
    man.note("rutas", "credencial", "token Bearer de Earthdata leído de un archivo/variable (no se guarda)"
             if src else "SIN TOKEN: no se pueden descargar IMERG/GLDAS")
    out = {"bbox": bbox, "adm1": adm1_meta.get("boundaryID")}
    elev = ddir / "gldas" / "GLDASp5_elevation_025d.nc4"
    if not man.verify(elev):
        try:
            body = power.http_get(earthdata.GLDAS_ELEV_URL, pause=0.5)
            elev.parent.mkdir(parents=True, exist_ok=True)
            elev.write_bytes(body)
            man.add(elev, earthdata.GLDAS_ELEV_URL, fuente="GLDAS: elevación de la rejilla 0.25° (constante del modelo)")
        except RuntimeError as e:
            man.note("rutas", "GLDAS_ELEV", {"estado": "falló", "error": str(e)})
    if not src:
        return out

    g = ddir / "grace" / Path(earthdata.GRACE_URL).name
    if not man.verify(g):
        try:
            print("[GRACE] mascons JPL RL06.3 (archivo global, ~46 MB)…", flush=True)
            body = earthdata.get_follow(earthdata.GRACE_URL)
            if not body.startswith(earthdata.HDF5_MAGIC):
                raise earthdata.EarthdataError(f"{earthdata.GRACE_URL} -> no es NetCDF4/HDF5: {body[:80]!r}")
            g.parent.mkdir(parents=True, exist_ok=True)
            g.write_bytes(body)
            man.add(g, earthdata.GRACE_URL, dataset="GRACE_MASCON", doi=earthdata.GRACE_DOI,
                    nota="solo contexto nacional: resolución efectiva ~3° (~300 km)")
            man.note("rutas", "GRACE", {"estado": "ok", "ruta": "HTTPS PO.DAAC (Bearer + URL firmada)", "pedidos": 1, "n_errores": 0})
        except (earthdata.EarthdataError, OSError) as e:
            man.note("rutas", "GRACE", {"estado": "falló", "pedidos": 1, "n_errores": 1, "errores_muestra": [str(e)],
                                        "nota": "cloud OPeNDAP devolvió 404 para este granulo el 2026-11-14"})

    steps = [("IMERG_M", lambda: earthdata.imerg_monthly_jobs(ddir, bbox, args.anio0, args.anio1)),
             ("GLDAS_M", lambda: earthdata.gldas_monthly_jobs(ddir, bbox, args.anio0, args.anio1)),
             ("GLDAS_RAIN", lambda: earthdata.gldas_monthly_jobs(ddir, bbox, args.anio0, args.anio1,
                                                                 earthdata.GLDAS_RAIN_VARS, "GLDAS_NOAH025_M.2.1_Rainf"))]
    if args.evento:
        t = pd.Timestamp(args.evento)
        days = [(t + pd.Timedelta(days=k)).strftime("%Y-%m-%d") for k in (-1, 0, 1)]
        steps.append(("IMERG_HH", lambda: earthdata.imerg_hh_jobs(ddir, bbox, days)))
    if not args.sin_diario:
        steps.append(("IMERG_D", lambda: earthdata.imerg_daily_jobs(ddir, bbox, args.anio0, args.anio1)))
    for key, mk in steps:
        print(f"[{key}] catálogo…", flush=True)
        try:
            jobs = mk()
        except earthdata.EarthdataError as e:
            man.note("rutas", key, {"estado": "falló el catálogo", "error": str(e)})
            print(f"  ERROR catálogo {key}: {e}", flush=True)
            continue
        fb = earthdata.imerg_fallback(key, bbox) if key.startswith("IMERG") else None
        res = earthdata.fetch_many(jobs, man, workers=args.hilos, fallback=fb)
        estado = "ok" if not res["errores"] else ("parcial" if res["descargados_ahora"] + res["ya_en_cache"] else "falló")
        man.note("rutas", key, {"estado": estado, "coleccion": earthdata.DATASETS[key]["nombre"],
                                "doi": earthdata.DATASETS[key]["doi"], "pedidos": res["pedidos"],
                                "en_cache_antes": res["ya_en_cache"], "descargados": res["descargados_ahora"],
                                "n_errores": len(res["errores"]), "errores_muestra": res["errores"][:5]})
        print(f"  {key}: {json.dumps({k: v for k, v in res.items() if k != 'errores'})} errores={len(res['errores'])}",
              flush=True)
        out[key] = res
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pais", default="DOM")
    ap.add_argument("--bbox", nargs=4, type=float, default=None)
    ap.add_argument("--anio0", type=int, default=2001)
    ap.add_argument("--anio1", type=int, default=2024)
    ap.add_argument("--datos", default="data/nacional")
    ap.add_argument("--evento", default="2023-11-18")
    ap.add_argument("--hilos", type=int, default=12)
    ap.add_argument("--sin-diario", dest="sin_diario", action="store_true")
    run(ap.parse_args(argv))


if __name__ == "__main__":
    main()
