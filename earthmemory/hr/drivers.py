"""¿Qué factores estáticos acompañan a la respuesta del suelo? Ridge estandarizado + validación cruzada espacial.

- Variables estandarizadas (z) para que los coeficientes sean tamaños de efecto comparables (DE de la
  respuesta por DE del factor, manteniendo los demás fijos).
- λ elegido por validación cruzada interna; la habilidad se mide con validación cruzada EXTERNA dejando fuera
  bloques espaciales de 0.5° × 0.5° (≈ 55 km): una celda vecina no puede 'filtrar' información a su vecina.
  Se informa también la R² de una validación cruzada aleatoria para mostrar cuánto la infla la autocorrelación.
- IC 95 % de los coeficientes por bootstrap de bloques espaciales (se remuestrean bloques enteros).
- Autocorrelación espacial de los residuos: I de Moran con vecinos reina, p por permutación.
Asociación, no causa: los factores están correlacionados entre sí (p. ej. elevación, pendiente y bosque).
"""

from __future__ import annotations

import numpy as np

LAMBDAS = np.logspace(-2, 3, 26)


def _ridge(X, y, lam):
    k = X.shape[1]
    return np.linalg.solve(X.T @ X + lam * np.eye(k), X.T @ y)


def _r2(y, yhat):
    return 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def _cv_pred(X, y, groups, lam):
    yhat = np.empty_like(y)
    for g in np.unique(groups):
        te = groups == g
        tr = ~te
        mx, sx = X[tr].mean(0), X[tr].std(0)
        sx[sx == 0] = 1
        my = y[tr].mean()
        b = _ridge((X[tr] - mx) / sx, y[tr] - my, lam)
        yhat[te] = my + ((X[te] - mx) / sx) @ b
    return yhat


def choose_lambda(X, y, groups) -> float:
    scores = [_r2(y, _cv_pred(X, y, groups, lam)) for lam in LAMBDAS]
    return float(LAMBDAS[int(np.argmax(scores))])


def spatial_blocks(lat, lon, size=0.5) -> np.ndarray:
    return (np.floor((lat - 17.0) / size) * 100 + np.floor((lon + 73.0) / size)).astype(int)


def morans_i(resid, ii, jj, n_perm=999, seed=2026) -> tuple[float, float]:
    """I de Moran con vecinos reina en la rejilla (ii, jj índices de fila/columna de cada celda)."""
    pos = {(a, b): k for k, (a, b) in enumerate(zip(ii, jj))}
    pairs = []
    for k, (a, b) in enumerate(zip(ii, jj)):
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                if (da or db) and (a + da, b + db) in pos:
                    pairs.append((k, pos[(a + da, b + db)]))
    P = np.array(pairs)
    z = resid - resid.mean()

    def I(zz):
        return len(zz) / len(P) * (zz[P[:, 0]] * zz[P[:, 1]]).sum() / (zz ** 2).sum()

    obs = I(z)
    rng = np.random.default_rng(seed)
    null = np.array([I(rng.permutation(z)) for _ in range(n_perm)])
    return float(obs), float((1 + (null >= obs).sum()) / (n_perm + 1))


def analyse(y, X, names, lat, lon, ii, jj, n_boot=500, seed=2026) -> dict:
    ok = np.isfinite(y) & np.isfinite(X).all(1)
    y, X, lat, lon, ii, jj = y[ok], X[ok], lat[ok], lon[ok], ii[ok], jj[ok]
    groups = spatial_blocks(lat, lon)
    lam = choose_lambda(X, y, groups)
    yhat_sp = _cv_pred(X, y, groups, lam)
    rng = np.random.default_rng(seed)
    rand_groups = rng.integers(0, len(np.unique(groups)), y.size)
    yhat_rand = _cv_pred(X, y, rand_groups, lam)
    mx, sx = X.mean(0), X.std(0)
    sx[sx == 0] = 1
    Z = (X - mx) / sx
    sy = y.std()
    beta = _ridge(Z, (y - y.mean()) / sy, lam)
    # Bootstrap por bloques espaciales
    ug = np.unique(groups)
    B = np.empty((n_boot, X.shape[1]))
    for b in range(n_boot):
        pick = rng.choice(ug, ug.size, replace=True)
        idx = np.concatenate([np.flatnonzero(groups == g) for g in pick])
        Zb = (X[idx] - X[idx].mean(0)) / np.where(X[idx].std(0) > 0, X[idx].std(0), 1)
        B[b] = _ridge(Zb, (y[idx] - y[idx].mean()) / y[idx].std(), lam)
    lo, hi = np.percentile(B, [2.5, 97.5], axis=0)
    resid = y - (y.mean() + sy * (Z @ beta))
    I, pI = morans_i(resid, ii, jj, seed=seed)
    # Correlación simple de Spearman (descriptiva) para cada factor
    from scipy.stats import spearmanr
    rho = [float(spearmanr(X[:, k], y).statistic) for k in range(X.shape[1])]
    return {"n": int(y.size), "n_bloques": int(ug.size), "lambda": lam,
            "r2_cv_espacial": float(_r2(y, yhat_sp)), "r2_cv_aleatoria": float(_r2(y, yhat_rand)),
            "r2_ajuste": float(_r2(y, y.mean() + sy * (Z @ beta))),
            "coef": {n: {"beta_z": float(beta[k]), "ic95": [float(lo[k]), float(hi[k])],
                         "excluye_0": bool(lo[k] > 0 or hi[k] < 0), "spearman": rho[k]}
                     for k, n in enumerate(names)},
            "moran_residuos": {"I": I, "p_perm": pI}}
