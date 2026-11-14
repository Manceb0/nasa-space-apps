"""Lectura de los resultados 'Point Sample' de AppEEARS, con calidad, escalas y unidades.

AppEEARS entrega un CSV por producto: '<tarea>-<PRODUCTO>-<versión>-results.csv', con columnas
ID, Category, Latitude, Longitude, Date y una columna por capa: '<PRODUCTO>_<versión>_<capa>'.
Normalmente los valores ya vienen escalados; aquí se detecta y se registra en vez de suponerlo.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

PRODUCTS = {
    "MOD13Q1": {"period_days": 16},
    "MOD11A2": {"period_days": 8},
    "MOD17A2HGF": {"period_days": 8},
    "MCD12Q1": {"period_days": 365},
}

# IGBP (LC_Type1) aceptadas como vegetación natural: bosques 1-5, matorral 6-7, sabanas 8-9.
NATURAL_CLASSES = set(range(1, 10))
LC_RELIABLE_UNTIL = 2021  # aviso de NASA sobre MCD12Q1 posterior a 2021


def find_product_files(folder: str | Path) -> dict[str, Path]:
    out = {}
    for p in Path(folder).rglob("*.csv"):
        m = re.search(r"(MOD13Q1|MOD11A2|MOD17A2HGF|MCD12Q1)-(\d{3})-results\.csv$", p.name)
        if m:
            out[m.group(1)] = p
    return out


def _layer_column(df: pd.DataFrame, layer: str) -> str:
    cands = [c for c in df.columns if c.endswith("_" + layer) and not c.endswith("_Description")]
    if not cands:
        raise KeyError(f"no encontré la columna de la capa {layer}; columnas: {list(df.columns)[:12]}...")
    return min(cands, key=len)


def _base(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "id": df["ID"].astype(str),
        "fecha": pd.to_datetime(df["Date"]),
    })
    out["categoria"] = df["Category"].astype(str) if "Category" in df.columns else ""
    out["lat"] = df.get("Latitude")
    out["lon"] = df.get("Longitude")
    return out


def scale_if_raw(values: pd.Series, factor: float, raw_threshold: float, log: list, name: str) -> pd.Series:
    """Aplica el factor solo si los valores parecen crudos (enteros sin escalar)."""
    v = pd.to_numeric(values, errors="coerce")
    big = np.nanmax(np.abs(v.to_numpy())) if v.notna().any() else 0
    if big > raw_threshold:
        log.append(f"{name}: valores crudos detectados (máx |x| = {big:g}); se multiplicó por {factor}")
        return v * factor
    log.append(f"{name}: valores ya escalados (máx |x| = {big:g}); sin cambio")
    return v


def lst_qc_ok(qc: pd.Series) -> pd.Series:
    """QC_Day de MOD11A2: bits 0-1 = 00 (buena) o 01 (otra calidad) con error de LST <= 2 K (bits 6-7 <= 01)."""
    q = pd.to_numeric(qc, errors="coerce").fillna(255).astype(int).to_numpy()
    mandatory = q & 0b11
    lst_err = (q >> 6) & 0b11
    return pd.Series((mandatory == 0) | ((mandatory == 1) & (lst_err <= 1)), index=qc.index)


def read_mod13(path: Path, log: list, strict: bool = False) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = _base(df)
    ndvi = scale_if_raw(df[_layer_column(df, "_250m_16_days_NDVI")], 1e-4, 1.5, log, "NDVI")
    evi = scale_if_raw(df[_layer_column(df, "_250m_16_days_EVI")], 1e-4, 1.5, log, "EVI")
    rel = pd.to_numeric(df[_layer_column(df, "_250m_16_days_pixel_reliability")], errors="coerce")
    keep = rel.isin([0] if strict else [0, 1])
    valid = keep & ndvi.between(-0.2, 1.0)
    out["ndvi"] = ndvi.where(valid)
    out["evi"] = evi.where(keep & evi.between(-0.2, 1.0))
    out["reliability"] = rel
    log.append(f"MOD13Q1: {int(valid.sum())} de {len(df)} observaciones pasan calidad "
               f"(pixel_reliability en {'{0}' if strict else '{0,1}'})")
    return out


def read_mod11(path: Path, log: list) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = _base(df)
    lst_raw = pd.to_numeric(df[_layer_column(df, "LST_Day_1km")], errors="coerce").replace(0, np.nan)
    lst_k = scale_if_raw(lst_raw, 0.02, 1000, log, "LST_Day_1km")
    ok = lst_qc_ok(df[_layer_column(df, "QC_Day")]) & lst_k.between(150, 400)
    out["lst_c"] = (lst_k - 273.15).where(ok)
    log.append(f"MOD11A2: {int(ok.sum())} de {len(df)} observaciones pasan calidad (QC_Day)")
    return out


def read_mod17(path: Path, log: list) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = _base(df)
    gpp = scale_if_raw(df[_layer_column(df, "Gpp_500m")], 1e-4, 10, log, "Gpp_500m")
    ok = gpp.between(0, 3.0)  # relleno 32761-32767 crudo => > 3 escalado
    out["gpp"] = gpp.where(ok)  # kgC/m²/8 días (acumulado del periodo, no tasa diaria)
    try:
        out["psn_qc"] = pd.to_numeric(df[_layer_column(df, "Psn_QC_500m")], errors="coerce")
    except KeyError:
        out["psn_qc"] = np.nan
    log.append(f"MOD17A2HGF: {int(ok.sum())} de {len(df)} observaciones válidas")
    return out


def read_mcd12(path: Path, log: list) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = _base(df)
    out["lc_type1"] = pd.to_numeric(df[_layer_column(df, "LC_Type1")], errors="coerce")
    out["anio"] = out["fecha"].dt.year
    return out


def landcover_stability(lc: pd.DataFrame) -> pd.DataFrame:
    """Por punto: clases vistas hasta 2021, si son todas naturales y si cambió de clase."""
    rows = []
    for pid, g in lc.groupby("id"):
        g = g[g["anio"] <= LC_RELIABLE_UNTIL]
        classes = sorted(int(c) for c in g["lc_type1"].dropna().unique())
        rows.append({
            "id": pid,
            "clases_2001_2021": classes,
            "estable": len(classes) == 1,
            "natural": bool(classes) and all(c in NATURAL_CLASSES for c in classes),
            "usar": bool(classes) and all(c in NATURAL_CLASSES for c in classes),
        })
    return pd.DataFrame(rows)


def load_point_sample(folder: str | Path, strict_vi: bool = False) -> tuple[dict[str, pd.DataFrame], list[str]]:
    files = find_product_files(folder)
    log: list[str] = [f"archivos encontrados: {', '.join(f'{k}={v.name}' for k, v in files.items()) or 'ninguno'}"]
    data: dict[str, pd.DataFrame] = {}
    if "MOD13Q1" in files:
        data["MOD13Q1"] = read_mod13(files["MOD13Q1"], log, strict=strict_vi)
    if "MOD11A2" in files:
        data["MOD11A2"] = read_mod11(files["MOD11A2"], log)
    if "MOD17A2HGF" in files:
        data["MOD17A2HGF"] = read_mod17(files["MOD17A2HGF"], log)
    if "MCD12Q1" in files:
        data["MCD12Q1"] = read_mcd12(files["MCD12Q1"], log)
    return data, log
