"""Meses de quiebre ('tipping months'): prueba de Pettitt sobre la serie mensual desestacionalizada.

Pettitt (1979): U_t = 2·Σ_{i≤t} r_i − t(n+1) (r = rangos); K = max|U_t|; el quiebre es t* = argmax|U_t|.
La p asintótica (2·exp(−6K²/(n³+n²))) supone independencia y, con series persistentes (humedad del suelo,
PDSI), da falsos quiebres. Aquí la p sale de un bootstrap por bloques circulares de la propia serie (bloques
de 12 meses; sensibilidad con 24): conserva la autocorrelación de corto plazo y destruye un cambio de nivel.
Se usan los MISMOS índices de remuestreo para todas las celdas (la nula conserva la correlación espacial) y
luego FDR de Benjamini-Hochberg sobre las celdas. Un quiebre de Pettitt indica un cambio de mediana; una
tendencia gradual también lo produce, por eso se informa la dirección y se compara con la lluvia.
"""

from __future__ import annotations

import numpy as np

from .common import bh_fdr
from .thresholds import circular_block_index


def deseasonalise(X: np.ndarray, months: np.ndarray) -> np.ndarray:
    """X (T, N) → anomalía respecto a la media de cada mes calendario."""
    mo = months.astype("datetime64[M]").astype(int) % 12
    out = np.array(X, float, copy=True)
    for m in range(12):
        s = mo == m
        out[s] -= np.nanmean(out[s], axis=0)
    return out


def _ranks(X: np.ndarray) -> np.ndarray:
    """Rangos 1..n por columna (empates rotos por orden, suficiente para series continuas)."""
    o = np.argsort(X, axis=0, kind="stable")
    r = np.empty_like(o)
    n = X.shape[0]
    np.put_along_axis(r, o, np.arange(1, n + 1)[:, None].repeat(X.shape[1], 1), axis=0)
    return r


def pettitt_stat(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """X (n, N). Devuelve K (N,) y t* (N,) (índice del último mes del primer tramo)."""
    n = X.shape[0]
    r = _ranks(X)
    t = np.arange(1, n + 1)[:, None]
    U = 2 * np.cumsum(r, axis=0) - t * (n + 1)
    U = U[:-1]
    k = np.argmax(np.abs(U), axis=0)
    return np.abs(U[k, np.arange(X.shape[1])]).astype(float), k


def pettitt_grid(X: np.ndarray, n_boot: int = 999, L: int = 12, seed: int = 2026) -> dict:
    """X (n, N) anomalías sin NaN. p por bootstrap por bloques circulares + p asintótica (referencia)."""
    n = X.shape[0]
    K, k = pettitt_stat(X)
    rng = np.random.default_rng(seed)
    exceed = np.zeros(X.shape[1])
    for _ in range(n_boot):
        ii = circular_block_index(n, L, rng)
        Kb, _ = pettitt_stat(X[ii])
        exceed += Kb >= K
    p = (1 + exceed) / (n_boot + 1)
    p_asym = np.clip(2 * np.exp(-6 * K ** 2 / (n ** 3 + n ** 2)), 0, 1)
    shift = np.array([X[k_ + 1:, c].mean() - X[:k_ + 1, c].mean() for c, k_ in enumerate(k)])
    return {"K": K, "k": k, "p": p, "q": bh_fdr(p), "p_asintotica": p_asym, "q_asintotica": bh_fdr(p_asym),
            "cambio_media": shift}
