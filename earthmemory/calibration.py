"""Calibración de falsos positivos con sustitutos nulos (surrogates).

Pregunta: si NO hubiera tendencia (o si dos celdas tuvieran el MISMO acople), ¿con qué frecuencia
nuestras pruebas dirían "significativo" al 5 %? Si la tasa empírica supera mucho el 5 % nominal, la
prueba está mal calibrada y hay que corregirla (aquí: p empírico contra el nulo) o decirlo.

1) Tendencias (Theil-Sen + Mann-Kendall con corrección AR(1) sobre medias anuales de anomalías):
   - se quita el ciclo estacional y la recta (MCO) de cada celda → residuos mensuales R (T × N);
   - sustitutos por ALEATORIZACIÓN DE FASES MULTIVARIADA (Prichard y Theiler 1994): la misma fase
     aleatoria en todas las celdas conserva el espectro de cada celda (autocorrelación) y los espectros
     cruzados (correlación espacial). Alternativa: BLOQUES CIRCULARES de 24 meses con los mismos
     bloques en todas las celdas;
   - en cada sustituto se repite exactamente la prueba de la corrida principal.
   Salidas: tasa empírica de p < 0.05 por prueba, fracción de mapas nulos con al menos un
   descubrimiento BH (q < 0.05), número de celdas "significativas" por mapa nulo (para la
   significancia de campo, Livezey y Chen 1983) y un p empírico por celda.
2) Pares (Δ de r, φ o γ entre dos celdas, bootstrap por bloques):
   - nulo paramétrico: se ajusta un ARX COMÚN a las dos celdas, z(t) = c + φ z(t−1) + γ SPI-1(t) + e,
     y se simulan las dos celdas con el MISMO forzamiento de lluvia (el de la celda A) y residuos
     remuestreados en bloques conjuntos de 12 meses (conserva la correlación entre celdas, la cola
     y parte de la estacionalidad de la varianza). Bajo este nulo r, φ y γ son iguales en A y B;
   - se aplica la misma prueba (Δ / EE bootstrap) → tasa empírica de p < 0.05;
   - corrección: factor de inflación σ = mediana(|Δ/EE| nulo)/0.6745 por respuesta y métrica;
     p calibrado = 2·(1 − Φ(|Δ/EE| / σ)) y BH sobre esos p. Control: posición empírica en el nulo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sstats

from phantom import stats as pstats

from . import coupling

ALPHA = 0.05


# ------------------------------------------------------------------ Mann-Kendall AR(1) vectorizado

def mk_ar1_matrix(Y: np.ndarray, x: np.ndarray) -> dict:
    """Misma prueba que phantom.stats.mann_kendall_ar1, fila por fila (Y: N × n, sin NaN, sin empates).
    Devuelve Z y p (simple y AR(1)), pendiente Theil-Sen por unidad de x y r1 de residuos."""
    Y = np.asarray(Y, float)
    x = np.asarray(x, float)
    n = Y.shape[1]
    i, j = np.triu_indices(n, 1)
    D = Y[:, j] - Y[:, i]
    S = np.sign(D).sum(1)
    var0 = n * (n - 1) * (2 * n + 5) / 18.0
    slope = np.median(D / (x[j] - x[i]), axis=1)
    inter = np.median(Y, axis=1) - slope * np.median(x)
    res = Y - (inter[:, None] + slope[:, None] * x[None, :])
    a = res[:, :-1] - res.mean(1, keepdims=True)
    b = res[:, 1:] - res.mean(1, keepdims=True)
    den = np.sqrt((a ** 2).sum(1) * (b ** 2).sum(1))
    r1 = np.where(den > 0, (a * b).sum(1) / np.where(den > 0, den, 1), 0.0)
    k = np.arange(1, n)
    fac = np.where(r1 > 0, 1 + 2 * ((1 - k / n)[None, :] * np.power(np.clip(r1, 0, None)[:, None], k[None, :])).sum(1), 1.0)
    num = S - np.sign(S)
    z0 = num / np.sqrt(var0)
    z1 = num / np.sqrt(var0 * fac)
    return {"S": S, "Z": z1, "p": 2 * sstats.norm.sf(np.abs(z1)), "p_simple": 2 * sstats.norm.sf(np.abs(z0)),
            "pendiente": slope, "r1": r1, "factor": fac}


def annual_means(M: np.ndarray, years: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    uy = np.unique(years)
    A = np.vstack([M[years == y].mean(0) for y in uy])  # años × N
    return uy.astype(float), A


def deseason_detrend(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Anomalía mensual (resta la media de cada mes calendario) y residuos tras quitar la recta MCO."""
    X = df.to_numpy(float)
    m = df.index.month.to_numpy()
    A = X.copy()
    for mm in range(1, 13):
        A[m == mm] -= np.nanmean(X[m == mm], axis=0)
    t = np.arange(len(df), dtype=float)
    tc = t - t.mean()
    beta = (tc[:, None] * A).sum(0) / (tc ** 2).sum()
    R = A - (A.mean(0)[None, :] + tc[:, None] * beta[None, :])
    return A, R


