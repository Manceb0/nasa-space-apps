"""Tendencias para la herramienta de detective: misma estadística que phantom.stats, sobre
anomalías anuales (se quita el ciclo estacional), para la serie completa y para cada ventana
de 10 años o más. El navegador solo consulta estos resultados; no recalcula estadística.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import stats

MIN_WINDOW_YEARS = 10
ALPHA = 0.05


def monthly_anomaly(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    clim = s.groupby(s.index.month).mean()
    anom = s - s.index.month.map(clim).to_numpy()
    return anom, clim


def annual_anomaly(anom: pd.Series) -> pd.DataFrame:
    g = anom.groupby(anom.index.year)
    df = pd.DataFrame({"anom": g.mean(), "meses_validos": g.count()})
    return df[df["meses_validos"] == 12]


def trend(years: np.ndarray, values: np.ndarray) -> dict:
    mk = stats.mann_kendall_ar1(years, values)
    ts = stats.theil_sen(years, values)
    if ts["pendiente"] is None:
        return {"n": int(len(values)), "pendiente_decada": None}
    return {
        "n": int(len(values)),
        "pendiente_decada": ts["pendiente"] * 10,
        "intercepto": ts["intercepto"],  # recta: anomalía = intercepto + (pendiente_decada/10) · año
        "ic95_decada": [ts["ic_bajo"] * 10, ts["ic_alto"] * 10],
        "p_mk_simple": mk["p"],
        "p_mk": mk["p_ajustado"],  # el veredicto usa el p corregido por autocorrelación
        "factor_varianza_ar1": mk["factor_varianza"],
        "tau": mk["tau"],
        "autocorr_lag1": stats.lag1_autocorr(values),
        "cambio_total": ts["pendiente"] * (years.max() - years.min()),
    }


def verdict(t: dict) -> str:
    """Una etiqueta que no confunde 'no significativo' con 'no hay cambio'."""
    if t.get("pendiente_decada") is None:
        return "insuficiente"
    lo, hi = t["ic95_decada"]
    if t["p_mk"] < ALPHA and (lo > 0 or hi < 0):
        return "sube" if t["pendiente_decada"] > 0 else "baja"
    if t["p_mk"] < 0.10:
        return "indicio"
    return "sin_evidencia"


def windows(annual: pd.DataFrame) -> list[dict]:
    years = annual.index.to_numpy()
    out = []
    for i, y0 in enumerate(years):
        for y1 in years[i:]:
            if y1 - y0 + 1 < MIN_WINDOW_YEARS:
                continue
            sel = annual.loc[y0:y1]
            t = trend(sel.index.to_numpy(dtype=float), sel["anom"].to_numpy())
            out.append({"inicio": int(y0), "fin": int(y1), **t, "veredicto": verdict(t)})
    return out


def misleading_windows(ws: list[dict], full_verdict: str, k: int = 3) -> list[dict]:
    """Ventanas cuya conclusión contradice la de la serie completa: material para enseñar."""
    def sign(v):
        return {"sube": 1, "baja": -1}.get(v, 0)
    cands = [w for w in ws if w["veredicto"] in ("sube", "baja") and sign(w["veredicto"]) != sign(full_verdict)]
    cands.sort(key=lambda w: (w["p_mk"], -(w["fin"] - w["inicio"])))
    return cands[:k]


def analyze(s: pd.Series) -> dict:
    anom, clim = monthly_anomaly(s)
    annual = annual_anomaly(anom)
    full = trend(annual.index.to_numpy(dtype=float), annual["anom"].to_numpy())
    full["veredicto"] = verdict(full)
    ws = windows(annual)
    amp = float(clim.max() - clim.min())
    return {
        "climatologia": [float(v) for v in clim.reindex(range(1, 13))],
        "amplitud_estacional": amp,
        "anomalia_mensual": [None if pd.isna(v) else float(v) for v in anom],
        "anual": {"anios": [int(y) for y in annual.index], "anomalia": [float(v) for v in annual["anom"]]},
        "completa": full,
        "ventanas": ws,
        "ventanas_que_enganan": misleading_windows(ws, full["veredicto"]),
        "autocorr_lag1_mensual": stats.lag1_autocorr(anom.to_numpy()),
    }
