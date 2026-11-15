"""Tasa de cambio de decisión ("flip rate"): ¿cambia la decisión solo por el producto que se elige?

Definiciones (todas por unidad × tiempo; unidad = provincia o celda):
- Bandera de sequía de un producto: SPI-3 <= umbral (−1.0 moderada; −1.5 severa). SPI de cada producto con SU
  propia climatología 2001-2024 (así lo usaría quien confía en ese producto): el cambio no es un sesgo de nivel.
- Cambio de decisión (varios productos): en un caso donde todos los productos tienen dato, los productos no
  son unánimes. Se informan dos tasas:
    tasa_global      = casos no unánimes / casos con dato         (depende de lo rara que es la sequía)
    tasa_condicional = casos no unánimes / casos donde ALGÚN producto da la alarma
                      (= de las veces que alguien declararía sequía, cuántas otro producto lo contradice)
- Por pares: desacuerdo = |A xor B| / |A or B| (= 1 − índice de Jaccard).
- Disparador de inundación (estilo sEAP de la Cruz Roja Dominicana: > 100 mm acumulados en 2 días): suma
  móvil de 2 días > 100 mm. Tolerancia de tiempo: el disparo de A cuenta como confirmado si B dispara en
  [t − tol, t + tol] días (tol = 0 y 1).
- IC 95 %: bootstrap por bloques de año (se remuestrean años completos con reemplazo; los meses y provincias
  de un mismo año viajan juntos, porque una sequía es nacional y dura meses).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from phantom import drought


def spi3(P: np.ndarray, fechas: pd.DatetimeIndex) -> np.ndarray:
    """P: (T, n) mm/mes → SPI-3 (T, n). Columnas sin datos → NaN."""
    out = np.full(P.shape, np.nan)
    for j in range(P.shape[1]):
        s = pd.Series(P[:, j], index=fechas)
        if s.notna().sum() < 60:
            continue
        out[:, j] = drought.spi(s, 3).to_numpy()
    return out


def flags(spi: np.ndarray, thr: float) -> np.ndarray:
    """Bandera float: 1 alarma, 0 no, NaN sin dato."""
    f = (spi <= thr).astype(float)
    f[~np.isfinite(spi)] = np.nan
    return f


def flip_components(F: dict[str, np.ndarray]) -> dict:
    """F: {producto: (T, n) float 0/1/NaN}. Devuelve matrices (T, n): valido, no_unanime, alguna_alarma."""
    S = np.stack(list(F.values()))  # (k, T, n)
    valid = np.all(np.isfinite(S), axis=0)
    s = np.nansum(S, axis=0)
    k = S.shape[0]
    any_ = valid & (s >= 1)
    flip = valid & (s >= 1) & (s <= k - 1)
    return {"valido": valid, "no_unanime": flip, "alguna_alarma": any_, "n_alarmas": np.where(valid, s, np.nan)}


def rates(c: dict, rows: np.ndarray | None = None, cols: np.ndarray | None = None) -> dict:
    v, f, a = c["valido"], c["no_unanime"], c["alguna_alarma"]
    if rows is not None:
        v, f, a = v[rows], f[rows], a[rows]
    if cols is not None:
        v, f, a = v[:, cols], f[:, cols], a[:, cols]
    nv, nf, na = int(v.sum()), int(f.sum()), int(a.sum())
    return {"n_casos": nv, "n_alguna_alarma": na, "n_no_unanime": nf,
            "tasa_global": nf / nv if nv else np.nan, "tasa_condicional": nf / na if na else np.nan}


def pair_disagreement(a: np.ndarray, b: np.ndarray) -> dict:
    m = np.isfinite(a) & np.isfinite(b)
    A, B = a[m] > 0.5, b[m] > 0.5
    union = int((A | B).sum())
    xor = int((A ^ B).sum())
    return {"n_casos": int(m.sum()), "n_union": union, "n_desacuerdo": xor,
            "tasa_global": xor / m.sum() if m.sum() else np.nan,
            "tasa_condicional": xor / union if union else np.nan}


def year_bootstrap(years: np.ndarray, stat, B: int = 2000, seed: int = 2026) -> tuple[float, float, np.ndarray]:
    """stat(rows_index) → número. Remuestrea años completos. Devuelve (p2.5, p97.5, muestras)."""
    rng = np.random.default_rng(seed)
    uy = np.unique(years)
    rows_by_year = {y: np.flatnonzero(years == y) for y in uy}
    out = np.empty(B)
    for b in range(B):
        pick = rng.choice(uy, size=uy.size, replace=True)
        rows = np.concatenate([rows_by_year[y] for y in pick])
        out[b] = stat(rows)
    out = out[np.isfinite(out)]
    if not out.size:
        return np.nan, np.nan, out
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), out


def ratio_bootstrap(num: np.ndarray, den: np.ndarray, years: np.ndarray, B: int = 2000, seed: int = 2026):
    """IC por bloques de año de sum(num)/sum(den), con num/den (T, n) ya contados por fila (T)."""
    nt = num.reshape(num.shape[0], -1).sum(1).astype(float)
    dt = den.reshape(den.shape[0], -1).sum(1).astype(float)
    return year_bootstrap(years, lambda r: nt[r].sum() / dt[r].sum() if dt[r].sum() > 0 else np.nan, B, seed)


# ------------------------------------------------------------------ lluvia diaria / disparador 48 h

def accum(P: np.ndarray, n: int = 2) -> np.ndarray:
    """Suma móvil de n días que TERMINA en el día t (NaN si falta algún día). P: (T, ...)."""
    out = np.full(P.shape, np.nan)
    c = np.cumsum(np.where(np.isfinite(P), P, 0.0), axis=0)
    bad = np.cumsum(~np.isfinite(P), axis=0)
    out[n - 1:] = c[n - 1:] - np.concatenate([np.zeros((1,) + P.shape[1:]), c[:-n]])
    nb = bad[n - 1:] - np.concatenate([np.zeros((1,) + P.shape[1:]), bad[:-n]])
    out[n - 1:][nb > 0] = np.nan
    return out


def shift(P: np.ndarray, k: int) -> np.ndarray:
    """Desplaza k días: shift(P, 1)[t] = P[t-1]."""
    out = np.full(P.shape, np.nan)
    if k > 0:
        out[k:] = P[:-k]
    elif k < 0:
        out[:k] = P[-k:]
    else:
        out[:] = P
    return out


def dilate(F: np.ndarray, tol: int) -> np.ndarray:
    """Bandera 0/1 (T, n) → 1 si hubo alarma en [t − tol, t + tol]. NaN se tratan como 0."""
    if tol == 0:
        return np.nan_to_num(F) > 0.5
    X = np.nan_to_num(F) > 0.5
    out = X.copy()
    for k in range(1, tol + 1):
        out[k:] |= X[:-k]
        out[:-k] |= X[k:]
    return out


def trigger_agreement(fa: np.ndarray, fb: np.ndarray, tol: int = 0) -> dict:
    """Disparos de A y B (T, n float). Un disparo de A está confirmado si B dispara dentro de ±tol días."""
    valid = np.isfinite(fa) & np.isfinite(fb)
    A = (np.nan_to_num(fa) > 0.5) & valid
    B = (np.nan_to_num(fb) > 0.5) & valid
    a_ok = A & dilate(fb, tol)
    b_ok = B & dilate(fa, tol)
    na, nb = int(A.sum()), int(B.sum())
    n_conf = int(a_ok.sum()) + int(b_ok.sum())
    n_tot = na + nb
    return {"n_A": na, "n_B": nb, "A_confirmado_por_B": int(a_ok.sum()), "B_confirmado_por_A": int(b_ok.sum()),
            "tasa_cambio_decision": 1 - n_conf / n_tot if n_tot else np.nan}
