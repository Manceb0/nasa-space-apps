"""JSON para las pantallas (results/yuna/web/) + CONTRATO.md. Solo lee lo que dejó el análisis."""

from __future__ import annotations

import datetime
import json

import numpy as np
import pandas as pd
from shapely.geometry import mapping, shape

from .common import RES, WEB

CLASES = {
    "imerg": "RECUPERACIÓN SATELITAL", "chirps": "RECUPERACIÓN SATELITAL + estaciones",
    "smap": "MODELO CON ASIMILACIÓN", "gldas": "MODELO FORZADO", "geoglows": "SIMULACIÓN HIDROLÓGICA",
    "gsw": "OBSERVACIÓN", "catalogo": "REGISTRO DOCUMENTAL (prensa, gobierno, IFRC, CEPAL)",
}


def _clean(x):
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), 3)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (pd.Timestamp, datetime.date)):
        return x.strftime("%Y-%m-%d")
    return x


def _dump(name, obj):
    (WEB / name).write_text(json.dumps(_clean(obj), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def run(res: dict) -> None:
    WEB.mkdir(parents=True, exist_ok=True)
    cu = json.loads((RES / "cuencas_yuna.geojson").read_text(encoding="utf-8"))
    for f in cu["features"]:
        f["geometry"] = mapping(shape(f["geometry"]).simplify(0.004, preserve_topology=True))
    _dump("cuencas.geojson", cu)
    rv = json.loads((RES / "rios_hydrorivers.geojson").read_text(encoding="utf-8"))
    rv["features"] = [{**f, "geometry": mapping(shape(f["geometry"]).simplify(0.002))}
                      for f in rv["features"] if f["properties"]["UPLAND_SKM"] >= 300]
    _dump("rios.geojson", rv)
    _dump("que_drena_donde.json", pd.read_csv(RES / "que_drena_donde.csv").to_dict("records"))
    cat = res["cat"].copy()
    cat["inicio"] = cat["inicio"].astype(str); cat["fin"] = cat["fin"].astype(str)
    cat["fuentes_url"] = cat["fuentes_url"].str.split(" | ")
    _dump("catalogo.json", {"clase": CLASES["catalogo"], "eventos": cat.to_dict("records")})
    # series por evento (−60 a +15 días)
    d, v = res["d"], res["v"]
    out = []
    for r in res["paneles"].itertuples():
        a, b = pd.Timestamp(r.inicio), pd.Timestamp(r.fin)
        if a.year > 2024:
            out.append({"id": r.id, "nota": "fuera del registro diario local (2001-2024)"})
            continue
        sl = slice(a - pd.Timedelta(days=60), b + pd.Timedelta(days=15))
        s = {"fecha": [x.strftime("%Y-%m-%d") for x in d.loc[sl].index],
             "imerg_media_yuna_mm": d.loc[sl, "imerg_media_yuna"].tolist(),
             "imerg_max_celda_yuna_mm": d.loc[sl, "imerg_max_yuna"].tolist(),
             "imerg_ant30_yuna_mm": v.loc[sl, "ant30_yuna"].tolist()}
        for z in ("alto_hatillo", "camu", "bajo_yuna"):
            if f"smap_raiz_{z}" in d:
                s[f"smap_raiz_{z}_m3m3"] = d.loc[sl, f"smap_raiz_{z}"].tolist()
        for c in [c for c in d.columns if c.startswith("q_")]:
            s[f"{c}_m3s"] = d.loc[sl, c].tolist()
        if "chirps_media_yuna" in d:
            s["chirps_media_yuna_mm"] = d.loc[sl, "chirps_media_yuna"].tolist()
        out.append({"id": r.id, "inicio": str(r.inicio), "fin": str(r.fin), "series": s,
                    "resumen": {k: v_ for k, v_ in r._asdict().items() if k not in ("Index",)}})
    _dump("series_eventos.json", {"clases": CLASES, "eventos": out})
    w = res["w"]
    _dump("hatillo.json", {"ficha": json.loads((RES / "hatillo_ficha.json").read_text(encoding="utf-8")),
                           "gsw_mensual": {"clase": CLASES["gsw"], "fecha": [x.strftime("%Y-%m") for x in w.index],
                                           "embalse_agua_km2": w["gsw_agua_km2_embalse"].tolist(),
                                           "embalse_frac_validos": w["gsw_validos_embalse"].tolist(),
                                           "llanura_agua_km2": w["gsw_agua_km2_llanura"].tolist(),
                                           "llanura_frac_validos": w["gsw_validos_llanura"].tolist()}})
    bt = res["backtest"].copy()
    _dump("backtest.json", {"tabla": bt.to_dict("records"), "info": res["info"],
                            "presa": {k: v_ for k, v_ in res["presa"]["auc"].items()},
                            "presa_mensual": res["presa"]["mensual"].to_dict("records") if "mensual" in res["presa"] else []})
    (WEB / "CONTRATO.md").write_text(CONTRATO, encoding="utf-8", newline="\n")


CONTRATO = """# Contrato de datos · caso Yuna (results/yuna/web/)

Generado por `docker compose run --rm yuna`. Todo es JSON UTF-8 (GeoJSON en WGS84 lon/lat). Los valores
faltantes son `null`. Cada variable lleva su CLASE; la pantalla debe mostrarla junto al dato:

| clase | productos |
|---|---|
| OBSERVACIÓN | JRC Global Surface Water mensual (Landsat 30 m; nubes = sin dato) |
| RECUPERACIÓN SATELITAL | IMERG Final V07 (calibrado con pluviómetros GPCC), CHIRPS v2 (+ estaciones) |
| MODELO CON ASIMILACIÓN | SMAP L4 (Catchment + Tb SMAP; su lluvia se ajusta a IMERG: no es independiente de IMERG) |
| MODELO FORZADO | GLDAS-2.1 Noah (GDAS + GPCP; sin asimilación de suelo) |
| SIMULACIÓN HIDROLÓGICA | GEOGLOWS v2 retrospectivo (forzado con ERA5; no son aforos; sin operación de Hatillo) |
| REGISTRO DOCUMENTAL | catálogo de eventos (prensa, gobierno, IFRC, CEPAL), cada evento con URL |

## Archivos

- `cuencas.geojson` — FeatureCollection; `properties.zona` ∈ {`yuna`, `alto_hatillo`, `camu`, `bajo_yuna`,
  `Yaque del Norte`, `Yaque del Sur`, `Ozama`}, `properties.area_km2`. Simplificado (0.004°). Fuente: HydroBASINS v1c nivel 10.
  `alto_hatillo` + `camu` + `bajo_yuna` = `yuna` (disjuntas).
- `rios.geojson` — tramos HydroRIVERS con ≥ 300 km² drenados: `HYRIV_ID`, `UPLAND_SKM`, `ORD_STRA`, `DIS_AV_CMS`
  (caudal medio MODELADO de HydroRIVERS).
- `que_drena_donde.json` — lista de puntos/celdas: `punto`, `lat`, `lon`, `celda_grados` (null = punto),
  `frac_<cuenca>` (fracción del rectángulo de la celda, o 0/1 para un punto), `salida_cuenca`.
- `catalogo.json` — `{clase, eventos:[{id, inicio, fin, precision, nombre, zona, lugares, impacto, confianza,
  n_fuentes, n_fuentes_leidas, fuentes_url:[...], hatillo_menciones, usable_backtest, motivo_exclusion}]}`.
  `zona = hatillo_operacion` son marcadores de operación de la presa, no inundaciones.
- `series_eventos.json` — `{clases, eventos:[{id, inicio, fin, series:{fecha:[...], imerg_media_yuna_mm,
  imerg_max_celda_yuna_mm, imerg_ant30_yuna_mm, smap_raiz_<zona>_m3m3, q_<punto>_m3s, chirps_media_yuna_mm},
  resumen:{...fila de results/yuna/paneles_eventos.csv...}}]}`; ventana −60 a +15 días. `q_yuna_villa_riva`,
  `q_yuna_cotui`, `q_camu_confluencia`, `q_yuna_hatillo` son GEOGLOWS (simulación) **pero quedaron en arroyos
  laterales, no en el cauce del Yuna: NO mostrarlos como caudal del Yuna** (ver CASO_YUNA.md §5).
- `hatillo.json` — `ficha` (datos publicados, con fuentes y conflictos: capacidad 710 / 441,6 / ~400 / 374,88 hm³ según
  definición y fuente) y `gsw_mensual` (área de agua del embalse y de la llanura, km², con fracción de píxeles válidos;
  usar solo meses con fracción válida ≥ 0.5 en el embalse y ≥ 0.3 en la llanura).
- `backtest.json` — `tabla` (una fila por disparador y periodo: POD, FAR, CSI con `*_ic95`, n de eventos,
  episodios), `info` (umbrales calibrados), `presa` (AUC por zona) y `presa_mensual` (ρ por estado del embalse).

## Reglas de lectura
- No decir «Hatillo regula/controla las crecidas»; la presa opera en «vertido libre» según INDRHI (2021).
- No decir «predice» ni «alerta temprana»: es evidencia retrospectiva con n pequeño.
- FAR es cota superior (el catálogo de prensa es incompleto).
"""
