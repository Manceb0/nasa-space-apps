"""Tendencias con incertidumbre y significancia, vectorizadas por filas (una fila = una celda o provincia).

- Pendiente de Theil-Sen (Sen 1968) con IC 95 % por el método de rangos de Sen, usando la varianza de S del
  Mann-Kendall corregida por empates y por autocorrelación (la misma que usa la prueba).
- Mann-Kendall modificado de Hamed y Rao (1998): se quita la tendencia de Sen, se toman los rangos de los residuos,
  se usan solo las autocorrelaciones de rangos significativas al 5 % (|ρ_k| > 1.96/√n, k = 1..n−1) y
  Var*(S) = Var(S) · n/n*,  n/n* = 1 + 2/(n(n−1)(n−2)) Σ_k (n−k)(n−k−1)(n−k−2) ρ_k.
  Opción conservadora (documentada): n/n* no baja de 1 (la autocorrelación negativa no hace la prueba más liberal).
- FDR de Benjamini y Hochberg (1995) entre celdas (o entre provincias) para cada índice × periodo × producto.
- Significancia de campo de Wilks (2016): con α_global = 0.05 se usa α_FDR = 2·α_global = 0.10; el campo es
  significativo si alguna celda tiene q ≤ 0.10, y esas celdas son las "significativas FDR".
- Tendencia mínima detectable (MDT): la pendiente que esta misma prueba detectaría con 80 % de potencia a α = 0.05
  (dos colas), dados n, la desviación típica de los residuos σ y su autocorrelación de lag 1 (r1 ≥ 0):
  MDT = c_n · σ · √((1 + r1)/(1 − r1)) · 10 (por década), con c_n calibrado por Monte Carlo para la prueba de
  Hamed-Rao sobre ruido blanco gaussiano (ver `mdt_factor`). Aproximación: los índices de conteo no son gaussianos.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy import stats as sstats

from ..hr.common import bh_fdr

ALPHA = 0.05
ALPHA_FDR = 2 * ALPHA  # Wilks (2016)


def _tie_term(Y: np.ndarray) -> np.ndarray:
    """Σ_grupos t(t−1)(2t+5) por fila, vía c_i = número de valores iguales a y_i."""
    out = np.zeros(Y.shape[0])
    for s in range(0, Y.shape[0], 4000):
        B = Y[s:s + 4000]
        c = (B[:, :, None] == B[:, None, :]).sum(2)
        out[s:s + 4000] = ((c - 1) * (2 * c + 5)).sum(1)
    return out


def _acf_rows(R: np.ndarray, kmax: int) -> np.ndarray:
    Rc = R - R.mean(1, keepdims=True)
    den = (Rc ** 2).sum(1)
    out = np.zeros((R.shape[0], kmax))
    for k in range(1, kmax + 1):
        out[:, k - 1] = np.where(den > 0, (Rc[:, :-k] * Rc[:, k:]).sum(1) / np.where(den > 0, den, 1), 0.0)
    return out


def _complete_rows(Y: np.ndarray, x: np.ndarray, alpha: float = ALPHA, hamed_rao: bool = True) -> dict:
    Y = np.asarray(Y, float)
    x = np.asarray(x, float)
    N, n = Y.shape
    i, j = np.triu_indices(n, 1)
    D = Y[:, j] - Y[:, i]
    S = np.sign(D).sum(1)
    var0 = (n * (n - 1) * (2 * n + 5) - _tie_term(Y)) / 18.0
    slopes = np.sort(D / (x[j] - x[i])[None, :], axis=1)
    slope = np.median(slopes, axis=1)
    inter = np.median(Y, axis=1) - slope * np.median(x)
    res = Y - (inter[:, None] + slope[:, None] * x[None, :])
    # Hamed-Rao
    if hamed_rao and n > 3:
        R = sstats.rankdata(res, axis=1)
        rho = _acf_rows(R, n - 1)
        k = np.arange(1, n)
        sig = np.abs(rho) > sstats.norm.ppf(1 - alpha / 2) / np.sqrt(n)
        w = (n - k) * (n - k - 1) * (n - k - 2)
        fac = 1 + 2.0 / (n * (n - 1) * (n - 2)) * (np.where(sig, rho, 0.0) * w[None, :]).sum(1)
        fac = np.maximum(fac, 1.0)
    else:
        fac = np.ones(N)
    var = var0 * fac
    num = S - np.sign(S)
    with np.errstate(invalid="ignore", divide="ignore"):
        Z = np.where(var > 0, num / np.sqrt(np.where(var > 0, var, 1)), 0.0)
        Z0 = np.where(var0 > 0, num / np.sqrt(np.where(var0 > 0, var0, 1)), 0.0)
    p = 2 * sstats.norm.sf(np.abs(Z))
    p0 = 2 * sstats.norm.sf(np.abs(Z0))
    # IC de Sen (como scipy.stats.theilslopes, con la varianza corregida)
    nt = slopes.shape[1]
    zc = sstats.norm.ppf(1 - alpha / 2)
    sd = np.sqrt(np.maximum(var, 0))
    Ru = np.clip(np.round((nt + zc * sd) / 2.0).astype(int), 0, nt - 1)
    Rl = np.clip(np.round((nt - zc * sd) / 2.0).astype(int) - 1, 0, nt - 1)
    lo = np.take_along_axis(slopes, Rl[:, None], 1)[:, 0]
    hi = np.take_along_axis(slopes, Ru[:, None], 1)[:, 0]
    # residuos para σ y r1
    sig_res = res.std(1, ddof=2) if n > 2 else np.full(N, np.nan)
    a = res[:, :-1] - res.mean(1, keepdims=True)
    b = res[:, 1:] - res.mean(1, keepdims=True)
    den = np.sqrt((a ** 2).sum(1) * (b ** 2).sum(1))
    r1 = np.where(den > 0, (a * b).sum(1) / np.where(den > 0, den, 1), 0.0)
    const = var0 <= 0
    p = np.where(const, 1.0, p)
    p0 = np.where(const, 1.0, p0)
    return {"n": np.full(N, n), "S": S, "Z": Z, "p": p, "p_sin_correccion": p0, "factor_hr": fac,
            "pendiente": slope, "ic_inf": lo, "ic_sup": hi, "intercepto": inter, "sigma_res": sig_res,
            "r1": r1, "media": Y.mean(1), "constante": const}


KEYS = ["n", "S", "Z", "p", "p_sin_correccion", "factor_hr", "pendiente", "ic_inf", "ic_sup", "intercepto",
        "sigma_res", "r1", "media", "constante"]


def trend_rows(Y: np.ndarray, x: np.ndarray, min_n: int = 12, alpha: float = ALPHA, hamed_rao: bool = True) -> dict:
    """Theil-Sen + MK Hamed-Rao por fila. Filas con NaN: se usan los años con dato si son ≥ min_n."""
    Y = np.asarray(Y, float)
    x = np.asarray(x, float)
    N = Y.shape[0]
    out = {k: np.full(N, np.nan) for k in KEYS}
    out["constante"] = np.zeros(N, bool)
    full = np.isfinite(Y).all(1)
    if full.any():
        r = _complete_rows(Y[full], x, alpha, hamed_rao)
        for k in KEYS:
            out[k][full] = r[k]
    for idx in np.flatnonzero(~full):
        ok = np.isfinite(Y[idx])
        if ok.sum() < min_n:
            continue
        r = _complete_rows(Y[idx, ok][None, :], x[ok], alpha, hamed_rao)
        for k in KEYS:
            out[k][idx] = r[k][0]
    out["pendiente_decada"] = out["pendiente"] * 10
    out["ic95_inf"] = out["ic_inf"] * 10
    out["ic95_sup"] = out["ic_sup"] * 10
    # dirección: signo de Sen; si Sen = 0, signo de S (para no perder la dirección en índices de conteo)
    s = np.sign(out["pendiente"])
    out["signo"] = np.where(s == 0, np.sign(out["S"]), s)
    return out


@lru_cache(maxsize=64)
def mdt_factor(n: int, power: float = 0.8, alpha: float = ALPHA, n_sim: int = 4000, seed: int = 7) -> float:
    """c_n tal que una pendiente δ = c_n·σ por año se detecta con la potencia dada (prueba de Hamed-Rao, ruido
    blanco gaussiano σ = 1, x = 0..n−1). Búsqueda por bisección sobre la potencia simulada (mismos ruidos)."""
    rng = np.random.default_rng(seed)
    E = rng.standard_normal((n_sim, n))
    x = np.arange(n, dtype=float)

    def pw(d):
        r = _complete_rows(E + d * x[None, :], x, alpha, True)
        return float(np.mean(r["p"] < alpha))

    lo, hi = 0.0, 1.0
    while pw(hi) < power:
        hi *= 2
    for _ in range(18):
        mid = (lo + hi) / 2
        if pw(mid) < power:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def mdt_decade(res: dict) -> np.ndarray:
    n = res["n"]
    out = np.full(n.shape, np.nan)
    r1 = np.clip(np.nan_to_num(res["r1"]), 0.0, 0.9)
    infl = np.sqrt((1 + r1) / (1 - r1))
    for nn in np.unique(n[np.isfinite(n)]).astype(int):
        sel = n == nn
        out[sel] = mdt_factor(int(nn)) * res["sigma_res"][sel] * infl[sel] * 10
    return out


def fdr(p: np.ndarray) -> np.ndarray:
    return bh_fdr(p)


def field_significance_wilks(q: np.ndarray, alpha_fdr: float = ALPHA_FDR) -> bool:
    q = np.asarray(q, float)
    return bool(np.nanmin(q) <= alpha_fdr) if np.isfinite(q).any() else False


def confidence_class(sig_a: np.ndarray, sig_b: np.ndarray, sgn_a: np.ndarray, sgn_b: np.ndarray) -> np.ndarray:
    """Clase de confianza de dos productos (A = IMERG, B = CHIRPS)."""
    sig_a = np.asarray(sig_a, bool)
    sig_b = np.asarray(sig_b, bool)
    same = (sgn_a * sgn_b) > 0
    opp = (sgn_a * sgn_b) < 0
    out = np.full(sig_a.shape, "sin señal detectable", dtype=object)
    out[(sig_a | sig_b) & ~opp] = "consistente"   # una significativa y la otra en la misma dirección (o plana)
    out[sig_a & sig_b & same] = "robusta"
    out[(sig_a | sig_b) & opp] = "en disputa"
    nan = ~(np.isfinite(sgn_a) & np.isfinite(sgn_b))
    out[nan] = "sin dato"
    return out


CLASSES = ["robusta", "consistente", "en disputa", "sin señal detectable"]


# ------------------------------------------------------------------ sustitutos nulos (calibración)

def detrend_field(Y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Y (años × filas) → residuos de Theil-Sen + media de cada fila (sin tendencia, con su nivel)."""
    r = _complete_rows(Y.T, x, ALPHA, False)
    return Y - (r["pendiente"][None, :] * (x[:, None] - x.mean()))


