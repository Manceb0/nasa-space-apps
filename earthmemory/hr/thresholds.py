"""Umbral de humedad antecedente donde cambia la respuesta del suelo a la lluvia (regresión segmentada).

Por celda, con t = mes:
    y_t  = S_t − S_{t−1}                 cambio de humedad del suelo en el mes (mm)
    Pa_t = P_t − clim_P(mes)             anomalía de lluvia del mes (mm)
    f_t  = (S_{t−1} − S_min)/(S_max − S_min)   llenado relativo antecedente (0-1 dentro del rango observado de
                                         la celda; así TerraClimate en mm y SMAP en m³/m³ son comparables)
Efectos fijos de mes calendario (Frisch-Waugh-Lovell: todo se centra por mes calendario).

    M0 (lineal):     y = FE + b1·Pa + b2·f + b3·Pa·f
    M1 (segmentada): M0 + b4·h + b5·Pa·h,   h = (f − θ)+

La 'eficiencia' de la lluvia, dy/dPa = b1 + b3·f + b5·(f − θ)+, es lineal a trozos en f con quiebre en θ.
θ se busca en una rejilla de cuantiles de f (15 %-85 %). Prueba: sup-F con distribución nula por bootstrap de
residuos de M0 en bloques circulares (12 meses, conserva la autocorrelación). FDR de Benjamini-Hochberg sobre
todas las celdas. IC de θ: bootstrap por bloques móviles de filas (pares). 'Umbral sostenido' = q < 0.05 y
ΔBIC (M0 − M1) > 2. Es asociación dentro de modelos/productos, no un mecanismo medido.
"""

from __future__ import annotations

import numpy as np

QGRID = np.arange(0.15, 0.851, 0.05)


def month_demean(A: np.ndarray, month: np.ndarray) -> np.ndarray:
    """Centra por mes calendario a lo largo del eje 0 (n, ...)."""
    out = np.array(A, float, copy=True)
    for m in range(12):
        s = month == m
        if s.any():
            out[s] -= out[s].mean(axis=0)
    return out


def circular_block_index(n: int, L: int, rng: np.random.Generator) -> np.ndarray:
    nb = int(np.ceil(n / L))
    starts = rng.integers(0, n, nb)
    return ((starts[:, None] + np.arange(L)[None, :]) % n).ravel()[:n]


def moving_block_index(n: int, L: int, rng: np.random.Generator) -> np.ndarray:
    nb = int(np.ceil(n / L))
    starts = rng.integers(0, n - L + 1, nb)
    return (starts[:, None] + np.arange(L)[None, :]).ravel()[:n]


def design(Pa, f, month, theta=None):
    cols = [Pa, f, Pa * f]
    if theta is not None:
        h = np.clip(f - theta, 0, None)
        cols += [h, Pa * h]
    return month_demean(np.column_stack(cols), month)


