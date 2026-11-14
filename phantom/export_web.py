"""Exporta a JSON estático todo lo que muestra la herramienta web. Nada se inventa aquí:
cada número sale de phantom.trends / phantom.drought / los resultados del pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import drought, giovanni, stats, trends

VARIABLES = {
    "imerg_precip": {
        "nombre": "Lluvia",
        "pregunta": "¿llueve más o menos que antes?",
        "definicion": "Cuánta agua cae en un mes sobre la zona. La miden satélites de la misión GPM.",
        "unidad": "mm/mes",
        "unidad_larga": "milímetros de agua por mes",
        "fuente": "NASA GPM IMERG V07, Final Run, mensual, 0.1°",
        "producto": "GPM_3IMERGM_07_precipitation",
        "tipo": "observación satelital",
        "aviso": None,
    },
    "merra2_t2m": {
        "nombre": "Temperatura del aire",
        "pregunta": "¿hace más calor que antes?",
        "definicion": "La temperatura a 2 metros del suelo. Sale de MERRA-2, un modelo que combina miles de observaciones.",
        "unidad": "°C",
        "unidad_larga": "grados Celsius",
        "fuente": "NASA GMAO MERRA-2 (M2TMNXSLV v5.12.4), mensual, 0.5° × 0.625°",
        "producto": "M2TMNXSLV_5_12_4_T2M",
        "tipo": "modelo (reanálisis)",
        "aviso": "La celda de MERRA-2 mide unos 55 × 65 km y su centro queda fuera de la zona: es la temperatura de los alrededores, no de un punto exacto.",
    },
    "gldas_soilmoi0_10cm": {
        "nombre": "Humedad del suelo",
        "pregunta": "¿el suelo está más seco que antes?",
        "definicion": "El agua guardada en los primeros 10 cm de tierra. La estima el modelo GLDAS a partir de lluvia, sol y temperatura.",
        "unidad": "kg/m²",
        "unidad_larga": "kilos de agua por metro cuadrado (1 kg/m² = 1 mm de agua)",
        "fuente": "NASA GLDAS Noah 2.1, mensual, 0.25°",
        "producto": "GLDAS_NOAH025_M_2_1_SoilMoi0_10cm_inst",
        "tipo": "modelo",
        "aviso": "GLDAS usa la lluvia como dato de entrada: si coincide con la lluvia, no es una confirmación independiente.",
    },
    "gldas_rootmoist": {
        "nombre": "Agua para las raíces",
        "pregunta": "¿las plantas tienen menos agua disponible?",
        "definicion": "El agua en la capa de suelo donde viven las raíces. También la estima el modelo GLDAS.",
        "unidad": "kg/m²",
        "unidad_larga": "kilos de agua por metro cuadrado (1 kg/m² = 1 mm de agua)",
        "fuente": "NASA GLDAS Noah 2.1, mensual, 0.25°",
        "producto": "GLDAS_NOAH025_M_2_1_RootMoist_inst",
        "tipo": "modelo",
        "aviso": "GLDAS usa la lluvia como dato de entrada: si coincide con la lluvia, no es una confirmación independiente.",
    },
}

REGIONS = {
    "noroeste": {"nombre": "Montecristi", "zona": "Línea Noroeste",
                 "descripcion": "Lomas de bosque seco y matorral en el extremo noroeste, cerca de la frontera con Haití.",
                 "centro": [19.84, -71.47]},
    "jaragua": {"nombre": "Jaragua", "zona": "Suroeste",
                "descripcion": "Parque Nacional Jaragua: uno de los bosques secos más grandes del Caribe.",
                "centro": [17.74, -71.45]},
}


def _box(text: str | None):
    if not text:
        return None
    try:
        w, s, e, n = [float(x) for x in text.split(",")]
        return [w, s, e, n]
    except ValueError:
        return None


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 6)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.strftime("%Y-%m-%d")
    if o is pd.NaT:
        return None
    return o


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_clean(obj), ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")


def export(root: Path, results: Path, out: Path) -> dict:
    series = giovanni.load_folder(root / "data" / "giovanni")
    index = {"generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
             "variables": VARIABLES, "regiones": REGIONS, "series": []}
    analyses = {}
    for var in VARIABLES:
        for reg in REGIONS:
            key = f"{var}_{reg}"
            gs = series[key]
            a = trends.analyze(gs.values)
            analyses[key] = (gs, a)

    # Corrección por comparaciones múltiples sobre las 8 pruebas de serie completa
    keys = list(analyses)
    q = stats.benjamini_hochberg([analyses[k][1]["completa"].get("p_mk") for k in keys])
    for k, qq in zip(keys, q):
        analyses[k][1]["completa"]["q_bh"] = qq

    for key, (gs, a) in analyses.items():
        var, reg = key.rsplit("_", 1)
        s = gs.values
        doc = {
            "id": key, "variable": var, "region": reg,
            "meses": [d.strftime("%Y-%m") for d in s.index],
            "valores": [None if pd.isna(v) else float(v) for v in s],
            **a,
            "pasaporte": {
                "fuente": VARIABLES[var]["fuente"],
                "producto": VARIABLES[var]["producto"],
                "herramienta": "NASA Giovanni, Time Series Area-Averaged",
                "caja_pedida": _box(gs.meta.get("User Bounding Box")),
                "caja_datos": _box(gs.meta.get("Data Bounding Box")),
                "url_reproducir": gs.meta.get("URL to Reproduce Results"),
                "archivo": f"data/giovanni/{gs.path.name}",
                "reconstruido": gs.reconstructed,
                "verificacion": ("Reconstruido del CSV de Giovanni; verificado valor por valor contra el original "
                                 "regenerado (idéntico redondeado a 4 decimales)") if gs.reconstructed else
                                "CSV descargado de Giovanni sin cambios",
                "metodo": ("Anomalía = valor − media del mismo mes (2001–2024). Media anual de anomalías "
                           "(solo años con 12 meses). Pendiente Theil-Sen con IC 95 %; prueba de Mann-Kendall "
                           "con corrección por empates; q de Benjamini-Hochberg sobre las 8 series."),
                "codigo": "phantom/trends.py · phantom/stats.py",
                "descargado": "2026-11-14",
            },
        }
        _write(out / "series" / f"{key}.json", doc)
        index["series"].append({"id": key, "variable": var, "region": reg,
                                "veredicto": a["completa"]["veredicto"]})

    # Sequías (reales, IMERG SPI-3) y expedientes MODIS
    events = []
    for reg in REGIONS:
        p = series[f"imerg_precip_{reg}"].values
        s3 = drought.spi(p, 3)
        ev = drought.primary_events(p)
        events.append({"region": reg,
                       "spi3": {"meses": [d.strftime("%Y-%m") for d in s3.index],
                                "valores": [None if pd.isna(v) else float(v) for v in s3]},
                       "eventos": ev.to_dict("records")})
    estado = json.loads((results / "estado_modis.json").read_text(encoding="utf-8")) \
        if (results / "estado_modis.json").exists() else {"estado": "pendiente"}
    phantom = {"estado_modis": estado.get("estado"), "sequias": events, "eventos": [], "sensibilidad": [],
               "colisiones": None, "cobertura_suelo": estado.get("cobertura_suelo")}
    rec = results / "recuperacion_eventos.csv"
    if estado.get("estado") == "procesado" and rec.exists():
        r = pd.read_csv(rec)
        phantom["eventos"] = r.replace({np.nan: None}).to_dict("records")
        sens = results / "sensibilidad.csv"
        if sens.exists():
            phantom["sensibilidad"] = pd.read_csv(sens).replace({np.nan: None}).to_dict("records")
        if "colision_verde" in r.columns:
            g = r.drop_duplicates(["id", "evento_inicio"])
            phantom["colisiones"] = {"eventos_evaluados": int(len(g)),
                                     "ventanas_cortadas": int(g["ventana_cortada_por_siguiente_sequia"].sum()),
                                     "colisiones": int(g["colision_verde"].sum())}
    _write(out / "phantom.json", phantom)
    _write(out / "index.json", index)
    return index
