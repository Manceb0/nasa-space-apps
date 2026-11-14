"""Anomalías por celda: SPI de la lluvia, z robusto (o estándar) por mes calendario y tendencias."""

from __future__ import annotations

import numpy as np
import pandas as pd

from phantom import drought, stats
from phantom import trends as ptrends

MIN_YEARS = 8


def monthly_total_mm(rate_mm_day: pd.DataFrame) -> pd.DataFrame:
    """mm/día (media del mes) → mm en el mes."""
    return rate_mm_day.mul(rate_mm_day.index.days_in_month, axis=0)


def spi_table(precip_mm: pd.DataFrame, scale: int) -> pd.DataFrame:
    return pd.DataFrame({c: drought.spi(precip_mm[c], scale) for c in precip_mm.columns})


def robust_z(df: pd.DataFrame) -> pd.DataFrame:
    """(x − mediana del mes calendario) / (1.4826 · MAD del mes). Vacío si hay < 8 años válidos."""
    m = df.index.month
    med = df.groupby(m).transform("median")
    mad = (df - med).abs().groupby(m).transform("median")
    cnt = df.groupby(m).transform("count")
    z = (df - med) / (1.4826 * mad).replace(0, np.nan)
    return z.where(cnt >= MIN_YEARS)


def standard_z(df: pd.DataFrame) -> pd.DataFrame:
    m = df.index.month
    g = df.groupby(m)
    z = (df - g.transform("mean")) / g.transform("std").replace(0, np.nan)
    return z.where(g.transform("count") >= MIN_YEARS)


def zscore(df: pd.DataFrame, kind: str = "robusta") -> pd.DataFrame:
    return robust_z(df) if kind == "robusta" else standard_z(df)


def cell_trends(var: str, df: pd.DataFrame, unit: str) -> list[dict]:
    """Theil-Sen + Mann-Kendall AR(1) sobre la anomalía anual (media de anomalías mensuales)."""
    out = []
    for c in df.columns:
        anom, _ = ptrends.monthly_anomaly(df[c])
        ann = ptrends.annual_anomaly(anom.dropna(), min_months=12)
        if len(ann) < 10:
            continue
        t = ptrends.trend(ann.index.to_numpy(float), ann["anom"].to_numpy())
        out.append({"celda": c, "variable": var, "unidad_por_decada": unit, "n_anios": t["n"],
                    "pendiente_decada": t["pendiente_decada"], "ic95_bajo": t["ic95_decada"][0],
                    "ic95_alto": t["ic95_decada"][1], "p_mk_simple": t["p_mk_simple"], "p_mk_ar1": t["p_mk"],
                    "autocorr_lag1": t["autocorr_lag1"]})
    return out


def add_bh(rows: list[dict], pcol: str = "p_mk_ar1", qcol: str = "q_bh") -> list[dict]:
    q = stats.benjamini_hochberg([r[pcol] for r in rows])
    for r, v in zip(rows, q):
        r[qcol] = v
    return rows
