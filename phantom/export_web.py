"""Exporta a JSON estático todo lo que muestra la herramienta web. Nada se inventa aquí:
cada número sale de phantom.trends / phantom.drought / los resultados del pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import appeears, drought, giovanni, modis_series, stats, trends

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

MODIS_META = {
    "modis_ndvi": {
        "nombre": "Verdor de la vegetación",
        "pregunta": "¿el bosque está más o menos verde?",
        "definicion": "NDVI: compara la luz roja y la infrarroja que refleja la vegetación. Más alto = hojas más verdes y densas. Lo mide el satélite Terra (MODIS) cada 16 días a 250 m.",
        "unidad": "NDVI",
        "unidad_larga": "índice NDVI (de −1 a 1; la vegetación sana suele estar entre 0,3 y 0,9)",
        "fuente": "NASA LP DAAC MOD13Q1 v6.1 (Terra MODIS), 250 m, 16 días",
        "producto": "MOD13Q1.061 _250m_16_days_NDVI (calidad: pixel_reliability 0–1)",
        "tipo": "observación satelital",
        "aviso": "Son puntos de monte seco revisados en imagen satelital (3 en Montecristi, 1 en Jaragua), no la región completa.",
    },
    "modis_lst": {
        "nombre": "Temperatura de la superficie",
        "pregunta": "¿se está calentando el suelo y el dosel?",
        "definicion": "La temperatura de la superficie de día (hojas, suelo) medida en el infrarrojo térmico por Terra (MODIS), cada 8 días a 1 km. No es la temperatura del aire.",
        "unidad": "°C",
        "unidad_larga": "grados Celsius de la superficie",
        "fuente": "NASA LP DAAC MOD11A2 v6.1 (Terra MODIS), 1 km, 8 días",
        "producto": "MOD11A2.061 LST_Day_1km (calidad: QC_Day bueno, o error ≤ 2 K)",
        "tipo": "observación satelital",
        "aviso": "Solo cuenta días despejados. Desde 2020 el satélite Terra pasa más temprano, lo que tiende a dar superficies algo más frías en los últimos años (NASA). Son puntos, no la región completa.",
    },
    "modis_gpp": {
        "nombre": "Productividad estimada",
        "pregunta": "¿las plantas fijan más o menos carbono?",
        "definicion": "GPP: cuánto carbono fijan las plantas por fotosíntesis. MODIS lo calcula con un modelo que usa el verdor y el clima; no es una medición directa.",
        "unidad": "gC/m²/día",
        "unidad_larga": "gramos de carbono por metro cuadrado por día",
        "fuente": "NASA LP DAAC MOD17A2HGF v6.1 (Terra MODIS), 500 m, 8 días",
        "producto": "MOD17A2HGF.061 Gpp_500m (acumulado de 8 días convertido a tasa diaria)",
        "tipo": "modelo con datos satelitales",
        "aviso": "GPP usa en parte el mismo verdor (FPAR) y meteorología de reanálisis: no confirma al NDVI de forma independiente. Son puntos, no la región completa.",
    },
}

GIOVANNI_VARS = list(VARIABLES)
VARIABLES = {**VARIABLES, **MODIS_META}

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


def _region_of(pid: str) -> str | None:
    # AppEEARS quita los guiones bajos de los ID: "montecristimontesecoa"
    if pid.startswith("montecristi") or pid.startswith("sierra"):
        return "noroeste"
    if pid.startswith("jaragua"):
        return "jaragua"
    return None


def _modis_series(root: Path) -> list[tuple]:
    """(clave, variable, zona, serie mensual, pasaporte, meses mínimos por año) para NDVI, LST y GPP."""
    adir = root / "data" / "appeears"
    data, _ = appeears.load_point_sample(adir)
    files = appeears.find_product_files(adir)
    out = []
    for var, spec in modis_series.MODIS_VARS.items():
        df = data.get(spec["producto"])
        if df is None:
            continue
        monthly = modis_series.monthly_point(df, spec["col"], spec["escala"])
        coords = df.groupby("id")[["lat", "lon"]].first()
        for reg in REGIONS:
            ids = [c for c in monthly.columns if _region_of(c) == reg]
            if not ids:
                continue
            s = modis_series.region_series(monthly, ids).rename(var)
            cov = modis_series.coverage(monthly, ids)
            passport = {
                "fuente": VARIABLES[var]["fuente"],
                "producto": VARIABLES[var]["producto"],
                "herramienta": "NASA AppEEARS, Point Sample (pedido 9490ce7b-3268-46aa-84a6-bbe8a3b648ed)",
                "caja_pedida": None, "caja_datos": None,
                "puntos": [[float(coords.loc[i, "lat"]), float(coords.loc[i, "lon"]), i] for i in ids],
                "url_reproducir": None,
                "archivo": f"data/appeears/{files[spec['producto']].name}",
                "reconstruido": False,
                "verificacion": (f"CSV de AppEEARS sin cambios; solo observaciones que pasan el filtro de calidad. "
                                 f"Meses con dato: {cov['meses_con_dato']} de {cov['meses_totales']}."),
                "metodo": ("Media mensual de observaciones válidas por punto; la zona es la media de las anomalías "
                           "de sus puntos. Anomalía anual con al menos 9 meses. Theil-Sen con IC 95 %; "
                           "Mann-Kendall corregido por empates y autocorrelación AR(1); BH sobre todas las series."),
                "codigo": "phantom/modis_series.py · phantom/trends.py · phantom/stats.py",
                "descargado": "2026-11-14",
                "cobertura": cov,
            }
            out.append((f"{var}_{reg}", var, reg, s, passport, 9))
    return out


def export(root: Path, results: Path, out: Path) -> dict:
    series = giovanni.load_folder(root / "data" / "giovanni")
    entries = []
    for var in GIOVANNI_VARS:
        for reg in REGIONS:
            gs = series[f"{var}_{reg}"]
            passport = {
                "fuente": VARIABLES[var]["fuente"],
                "producto": VARIABLES[var]["producto"],
                "herramienta": "NASA Giovanni, Time Series Area-Averaged",
                "caja_pedida": _box(gs.meta.get("User Bounding Box")),
                "caja_datos": _box(gs.meta.get("Data Bounding Box")),
                "puntos": None,
                "url_reproducir": gs.meta.get("URL to Reproduce Results"),
                "archivo": f"data/giovanni/{gs.path.name}",
                "reconstruido": gs.reconstructed,
                "verificacion": ("Reconstruido del CSV de Giovanni; verificado valor por valor contra el original "
                                 "regenerado (idéntico redondeado a 4 decimales)") if gs.reconstructed else
                                "CSV descargado de Giovanni sin cambios",
                "metodo": ("Anomalía = valor − media del mismo mes (2001–2024). Media anual de anomalías "
                           "(solo años con 12 meses). Pendiente Theil-Sen con IC 95 %; prueba de Mann-Kendall "
                           "con corrección por empates y autocorrelación AR(1); q de Benjamini-Hochberg sobre todas las series."),
                "codigo": "phantom/trends.py · phantom/stats.py",
                "descargado": "2026-11-14",
            }
            entries.append((f"{var}_{reg}", var, reg, gs.values, passport, 12))
    entries += _modis_series(root)

    present_vars = {e[1] for e in entries}
    index = {"generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
             "variables": {k: v for k, v in VARIABLES.items() if k in present_vars},
             "regiones": REGIONS, "series": []}
    analyses = [(e, trends.analyze(e[3], e[5])) for e in entries]

    # Corrección por comparaciones múltiples sobre todas las pruebas de serie completa
    q = stats.benjamini_hochberg([a["completa"].get("p_mk") for _, a in analyses])
    for (_, a), qq in zip(analyses, q):
        a["completa"]["q_bh"] = qq

    for (key, var, reg, s, passport, _), a in analyses:
        doc = {
            "id": key, "variable": var, "region": reg,
            "meses": [d.strftime("%Y-%m") for d in s.index],
            "valores": [None if pd.isna(v) else float(v) for v in s],
            **a,
            "pasaporte": passport,
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
    aud = results / "auditorias.json"
    if estado.get("estado") == "procesado" and aud.exists():
        phantom["auditorias"] = json.loads(aud.read_text(encoding="utf-8"))
    _write(out / "phantom.json", phantom)
    pts = export_points(root, results, out)
    if pts:
        index["puntos"] = True
    _write(out / "index.json", index)
    return index


POINT_NAMES = {
    "montecristimontesecoa": "Montecristi A", "montecristimontesecob": "Montecristi B",
    "sierramontecristi": "Sierra de Montecristi", "jaraguacomparacionseco": "Jaragua",
    "cordilleracomparacionhumedo": "Cordillera Central",
}


def export_points(root: Path, results: Path, out: Path) -> dict | None:
    """Por punto: tendencias de NDVI, LST y GPP (mismo método que el detective), anomalías mensuales
    estandarizadas para el mapa de calor y las series z de recuperación para la doble línea."""
    adir = root / "data" / "appeears"
    data, _ = appeears.load_point_sample(adir)
    if not data:
        return None
    lc = appeears.landcover_stability(data["MCD12Q1"]) if "MCD12Q1" in data else pd.DataFrame()
    first = next(iter(data.values()))
    coords = first.groupby("id")[["lat", "lon"]].first()
    meses = modis_series.MONTHS
    heat: dict = {"meses": [d.strftime("%Y-%m") for d in meses], "series": {}}
    trends_out: dict = {}
    tests = []
    for var, spec in modis_series.MODIS_VARS.items():
        df = data.get(spec["producto"])
        if df is None:
            continue
        monthly = modis_series.monthly_point(df, spec["col"], spec["escala"])
        g = monthly.groupby(monthly.index.month)
        z = (monthly - g.transform("mean")) / g.transform("std")
        heat["series"][var] = {pid: [None if pd.isna(v) else round(float(v), 2) for v in z[pid]] for pid in z.columns}
        for pid in monthly.columns:
            a = trends.analyze(monthly[pid], 9)["completa"]
            trends_out.setdefault(pid, {})[var] = a
            tests.append((pid, var, a.get("p_mk")))
    q = stats.benjamini_hochberg([t[2] for t in tests])
    for (pid, var, _), qq in zip(tests, q):
        trends_out[pid][var]["q_bh"] = qq
    points = []
    for pid in coords.index:
        row = lc[lc["id"] == pid].to_dict("records")[0] if len(lc) else {}
        points.append({
            "id": pid, "nombre": POINT_NAMES.get(pid.replace("_", ""), pid),
            "lat": float(coords.loc[pid, "lat"]), "lon": float(coords.loc[pid, "lon"]),
            "region": _region_of(pid), "cobertura": row.get("clases_2001_2021"), "estable": row.get("estable"),
            "tendencias": trends_out.get(pid, {}),
        })
    zfile = results / "zseries.json"
    doc = {"puntos": points, "calor": heat, "n_pruebas_mapa": len(tests),
           "z": json.loads(zfile.read_text(encoding="utf-8")) if zfile.exists() else {}}
    _write(out / "puntos.json", doc)
    return doc
