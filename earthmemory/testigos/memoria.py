"""¿Memoria del suelo o memoria de la lluvia? Modelos anidados sobre los episodios de sequía del motor nacional.

Afirmación puesta a prueba: "el estado antecedente del suelo (z de la zona de raíces de GLDAS el mes anterior al
inicio de la sequía) es el único factor significativo de la respuesta tras la sequía (β 0.46)".

Sospecha (Mentalist): GLDAS es un modelo forzado por lluvia. Su z antecedente puede ser solo la lluvia de los
meses previos 'filtrada' por el modelo. Si un índice de lluvia antecedente (API) explica lo mismo, la memoria es
de la lluvia y el suelo del modelo no añade nada.

API (índice de precipitación antecedente) con decaimiento k y ventana W días, evaluado el último día del mes
anterior al inicio:  API = Σ_{j=0}^{W−1} k^j · P(d − j).  Se estandariza por celda y mes calendario (z), igual
que el z del suelo, para no mezclar estacionalidad.

Modelos anidados (OLS; variables continuas estandarizadas; efectos fijos como dummies):
    M0: y ~ severidad + EF                (EF = mes de inicio + provincia + elevación/pendiente, o mes + celda)
    M1: M0 + lluvia antecedente (API)
    M2: M0 + suelo antecedente (z GLDAS)
    M3: M0 + API + suelo
R² parcial del suelo dado la lluvia = (RSS_M1 − RSS_M3)/RSS_M1 (y al revés para la lluvia). Varianza común =
R²(M1) + R²(M2) − R²(M3) − R²(M0). IC por bootstrap de conglomerados de AÑO (los episodios de un mismo año los
viven celdas vecinas a la vez). p del β por aproximación normal con el EE bootstrap (como el motor original).
FDR de Benjamini-Hochberg sobre todas las especificaciones.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sstats

from .common import bh_fdr

KS = (0.85, 0.90, 0.95)
WINDOWS = (30, 60, 90)


# ------------------------------------------------------------------ API

def api_window(P: np.ndarray, k: float, window: int) -> np.ndarray:
    """API truncado: A(t) = Σ_{j=0}^{W−1} k^j P(t−j), a lo largo del eje 0 (días). NaN cuenta como 0 lluvia,
    pero los primeros W−1 días (ventana incompleta) quedan NaN."""
    P = np.nan_to_num(np.asarray(P, float), nan=0.0)
    one = P.ndim == 1
    if one:
        P = P[:, None]
    n = P.shape[0]
    acc = np.zeros(P.shape)
    for j in range(min(window, n)):           # convolución causal (W ≤ 90: un bucle corto basta)
        acc[j:] += (k ** j) * P[:n - j]
    out = np.full(P.shape, np.nan)
    out[window - 1:] = acc[window - 1:]
    return out[:, 0] if one else out


def api_monthly(Pm: np.ndarray, k: float, window_days: int) -> np.ndarray:
    """API aproximado con totales MENSUALES (lluvia del mes j concentrada a mitad del mes): peso del mes j
    (j = 0 el propio mes, que termina en el día de evaluación) = k^(30·j + 15). Ventana = ceil(W/30) meses."""
    Pm = np.asarray(Pm, float)
    J = int(np.ceil(window_days / 30))
    one = Pm.ndim == 1
    if one:
        Pm = Pm[:, None]
    out = np.full(Pm.shape, np.nan)
    for t in range(J - 1, Pm.shape[0]):
        out[t] = sum(k ** (30 * j + 15) * Pm[t - j] for j in range(J))
    return out[:, 0] if one else out


def z_by_month(values: pd.DataFrame) -> pd.DataFrame:
    """z por mes calendario (media y DE de cada mes en cada columna). values: índice mensual × celdas."""
    m = values.index.month
    mu = values.groupby(m).transform("mean")
    sd = values.groupby(m).transform("std")
    return (values - mu) / sd


def month_end_api_z(daily: pd.DataFrame, k: float, window: int) -> pd.DataFrame:
    """API diario → valor del último día de cada mes → z por celda y mes calendario."""
    A = pd.DataFrame(api_window(daily.to_numpy(float), k, window), index=daily.index, columns=daily.columns)
    me = A.groupby(A.index.to_period("M")).last()
    me.index = me.index.to_timestamp()
    return z_by_month(me)


# ------------------------------------------------------------------ modelos anidados

def _design(d: pd.DataFrame, cont: list[str], fe: list[str]) -> np.ndarray:
    cols = [np.ones(len(d))]
    for c in cont:
        x = d[c].to_numpy(float)
        s = x.std()
        cols.append((x - x.mean()) / s if s > 0 else x * 0)
    for f in fe:
        dm = pd.get_dummies(d[f].astype(str), drop_first=True, dtype=float)
        cols += [dm[c].to_numpy() for c in dm.columns]
    return np.column_stack(cols)


def _fit(d, y, cont, fe):
    X = _design(d, cont, fe)
    yy = d[y].to_numpy(float)
    b, *_ = np.linalg.lstsq(X, yy, rcond=None)
    r = yy - X @ b
    rss = float(r @ r)
    tss = float(((yy - yy.mean()) ** 2).sum())
    return b, rss, 1 - rss / tss


def nested(d: pd.DataFrame, y: str, base: list[str], fe: list[str], rain: list[str], soil: str) -> dict:
    """Ajusta M0-M3 y devuelve R², R² parciales, varianza común y β estandarizados de M3."""
    _, rss0, r20 = _fit(d, y, base, fe)
    _, rss1, r21 = _fit(d, y, base + rain, fe)
    _, rss2, r22 = _fit(d, y, base + [soil], fe)
    b3, rss3, r23 = _fit(d, y, base + rain + [soil], fe)
    nb = len(base)
    return {"r2_M0": r20, "r2_M1_lluvia": r21, "r2_M2_suelo": r22, "r2_M3_ambos": r23,
            "r2p_suelo_dado_lluvia": (rss1 - rss3) / rss1 if rss1 > 0 else np.nan,
            "r2p_lluvia_dado_suelo": (rss2 - rss3) / rss2 if rss2 > 0 else np.nan,
            "r2p_suelo_solo": (rss0 - rss2) / rss0 if rss0 > 0 else np.nan,
            "r2p_lluvia_sola": (rss0 - rss1) / rss0 if rss0 > 0 else np.nan,
            "varianza_comun": r21 + r22 - r23 - r20,
            "beta_suelo_M3": float(b3[1 + nb + len(rain)]), "beta_lluvia_M3": float(b3[1 + nb]),
            "beta_suelo_M2": float(_fit(d, y, base + [soil], fe)[0][1 + nb])}


def nested_boot(d: pd.DataFrame, y: str, base, fe, rain, soil, cluster: str = "anio_cluster", B: int = 1000,
                seed: int = 2026) -> dict:
    pt = nested(d, y, base, fe, rain, soil)
    rng = np.random.default_rng(seed)
    cl = d[cluster].to_numpy()
    ucl = np.unique(cl)
    groups = {c: np.flatnonzero(cl == c) for c in ucl}
    keys = list(pt)
    bs = {k: [] for k in keys}
    for _ in range(B):
        pick = rng.choice(ucl, ucl.size, replace=True)
        idx = np.concatenate([groups[c] for c in pick])
        r = nested(d.iloc[idx], y, base, fe, rain, soil)
        for k in keys:
            bs[k].append(r[k])
    out = {"n": int(len(d)), "n_conglomerados": int(ucl.size)}
    for k in keys:
        v = np.asarray(bs[k], float)
        v = v[np.isfinite(v)]
        out[k] = pt[k]
        out[f"{k}_ic95"] = [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if v.size else [np.nan, np.nan]
        if k.startswith("beta"):
            se = v.std(ddof=1) if v.size > 2 else np.nan
            out[f"p_{k}"] = float(2 * sstats.norm.sf(abs(pt[k]) / se)) if se and se > 0 else np.nan
    # p de una cola del R² parcial del suelo dado la lluvia: fracción bootstrap ≤ 0 no tiene sentido (R² ≥ 0);
    # se usa el p del β del suelo en M3 (equivalente para un solo regresor añadido).
    return out


def verdict(row: pd.Series, beta_orig: float) -> str:
    lo, hi = row["beta_suelo_M3_ic95"]
    excl = lo > 0 or hi < 0
    if not excl or row["q_beta_suelo_M3"] >= 0.05:
        return "se cae"
    if row["beta_suelo_M3"] < 0.5 * beta_orig:
        return "se debilita"
    return "sostiene"


def fdr(df: pd.DataFrame, col: str) -> np.ndarray:
    return bh_fdr(df[col].to_numpy(float))