def rss_many(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """RSS de regresiones de cada columna de Y (n, B) sobre X (n, k) ya centrados."""
    Q, _ = np.linalg.qr(X)
    proj = Q.T @ Y
    return (Y ** 2).sum(0) - (proj ** 2).sum(0)


def series_for_cell(P: np.ndarray, S: np.ndarray, months: np.ndarray):
    """P, S: (T,) mensuales. Devuelve y, Pa, f (llenado relativo), mes (longitud T−1) y S_max."""
    mo = months.astype("datetime64[M]").astype(int) % 12
    clim = np.array([np.nanmean(P[mo == m]) for m in range(12)])
    Pa = P - clim[mo]
    smax, smin = np.nanmax(S), np.nanmin(S)
    y = np.diff(S)
    f = (S[:-1] - smin) / (smax - smin) if smax > smin else np.full(S.size - 1, np.nan)
    return y, Pa[1:], f, mo[1:], smax


def fit_cell(y, Pa, f, mo, n_boot: int = 499, n_ci: int = 300, L: int = 12, rng=None) -> dict:
    rng = rng or np.random.default_rng(0)
    n = y.size
    k0 = 3 + 12
    k1 = 5 + 12 + 1      # + θ
    yd = month_demean(y, mo)
    X0 = design(Pa, f, mo)
    thetas = np.quantile(f, QGRID)
    X1s = [design(Pa, f, mo, th) for th in thetas]
    rss0 = float(rss_many(X0, yd[:, None])[0])
    rss1 = np.array([rss_many(X, yd[:, None])[0] for X in X1s])
    j = int(np.argmin(rss1))
    F = (rss0 - rss1) / 2 / (rss1 / (n - k1))
    supF = float(F.max())
    # Nula: residuos de M0 en bloques circulares
    beta0 = np.linalg.lstsq(X0, yd, rcond=None)[0]
    fit0 = X0 @ beta0
    e0 = yd - fit0
    idx = np.stack([circular_block_index(n, L, rng) for _ in range(n_boot)], axis=1)
    Ys = month_demean(fit0[:, None] + e0[idx], mo)
    r0 = rss_many(X0, Ys)
    Fs = np.max(np.stack([(r0 - rss_many(X, Ys)) / 2 / (rss_many(X, Ys) / (n - k1)) for X in X1s]), axis=0)
    p = (1 + int((Fs >= supF).sum())) / (n_boot + 1)
    bic0 = n * np.log(rss0 / n) + k0 * np.log(n)
    bic1 = n * np.log(rss1[j] / n) + k1 * np.log(n)
    aic0 = n * np.log(rss0 / n) + 2 * k0
    aic1 = n * np.log(rss1[j] / n) + 2 * k1
    th = float(thetas[j])
    b = np.linalg.lstsq(X1s[j], yd, rcond=None)[0]
    lo_f, hi_f = np.quantile(f, [0.10, 0.90])
    eff = lambda ff: b[0] + b[2] * ff + b[4] * max(ff - th, 0.0)  # noqa: E731
    out = {"theta": th, "supF": supF, "p": p, "dBIC": float(bic0 - bic1), "dAIC": float(aic0 - aic1),
           "ef_seco": float(eff(lo_f)), "ef_umbral": float(eff(th)), "ef_humedo": float(eff(hi_f)),
           "pend_bajo": float(b[2]), "pend_sobre": float(b[2] + b[4]), "b5": float(b[4]),
           "f_q10": float(lo_f), "f_q90": float(hi_f), "n": n,
           "ef_lineal_mediana": float(np.linalg.lstsq(X0, yd, rcond=None)[0][0]
                                      + np.linalg.lstsq(X0, yd, rcond=None)[0][2] * np.median(f))}
    out["_ci_args"] = (yd, Pa, f, mo, thetas)
    return out


def theta_ci(y, Pa, f, mo, thetas, n_ci: int = 300, L: int = 12, rng=None) -> tuple[float, float]:
    """IC 95 % del umbral: bootstrap por bloques móviles de filas (y, Pa, f, mes conservan su relación)."""
    rng = rng or np.random.default_rng(0)
    n = y.size
    th_b = np.empty(n_ci)
    for b in range(n_ci):
        ii = moving_block_index(n, L, rng)
        yb, Pb, fb, mb = y[ii], Pa[ii], f[ii], mo[ii]
        ybd = month_demean(yb, mb)
        r = [rss_many(design(Pb, fb, mb, th), ybd[:, None])[0] for th in thetas]
        th_b[b] = thetas[int(np.argmin(r))]
    return float(np.quantile(th_b, 0.025)), float(np.quantile(th_b, 0.975))


def run_grid(P: np.ndarray, S: np.ndarray, months: np.ndarray, mask: np.ndarray, n_boot: int = 499,
             n_ci: int = 300, seed: int = 2026, min_smax: float = 5.0, fe: bool = True) -> dict:
    """P, S: (T, ny, nx). Devuelve mapas (ny, nx) de cada métrica."""
    ny, nx = mask.shape
    keys = ["theta", "supF", "p", "dBIC", "dAIC", "ef_seco", "ef_umbral", "ef_humedo", "pend_bajo", "pend_sobre",
            "b5", "f_q10", "f_q90", "smax", "smin", "theta_lo", "theta_hi", "ef_lineal_mediana"]
    M = {k: np.full((ny, nx), np.nan) for k in keys}
    cells = np.argwhere(mask)
    store = {}
    for c, (i, j) in enumerate(cells):
        y, Pa, f, mo, smax = series_for_cell(P[:, i, j], S[:, i, j], months)
        if not np.isfinite(smax) or smax < min_smax or np.nanstd(y) <= 0 or not np.isfinite(y).all():
            continue
        if not fe:                                             # sensibilidad: sin efectos fijos de mes
            mo = np.zeros_like(mo)
        rng = np.random.default_rng([seed, int(i), int(j)])   # determinista por celda
        r = fit_cell(y, Pa, f, mo, n_boot=n_boot, rng=rng)
        store[(i, j)] = (r.pop("_ci_args"), rng)
        for k, v in r.items():
            if k in M:
                M[k][i, j] = v
        M["smax"][i, j] = smax
        M["smin"][i, j] = np.nanmin(S[:, i, j])
        if c % 200 == 0:
            print(f"  umbrales: {c}/{len(cells)}", flush=True)
    from .common import bh_fdr
    M["q"] = bh_fdr(M["p"])
    M["sostenido"] = (M["q"] < 0.05) & (M["dBIC"] > 2)
    for (i, j), ((yd, Pa, f, mo, thetas), rng) in store.items():
        if n_ci > 0 and M["sostenido"][i, j]:
            lo, hi = theta_ci(yd, Pa, f, mo, thetas, n_ci=n_ci, rng=rng)
            M["theta_lo"][i, j], M["theta_hi"][i, j] = lo, hi
    return M


def example_curve(P, S, months, i, j) -> dict:
    """Datos para dibujar la eficiencia frente al llenado en una celda (binned + ajuste M1)."""
    y, Pa, f, mo, smax = series_for_cell(P[:, i, j], S[:, i, j], months)
    yd = month_demean(y, mo)
    r = fit_cell(y, Pa, f, mo, n_boot=19)
    th = r["theta"]
    # eficiencia empírica por tramos de f: pendiente local de yd sobre Pa centrado
    bins = np.quantile(f, np.linspace(0, 1, 9))
    eff, mid = [], []
    for a, b in zip(bins[:-1], bins[1:]):
        s = (f >= a) & (f <= b)
        pa = Pa[s] - Pa[s].mean()
        eff.append(float((pa * (yd[s] - yd[s].mean())).sum() / (pa ** 2).sum()))
        mid.append(float(np.median(f[s])))
    return {"f": f, "Pa": Pa, "yd": yd, "theta": th, "smax": smax, "bins_mid": mid, "bins_ef": eff,
            "ef_seco": r["ef_seco"], "ef_umbral": r["ef_umbral"], "ef_humedo": r["ef_humedo"],
            "f_q10": r["f_q10"], "f_q90": r["f_q90"]}


# ------------------------------------------------------------------ curva agrupada (paisajes)

def _pooled_fit(Y, PA, F, mo, thetas):
    """Ajuste agrupado por ecuaciones normales (rápido): base [Pa, f, Pa·f] fija y [h, Pa·h] por cada θ."""
    yd = month_demean(Y, mo).ravel()
    base = [month_demean(c, mo).ravel() for c in (PA, F, PA * F)]
    X0 = np.column_stack(base)
    b0 = np.linalg.solve(X0.T @ X0, X0.T @ yd)
    rss0 = float(yd @ yd - b0 @ (X0.T @ yd))
    best = None
    for th in thetas:
        H = np.clip(F - th, 0, None)
        X = np.column_stack(base + [month_demean(H, mo).ravel(), month_demean(PA * H, mo).ravel()])
        G, g = X.T @ X, X.T @ yd
        bb = np.linalg.lstsq(G, g, rcond=None)[0]
        rss = float(yd @ yd - bb @ g)
        if best is None or rss < best[0]:
            best = (rss, float(th), bb)
    return best, rss0, yd.size


def pooled_curve(P2, S2, months, n_boot=200, L=12, seed=2026, fgrid=None) -> dict:
    """Umbral COMÚN a un grupo de celdas (efectos fijos celda × mes calendario). P2, S2: (T, C) series de las C
    celdas del grupo. Incertidumbre por bootstrap de bloques móviles de TIEMPO compartidos por todas las celdas
    (conserva la correlación espacial: no se finge que cada celda sea independiente)."""
    fgrid = np.linspace(0.05, 0.95, 37) if fgrid is None else fgrid
    mo_all = months.astype("datetime64[M]").astype(int) % 12
    Ys, PAs, Fs = [], [], []
    for c in range(P2.shape[1]):
        y, Pa, f, mo, smax = series_for_cell(P2[:, c], S2[:, c], months)
        if not (np.isfinite(y).all() and np.isfinite(f).all() and np.isfinite(Pa).all()):
            continue                                       # celda sin rango (suelo constante) o con huecos
        Ys.append(y)
        PAs.append(Pa)
        Fs.append(f)
    Y, PA, F = np.column_stack(Ys), np.column_stack(PAs), np.column_stack(Fs)
    mo = mo_all[1:]
    thetas = np.unique(np.round(np.quantile(F, np.arange(0.15, 0.851, 0.05)), 3))
    (rss1, th, b), rss0, n = _pooled_fit(Y, PA, F, mo, thetas)
    k0, k1 = 3, 6
    dbic = n * np.log(rss0 / n) + k0 * np.log(n) - (n * np.log(rss1 / n) + k1 * np.log(n))
    eff = lambda bb, tt: bb[0] + bb[2] * fgrid + bb[4] * np.clip(fgrid - tt, 0, None)  # noqa: E731
    rng = np.random.default_rng(seed)
    TH, B5, EF = [], [], []
    for _ in range(n_boot):
        ii = moving_block_index(Y.shape[0], L, rng)
        (_, tb, bb), _, _ = _pooled_fit(Y[ii], PA[ii], F[ii], mo[ii], thetas)
        TH.append(tb)
        B5.append(bb[4])
        EF.append(eff(bb, tb))
    TH, B5, EF = np.array(TH), np.array(B5), np.array(EF)
    return {"n_celdas": int(Y.shape[1]), "n_obs": int(n), "theta": float(th),
            "theta_ic95": np.percentile(TH, [2.5, 97.5]).tolist(), "dBIC": float(dbic),
            "b5": float(b[4]), "b5_ic95": np.percentile(B5, [2.5, 97.5]).tolist(),
            "b5_excluye_0": bool(np.percentile(B5, 2.5) > 0 or np.percentile(B5, 97.5) < 0),
            "f": fgrid.tolist(), "ef": eff(b, th).tolist(), "ef_lo": np.percentile(EF, 2.5, 0).tolist(),
            "ef_hi": np.percentile(EF, 97.5, 0).tolist(), "f_q05_q95": np.quantile(F, [0.05, 0.95]).tolist(),
            "theta_boot": TH.tolist()}