def phase_surrogate(R: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Aleatorización de fases multivariada (misma fase en todas las columnas; Prichard y Theiler 1994)."""
    from ..calibration import phase_surrogate as ps
    mu = R.mean(0, keepdims=True)
    return ps(R - mu, rng) + mu


def block_surrogate(R: np.ndarray, rng: np.random.Generator, block: int = 3) -> np.ndarray:
    """Bloques circulares de `block` años, los mismos para todas las columnas."""
    from ..calibration import block_surrogate as bs
    return bs(R, rng, block)


def calibrate(Y: np.ndarray, x: np.ndarray, n_surr: int = 300, method: str = "fase", seed: int = 2026,
              block: int = 3) -> dict:
    """Repite exactamente la prueba de la corrida (MK Hamed-Rao + BH, criterio de Wilks) en campos nulos sin
    tendencia que conservan la autocorrelación y la correlación espacial. Y: años × filas, completo."""
    keep = np.isfinite(Y).all(0)
    Y = Y[:, keep]
    R = detrend_field(Y, x)
    obs = trend_rows(Y.T, x)
    q_obs = fdr(obs["p"])
    nsig_obs = int((q_obs <= ALPHA_FDR).sum())
    np05_obs = int((obs["p"] < ALPHA).sum())
    rng = np.random.default_rng(seed)
    rate, rate0, anyq, nsig, np05 = [], [], [], [], []
    for _ in range(n_surr):
        Rs = phase_surrogate(R, rng) if method == "fase" else block_surrogate(R, rng, block)
        r = trend_rows(Rs.T, x)
        q = fdr(r["p"])
        rate.append(np.mean(r["p"] < ALPHA))
        rate0.append(np.mean(r["p_sin_correccion"] < ALPHA))
        anyq.append(bool((q <= ALPHA_FDR).any()))
        nsig.append(int((q <= ALPHA_FDR).sum()))
        np05.append(int((r["p"] < ALPHA).sum()))
    rate, nsig, np05 = np.asarray(rate), np.asarray(nsig), np.asarray(np05)
    return {"metodo": "fases aleatorias multivariadas" if method == "fase" else f"bloques circulares de {block} años",
            "n_sustitutos": n_surr, "n_filas": int(Y.shape[1]),
            "fpr_local_p05": float(rate.mean()), "fpr_local_p05_ic95": [float(np.percentile(rate, 2.5)), float(np.percentile(rate, 97.5))],
            "fpr_local_p05_sin_correccion_hr": float(np.mean(rate0)),
            "fraccion_mapas_nulos_con_celda_fdr": float(np.mean(anyq)),
            "celdas_p05_observadas": np05_obs, "celdas_p05_nulo_p95": float(np.percentile(np05, 95)),
            "celdas_fdr_observadas": nsig_obs,
            "p_campo_bootstrap": float((1 + (np05 >= np05_obs).sum()) / (1 + n_surr))}
