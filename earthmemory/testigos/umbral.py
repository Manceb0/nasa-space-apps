"""¿Sobrevive el umbral nacional θ (≈ 0.59 del llenado) fuera del modelo de cubo de TerraClimate?

Misma regresión segmentada agrupada que earthmemory.hr.thresholds.pooled_curve (efectos fijos celda × mes,
bootstrap de bloques de TIEMPO compartidos por todas las celdas), pero con el estado antecedente f y la respuesta y
intercambiables y con huecos permitidos (SMAP no tiene dato todos los meses):
    y = FE + b1·Pa + b2·f + b3·Pa·f + b4·h + b5·Pa·h,   h = (f − θ)+
'Quiebre sostenido' = IC 95 % de b5 excluye 0 (mismo criterio que el informe de alta resolución).

Variantes:
  (0) original reconstruido: y = ΔS TerraClimate, f = llenado TerraClimate, Pa = CHIRPS (control de que el código
      reproduce θ ≈ 0.59), también solo 2015-04..2024-12;
  (1) SMAP L3: y = Δ humedad superficial observada, f = llenado SMAP L3, Pa = CHIRPS (en el píxel 9 km);
  (2) API en lugar del cubo: y = ΔS TerraClimate, f = llenado del API de IMERG (k 0.90, 90 d);
  (3) totalmente observacional: y = Δ SMAP L3, f = llenado del API de IMERG.
"""

from __future__ import annotations

import numpy as np

from ..hr.thresholds import moving_block_index


def demean_masked(A: np.ndarray, mo: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Centra cada columna por mes calendario usando solo las filas válidas (W); las inválidas quedan en 0."""
    out = np.zeros_like(A, dtype=float)
    for m in range(12):
        s = mo == m
        if not s.any():
            continue
        w = W[s]
        a = np.where(w, A[s], 0.0)
        cnt = w.sum(0)
        mu = np.divide(a.sum(0), cnt, out=np.zeros(A.shape[1]), where=cnt > 0)
        out[s] = np.where(w, A[s] - mu, 0.0)
    return out


def _fit(Y, PA, F, mo, W, thetas):
    yd = demean_masked(Y, mo, W).ravel()
    base = [demean_masked(c, mo, W).ravel() for c in (PA, F, PA * F)]
    X0 = np.column_stack(base)
    g0 = X0.T @ yd
    b0 = np.linalg.solve(X0.T @ X0, g0)
    rss0 = float(yd @ yd - b0 @ g0)
    best = None
    for th in thetas:
        H = np.clip(F - th, 0, None)
        X = np.column_stack(base + [demean_masked(H, mo, W).ravel(), demean_masked(PA * H, mo, W).ravel()])
        G, g = X.T @ X, X.T @ yd
        bb = np.linalg.lstsq(G, g, rcond=None)[0]
        rss = float(yd @ yd - bb @ g)
        if best is None or rss < best[0]:
            best = (rss, float(th), bb)
    return best, rss0, int(W.sum())


def pooled(Y, PA, F, mo, n_boot: int = 200, L: int = 12, seed: int = 2026, fgrid=None) -> dict:
    """Y, PA, F: (T, C) con NaN donde no hay dato. mo: (T,) mes calendario 0-11."""
    W = np.isfinite(Y) & np.isfinite(PA) & np.isfinite(F)
    Y, PA, F = np.where(W, Y, 0.0), np.where(W, PA, 0.0), np.where(W, F, 0.0)
    fgrid = np.linspace(0.05, 0.95, 37) if fgrid is None else fgrid
    thetas = np.unique(np.round(np.quantile(F[W], np.arange(0.15, 0.851, 0.05)), 3))
    (rss1, th, b), rss0, n = _fit(Y, PA, F, mo, W, thetas)
    dbic = n * np.log(rss0 / n) + 3 * np.log(n) - (n * np.log(rss1 / n) + 6 * np.log(n))
    eff = lambda bb, tt: bb[0] + bb[2] * fgrid + bb[4] * np.clip(fgrid - tt, 0, None)  # noqa: E731
    rng = np.random.default_rng(seed)
    TH, B5, EF = [], [], []
    for _ in range(n_boot):
        ii = moving_block_index(Y.shape[0], L, rng)
        (_, tb, bb), _, _ = _fit(Y[ii], PA[ii], F[ii], mo[ii], W[ii], thetas)
        TH.append(tb)
        B5.append(bb[4])
        EF.append(eff(bb, tb))
    TH, B5, EF = np.array(TH), np.array(B5), np.array(EF)
    lo, hi = np.percentile(B5, [2.5, 97.5])
    return {"n_celdas": int((W.sum(0) > 0).sum()), "n_obs": n, "theta": th,
            "theta_ic95": np.percentile(TH, [2.5, 97.5]).tolist(), "dBIC": float(dbic), "b5": float(b[4]),
            "b5_ic95": [float(lo), float(hi)], "b5_excluye_0": bool(lo > 0 or hi < 0),
            "f": fgrid.tolist(), "ef": eff(b, th).tolist(), "ef_lo": np.percentile(EF, 2.5, 0).tolist(),
            "ef_hi": np.percentile(EF, 97.5, 0).tolist(), "f_q05_q95": np.quantile(F[W], [0.05, 0.95]).tolist()}


def fill_fraction(S: np.ndarray) -> np.ndarray:
    """(S − min)/(max − min) por columna, ignorando NaN."""
    lo, hi = np.nanmin(S, 0), np.nanmax(S, 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (S - lo) / np.where(hi > lo, hi - lo, np.nan)


def anomaly(P: np.ndarray, mo: np.ndarray) -> np.ndarray:
    out = np.array(P, float)
    for m in range(12):
        s = mo == m
        out[s] -= np.nanmean(P[s], axis=0)
    return out


def build(S: np.ndarray, P: np.ndarray, months: np.ndarray, Fstate: np.ndarray | None = None):
    """S (respuesta), P (lluvia) y opcionalmente el estado Fstate (T, C), mensuales. Devuelve Y, PA, F, mo con
    longitud T−1: y_t = S_t − S_{t−1}, Pa_t, f = llenado en t−1 (de S o de Fstate)."""
    mo = months.astype("datetime64[M]").astype(int) % 12
    Y = S[1:] - S[:-1]
    PA = anomaly(P, mo)[1:]
    F = fill_fraction(S if Fstate is None else Fstate)[:-1]
    return Y, PA, F, mo[1:]
