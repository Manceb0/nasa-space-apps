"""Series mensuales de MODIS (por punto y por zona) para la herramienta de detective.

Cada observación que pasa calidad se agrega por mes:
- NDVI y LST: media de las observaciones válidas del mes.
- GPP: media de los acumulados de 8 días, dividida entre 8 → tasa diaria (kgC/m²/día × 1000 = gC/m²/día).

Un mes sin observación válida queda vacío; no se rellena. La zona es la media de las anomalías
de sus puntos (no de los valores), para que un punto más verde no domine la serie.
"""

from __future__ import annotations

import pandas as pd

MODIS_VARS = {
    "modis_ndvi": {"producto": "MOD13Q1", "col": "ndvi", "escala": 1.0},
    "modis_lst": {"producto": "MOD11A2", "col": "lst_c", "escala": 1.0},
    "modis_gpp": {"producto": "MOD17A2HGF", "col": "gpp", "escala": 1000 / 8},  # gC/m²/día
}

MONTHS = pd.date_range("2001-01-01", "2024-12-01", freq="MS")


def monthly_point(df: pd.DataFrame, col: str, scale: float) -> pd.DataFrame:
    """Devuelve un DataFrame (meses × puntos) con la media mensual de las observaciones válidas."""
    d = df[["id", "fecha", col]].dropna()
    d = d.assign(mes=d["fecha"].dt.to_period("M").dt.to_timestamp())
    m = d.groupby(["mes", "id"])[col].mean().unstack("id") * scale
    return m.reindex(MONTHS)


def region_series(monthly: pd.DataFrame, ids: list[str]) -> pd.Series:
    """Media de los valores de los puntos de la zona, reconstruida como climatología media + anomalía media.

    Así un mes en que falta un punto no cambia el nivel de la serie, solo su ruido.
    """
    sub = monthly[[c for c in ids if c in monthly.columns]]
    clim = sub.groupby(sub.index.month).transform("mean")
    anom = (sub - clim).mean(axis=1, skipna=True)
    base = clim.mean(axis=1, skipna=True)
    out = (base + anom).where(sub.notna().any(axis=1))
    return out


def coverage(monthly: pd.DataFrame, ids: list[str]) -> dict:
    sub = monthly[[c for c in ids if c in monthly.columns]]
    return {"meses_con_dato": int(sub.notna().any(axis=1).sum()), "meses_totales": int(len(sub)),
            "por_punto": {c: int(sub[c].notna().sum()) for c in sub.columns}}