def phase_surrogate(R: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    T = R.shape[0]
    F = np.fft.rfft(R, axis=0)
    ph = rng.uniform(0, 2 * np.pi, size=F.shape[0])
    ph[0] = 0.0
    if T % 2 == 0:
        ph[-1] = 0.0
    return np.fft.irfft(F * np.exp(1j * ph)[:, None], n=T, axis=0)


def block_surrogate(R: np.ndarray, rng: np.random.Generator, block: int = 24) -> np.ndarray:
    T = R.shape[0]
    nb = int(np.ceil(T / block))
    starts = rng.integers(0, T, size=nb)
    idx = ((starts[:, None] + np.arange(block)[None, :]) % T).ravel()[:T]
    return R[idx]


def trend_calibration(df: pd.DataFrame, n_surr: int = 500, seed: int = 2026, method: str = "fase",
                      block: int = 24) -> tuple[dict, pd.DataFrame]:
    """df: tiempo × celda (mensual, completo en las celdas que entran). Devuelve (resumen, tabla por celda)."""
    df = df.loc[:, df.notna().all()]
    years = df.index.year.to_numpy()
    A, R = deseason_detrend(df)
    yrs, obs_ann = annual_means(A, years)
    obs = mk_ar1_matrix(obs_ann.T, yrs)
    rng = np.random.default_rng(seed)
    N = df.shape[1]
    exceed = np.zeros(N)
    nsig, any_bh, rej = [], [], []
    absZ = np.abs(obs["Z"])
    for _ in range(n_surr):
        Rs = phase_surrogate(R, rng) if method == "fase" else block_surrogate(R, rng, block)
        _, ann = annual_means(Rs, years)
        res = mk_ar1_matrix(ann.T, yrs)
        p = res["p"]
        rej.append(np.mean(p < ALPHA))
        nsig.append(int((p < ALPHA).sum()))
        q = np.asarray(pstats.benjamini_hochberg(list(p)), float)
        any_bh.append(bool((q < ALPHA).any()))
        exceed += np.abs(res["Z"]) >= absZ
    p_emp = (1 + exceed) / (1 + n_surr)
    q_emp = np.asarray(pstats.benjamini_hochberg(list(p_emp)), float)
    q_obs = np.asarray(pstats.benjamini_hochberg(list(obs["p"])), float)
    nsig = np.asarray(nsig)
    nsig_obs = int((obs["p"] < ALPHA).sum())
    summary = {"metodo": "fases aleatorias multivariadas" if method == "fase" else f"bloques circulares de {block} meses",
               "n_sustitutos": n_surr, "n_celdas": N, "alfa_nominal": ALPHA,
               "tasa_empirica_p05": float(np.mean(rej)),
               "tasa_empirica_p05_ic95": [float(np.percentile(rej, 2.5)), float(np.percentile(rej, 97.5))],
               "fraccion_mapas_nulos_con_descubrimiento_BH": float(np.mean(any_bh)),
               "celdas_p05_nulo_media": float(nsig.mean()), "celdas_p05_nulo_p95": float(np.percentile(nsig, 95)),
               "celdas_p05_observadas": nsig_obs,
               "p_campo": float((1 + (nsig >= nsig_obs).sum()) / (1 + n_surr)),
               "celdas_q05_BH_nominal": int((q_obs < ALPHA).sum()),
               "celdas_q05_BH_p_empirico": int((q_emp < ALPHA).sum())}
    cells = pd.DataFrame({"celda": df.columns, "Z_obs": obs["Z"], "p_mk_ar1": obs["p"], "q_bh": q_obs,
                          "p_empirico": p_emp, "q_bh_empirico": q_emp})
    return summary, cells


# ------------------------------------------------------------------ nulo de pares

def _pooled_arx(da: dict, db: dict) -> tuple[float, float, float, np.ndarray, np.ndarray]:
    y = np.concatenate([da["y"], db["y"]])
    X = np.column_stack([np.ones_like(y), np.concatenate([da["y_lag1"], db["y_lag1"]]),
                         np.concatenate([da["s_arx"], db["s_arx"]])])
    c, phi, gam = np.linalg.lstsq(X, y, rcond=None)[0]
    ea = da["y"] - (c + phi * da["y_lag1"] + gam * da["s_arx"])
    eb = db["y"] - (c + phi * db["y_lag1"] + gam * db["s_arx"])
    return float(c), float(phi), float(gam), ea, eb


def _simulate(c, phi, gam, s, e, y0):
    y = np.empty(e.size)
    prev = y0
    for t in range(e.size):
        prev = c + phi * prev + gam * s[t] + e[t]
        y[t] = prev
    return y


def pair_null(z: dict, spi_tables: dict, pairs: list, responses: list, st: coupling.Settings,
              n_surr: int = 100, B: int = 400, seed: int = 99, burn: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for a, b in pairs:
        for r in responses:
            dates, rr = coupling.build_rows(z, spi_tables[st.spi_r], spi_tables[st.spi_arx], [a, b], [r], st.lag_r)
            da, db = rr[(a, r)], rr[(b, r)]
            n = len(dates)
            c, phi, gam, ea, eb = _pooled_arx(da, db)
            s_drv = np.concatenate([da["s_arx"][-burn:], da["s_arx"]])
            idxB = coupling.block_indices(n, st.block, B, int(rng.integers(1 << 31)))
            full = np.arange(n)[None, :]
            for k in range(n_surr):
                nb = int(np.ceil((n + burn + 1) / st.block))
                starts = rng.integers(0, n - st.block + 1, size=nb)
                ix = (starts[:, None] + np.arange(st.block)).ravel()[: n + burn + 1]
                ya = _simulate(c, phi, gam, np.concatenate([[0.0], s_drv]), ea[ix], 0.0)
                yb = _simulate(c, phi, gam, np.concatenate([[0.0], s_drv]), eb[ix], 0.0)
                sims = {}
                for lab, yy in (("a", ya), ("b", yb)):
                    yv = yy[burn + 1:]
                    sims[lab] = {"s_r": da["s_r"], "y_lead": yv, "y": yv, "y_lag1": yy[burn:-1], "s_arx": da["s_arx"]}
                pa, pb = coupling.metrics_for(sims["a"], full, st.corr), coupling.metrics_for(sims["b"], full, st.corr)
                ba, bb = coupling.metrics_for(sims["a"], idxB, st.corr), coupling.metrics_for(sims["b"], idxB, st.corr)
                for m in coupling.METRICS:
                    d = float(pa[m][0] - pb[m][0])
                    bd = ba[m] - bb[m]
                    se = float(bd.std(ddof=1))
                    rows.append({"celda_a": a, "celda_b": b, "respuesta": r, "metrica": m, "sustituto": k,
                                 "delta": d, "ee_boot": se, "z": d / se if se > 0 else np.nan,
                                 "p": coupling.p_from_boot(d, bd)})
    return pd.DataFrame(rows)


def inflation(null: pd.DataFrame) -> dict:
    """Factor de inflación del error estándar por (respuesta, métrica): σ = mediana(|Δ/EE| nulo) / 0.6745.
    Bajo el nulo Δ/EE debería ser N(0, 1); σ > 1 dice cuánto subestima el bootstrap la variabilidad real."""
    return {k: float(np.nanmedian(np.abs(g["z"])) / 0.6745) for k, g in null.groupby(["respuesta", "metrica"])}


def pair_null_summary(null: pd.DataFrame) -> pd.DataFrame:
    lam = inflation(null)
    rows = []
    for (r, m), g in null.groupby(["respuesta", "metrica"]):
        z = g["z"].to_numpy(float)
        pc = 2 * sstats.norm.sf(np.abs(z) / lam[(r, m)])
        rows.append({"respuesta": r, "metrica": m, "n": int(len(g)),
                     "tasa_empirica_p05": float(np.mean(g["p"] < ALPHA)),
                     "factor_inflacion_EE": lam[(r, m)],
                     "tasa_p05_tras_calibrar": float(np.nanmean(pc < ALPHA)),
                     "z_abs_critico_95": float(np.nanpercentile(np.abs(z), 95))})
    out = pd.DataFrame(rows)
    allz = null["z"].to_numpy(float)
    pc_all = np.concatenate([2 * sstats.norm.sf(np.abs(g["z"].to_numpy(float)) / lam[k]) for k, g in null.groupby(["respuesta", "metrica"])])
    tot = {"respuesta": "TODAS", "metrica": "TODAS", "n": int(len(null)),
           "tasa_empirica_p05": float(np.mean(null["p"] < ALPHA)),
           "factor_inflacion_EE": float(np.nanmedian(np.abs(allz)) / 0.6745),
           "tasa_p05_tras_calibrar": float(np.nanmean(pc_all < ALPHA)),
           "z_abs_critico_95": float(np.nanpercentile(np.abs(allz), 95))}
    return pd.concat([out, pd.DataFrame([tot])], ignore_index=True)


def calibrated_p(tests: pd.DataFrame, null: pd.DataFrame) -> pd.Series:
    """p calibrado = 2·(1 − Φ(|Δ/EE| / σ)), σ = factor de inflación de su respuesta y métrica (como el
    'genomic control' λ). Se prefiere a la posición empírica porque con miles de pruebas el p empírico no
    puede bajar de 1/(n_nulo+1) y BH no tendría resolución. La posición empírica se guarda aparte."""
    lam = inflation(null)
    z = (tests["delta"] / tests["ee_boot"]).abs()
    sig = np.array([lam.get((r, m), np.nan) for r, m in zip(tests["respuesta"], tests["metrica"])])
    return pd.Series(2 * sstats.norm.sf(z.to_numpy(float) / sig), index=tests.index)


def empirical_p(tests: pd.DataFrame, null: pd.DataFrame) -> pd.Series:
    """Posición de |Δ/EE| observado en la distribución nula de su respuesta y métrica (control)."""
    pools = {k: np.sort(np.abs(g["z"].dropna().to_numpy())) for k, g in null.groupby(["respuesta", "metrica"])}
    out = []
    for _, t in tests.iterrows():
        pool = pools.get((t["respuesta"], t["metrica"]))
        zo = abs(t["delta"] / t["ee_boot"]) if t["ee_boot"] > 0 else np.nan
        if pool is None or not np.isfinite(zo):
            out.append(np.nan)
            continue
        ge = pool.size - np.searchsorted(pool, zo, side="left")
        out.append((1 + ge) / (1 + pool.size))
    return pd.Series(out, index=tests.index)
