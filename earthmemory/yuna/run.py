"""Caso Yuna: cuenca, presa de Hatillo, inundaciones observadas y prueba de disparadores.

    docker compose run --rm yuna                    (todo: descarga lo que falte, analiza, figuras, cuaderno, informe)
    docker compose run --rm yuna --sin-descarga     (solo con lo que ya está en data/)
    docker compose run --rm yuna --etapa analisis   (rehace análisis/figuras/informe con las series ya extraídas)

Escribe solo en data/yuna, results/yuna, figures/yuna, reports_nacional/CASO_YUNA.md, notebooks/08_caso_yuna.ipynb
y reports_nacional/notebooks_html/08_caso_yuna.html.
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd
from shapely.geometry import mapping, shape

from .common import DATA, RES, ensure_dirs, manifest


def _zonas_desde_geojson() -> dict:
    d = json.loads((RES / "cuencas_yuna.geojson").read_text(encoding="utf-8"))
    return {f["properties"]["zona"]: shape(f["geometry"]) for f in d["features"]}


def puntos_geoglows(rivs_meta: dict) -> dict:
    """Puntos SOBRE el cauce (HydroRIVERS) donde pedir el river_id de GEOGLOWS."""
    from . import cuencas
    rivs = cuencas.rivers()
    by = {r["HYRIV_ID"]: r for r in rivs}
    def mid(rid):
        g = by[rid]["geom"]
        p = g.interpolate(0.5, normalized=True)
        return (round(p.y, 5), round(p.x, 5))
    pts = {"yuna_hatillo": mid(rivs_meta["hatillo"]["hydrorivers_tramo"]),
           "camu_confluencia": mid(rivs_meta["camu"]["tramo_final"])}
    # Yuna principal cerca de Villa Riva: tramo de mayor área drenada a < 5 km del pueblo
    vr = cuencas._river_near(rivs, 19.176, -69.908, min_up=4000, radio=0.06)
    pts["yuna_villa_riva"] = mid(vr["HYRIV_ID"])
    # Yuna aguas abajo de la cortina y antes de la confluencia con el Camú (Cotuí)
    ct = cuencas._river_near(rivs, 19.07, -70.13, min_up=1200, radio=0.05)
    pts["yuna_cotui"] = mid(ct["HYRIV_ID"])
    meta = {k: {"lat": v[0], "lon": v[1]} for k, v in pts.items()}
    for k, rid in (("yuna_hatillo", rivs_meta["hatillo"]["hydrorivers_tramo"]), ("camu_confluencia", rivs_meta["camu"]["tramo_final"]),
                   ("yuna_villa_riva", vr["HYRIV_ID"]), ("yuna_cotui", ct["HYRIV_ID"])):
        meta[k].update({"HYRIV_ID": int(rid), "UPLAND_km2": float(by[rid]["UPLAND_SKM"]),
                        "DIS_AV_CMS_hydrorivers": float(by[rid]["DIS_AV_CMS"])})
    (RES / "geoglows_puntos.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return pts


def preparar(sin_descarga: bool) -> None:
    from . import cuencas, download, observacion, series
    ensure_dirs()
    t = time.time()
    if not sin_descarga and not (DATA / "derivados" / "imerg_zonas.parquet").exists():
        download.run()
    print("· cuencas (HydroBASINS lev10 + HydroRIVERS)", flush=True)
    out, geoms, rivs, _ = cuencas.delinear()
    cuencas.guardar(out, geoms, rivs)
    zonas = {k: geoms[k] for k in ("yuna", "alto_hatillo", "camu", "bajo_yuna")}
    if not sin_descarga and not (RES / "geoglows_ids.json").exists():
        print("· GEOGLOWS v2", flush=True)
        solo_geoglows()
    print("· JRC GSW: máscaras y series", flush=True)
    m = observacion.mascaras(zonas)
    np.savez_compressed(DATA / "derivados" / "mascaras_gsw.npz", embalse=m["embalse"], llanura=m["llanura"],
                        occ=np.nan_to_num(m["occ"], nan=-1).astype(np.float32), dem=m["dem"])
    g = series.gsw({"embalse": m["embalse"], "llanura": m["llanura"]})
    g.to_csv(RES / "gsw_mensual.csv")
    (RES / "gsw_mascaras.json").write_text(json.dumps(m["meta"], indent=1), encoding="utf-8")
    print("· GLDAS mensual", flush=True)
    series.gldas(zonas).to_csv(RES / "gldas_mensual_zonas.csv")
    cache = DATA / "derivados"
    print("· SMAP L4 diario", flush=True)
    if (cache / "smap_zonas.parquet").exists():
        sm = pd.read_parquet(cache / "smap_zonas.parquet")
    else:
        sm = series.smap(zonas)
        if sm is not None:
            sm.to_parquet(cache / "smap_zonas.parquet")
    print("· IMERG diario", flush=True)
    if (cache / "imerg_zonas.parquet").exists():
        im = pd.read_parquet(cache / "imerg_zonas.parquet")
    else:
        im = series.imerg(zonas)
        im.to_parquet(cache / "imerg_zonas.parquet")
    print("· CHIRPS diario (motor tendencias, si existe)", flush=True)
    ch = series.chirps(zonas)
    d = im
    for extra in (sm, ch):
        if extra is not None:
            d = d.join(extra, how="left")
    ids = json.loads((RES / "geoglows_ids.json").read_text()) if (RES / "geoglows_ids.json").exists() else {}
    q = series.geoglows(ids)
    if q is not None:
        d = d.join(q, how="left")
    d.index.name = "fecha"
    d.to_parquet(RES / "series_diarias_zonas.parquet")
    print(f"  series: {d.shape}, {time.time() - t:.0f} s", flush=True)


def solo_geoglows() -> None:
    from . import download
    out = json.loads((RES / "cuencas_resumen.json").read_text(encoding="utf-8"))
    ids = download.geoglows(manifest(), puntos_geoglows(out))
    (RES / "geoglows_ids.json").write_text(json.dumps(ids, indent=1), encoding="utf-8")


def bajar_mcdwd() -> None:
    """Días de MCDWD_L3 que hacen falta (eventos, referencia seca, episodios p99, meses GSW sin evento)."""
    from . import analisis, catalogo, mcdwd
    from .observacion import anomalias
    cat = catalogo.construir()
    d, g, w = analisis.cargar()
    v = analisis.variables(d, g)
    ep = pd.read_csv(RES / "presa_episodios_lluvia_fuerte.csv", parse_dates=["inicio", "fin"])
    lla = anomalias(w, "llanura")
    ev_meses = set()
    for r in cat[cat["usable_backtest"]].itertuples():
        ev_meses |= set(pd.date_range(pd.Timestamp(r.inicio).replace(day=1), pd.Timestamp(r.fin) + pd.offsets.MonthBegin(1), freq="MS"))
    sin_cat = [x.strftime("%Y-%m") for x in lla.index[lla["sobre_p90"]] if x not in ev_meses]
    dias = mcdwd.dias_necesarios(cat, v, ep, sin_cat)
    mcdwd.guardar_dias(dias)
    print(f"  MCDWD: {dias['fecha'].nunique()} días únicos", flush=True)
    prio = {"evento": 0, "referencia_seca": 1, "gsw_sin_evento": 2, "episodio_p99": 3}
    orden = dias.assign(p=dias["motivo"].map(prio)).sort_values(["p", "fecha"])
    est = mcdwd.bajar(list(orden["fecha"]))
    mcdwd.resumen_json(est)


def analizar() -> None:
    from . import analisis, catalogo, figuras, notebook, report, web
    cat = catalogo.construir()
    res = analisis.run(cat)
    figuras.run(res)
    web.run(res)
    report.run(res)
    notebook.build_and_run()


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sin-descarga", action="store_true")
    ap.add_argument("--etapa", choices=["todo", "preparar", "geoglows", "mcdwd", "analisis"], default="todo")
    a = ap.parse_args(argv)
    if a.etapa == "geoglows":
        solo_geoglows()
        return
    if a.etapa == "mcdwd":
        bajar_mcdwd()
        return
    if a.etapa in ("todo", "preparar"):
        preparar(a.sin_descarga)
    if a.etapa == "todo" and not a.sin_descarga:
        bajar_mcdwd()
    if a.etapa in ("todo", "analisis"):
        analizar()


if __name__ == "__main__":
    main()
