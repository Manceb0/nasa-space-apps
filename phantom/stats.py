"""Tendencia y significación: Theil-Sen, Mann-Kendall, autocorrelación, Benjamini-Hochberg, bootstrap."""

from __future__ import annotations

import numpy as np
from scipy import stats


def mann_kendall(y) -> dict:
    """Mann-Kendall con corrección por empates. Devuelve S, Z, p bilateral y tau."""
    y = np.asarray([v for v in y if v is not None and np.isfinite(v)], dtype=float)
    n = y.size
    if n < 4:
        return {"n": n, "S": None, "Z": None, "p": None, "tau": None}
    s = 0.0
    for i in range(n - 1):
        s += np.sign(y[i + 1:] - y[i]).sum()
    _, counts = np.unique(y, return_counts=True)
    var = (n * (n - 1) * (2 * n + 5) - np.sum(counts * (counts - 1) * (2 * counts + 5))) / 18.0
    if s > 0:
        z = (s - 1) / np.sqrt(var)
    elif s < 0:
        z = (s + 1) / np.sqrt(var)
    else:
        z = 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    tau = s / (0.5 * n * (n - 1))
    return {"n": n, "S": float(s), "Z": float(z), "p": float(p), "tau": float(tau)}


def theil_sen(x, y) -> dict:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 4:
        return {"pendiente": None, "ic_bajo": None, "ic_alto": None}
    slope, intercept, lo, hi = stats.theilslopes(y[m], x[m], alpha=0.95)
    return {"pendiente": float(slope), "intercepto": float(intercept), "ic_bajo": float(lo), "ic_alto": float(hi)}


def lag1_autocorr(y) -> float | None:
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    if y.size < 5:
        return None
    a, b = y[:-1] - y.mean(), y[1:] - y.mean()
    den = np.sqrt((a ** 2).sum() * (b ** 2).sum())
    return float((a * b).sum() / den) if den else None


def benjamini_hochberg(pvals) -> list:
    """Valores q (FDR). Conserva None donde no hubo prueba."""
    idx = [i for i, p in enumerate(pvals) if p is not None]
    q = [None] * len(pvals)
    if not idx:
        return q
    p = np.array([pvals[i] for i in idx])
    order = np.argsort(p)
    m = len(p)
    ranked = p[order] * m / (np.arange(m) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.clip(ranked, 0, 1)
    for k, i in enumerate(idx):
        q[i] = float(out[k])
    return q


def bootstrap_mean_ci(values, n_boot: int = 5000, seed: int = 2026) -> dict:
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    if v.size < 3:
        return {"n": int(v.size), "media": float(v.mean()) if v.size else None, "ic95": None}
    rng = np.random.default_rng(seed)
    means = rng.choice(v, size=(n_boot, v.size), replace=True).mean(axis=1)
    return {"n": int(v.size), "media": float(v.mean()),
            "ic95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]}
