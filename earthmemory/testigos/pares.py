"""Re-prueba de los dos pares 'misma lluvia, distinta respuesta' con un testigo observacional (SMAP L3).

Métrica común ('eficiencia'): pendiente b de  Δ(humedad) = b · lluvia + c · humedad_inicial + EF(mes) + e
(Frisch-Waugh-Lovell: todo centrado por mes calendario dentro de cada celda).
- Mensual (como el motor de alta resolución): Δ = cambio de la media mensual, lluvia = anomalía mensual (CHIRPS
  o IMERG), sin covariable.
- Por evento (respuesta a la lluvia, SMAP): Δ = humedad en un paso del satélite menos la del paso anterior válido
  (≤ 72 h), lluvia = IMERG diario acumulado entre los dos pasos (la lluvia de cada día UTC se fecha a las 18 UTC,
  pico de la convección vespertina: AM = 10 UTC, PM = 22 UTC), covariable = humedad inicial (secado).
Prueba: bootstrap por bloques de 3 MESES compartidos por las dos celdas (conserva autocorrelación y la
correlación entre celdas); p centrado en la nula. Calibración: sustitutos con la MISMA eficiencia en A y B
(b común + residuos propios remuestreados por los mismos bloques de meses) → tasa de falsos positivos y factor de
inflación σ = mediana|z_nulo|/0.6745 (misma lógica que earthmemory.calibration); p calibrado = 2Φ(−|z|/σ).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats as sstats


@dataclass
class Serie:
    y: np.ndarray          # respuesta (Δ humedad)
    x: np.ndarray          # lluvia
    cov: np.ndarray | None  # covariable (humedad inicial) o None
    mes_cal: np.ndarray    # 0-11
    mes_idx: np.ndarray    # índice de mes absoluto (para los bloques)

    def ok(self) -> "Serie":
        m = np.isfinite(self.y) & np.isfinite(self.x)
        if self.cov is not None:
            m &= np.isfinite(self.cov)
        return Serie(self.y[m], self.x[m], None if self.cov is None else self.cov[m], self.mes_cal[m], self.mes_idx[m])

    def take(self, idx) -> "Serie":
        return Serie(self.y[idx], self.x[idx], None if self.cov is None else self.cov[idx], self.mes_cal[idx],
                     self.mes_idx[idx])

    @property
    def n(self) -> int:
        return int(self.y.size)


def _demean(v, mo):
    out = np.array(v, float)
    for m in np.unique(mo):
        s = mo == m
        out[s] -= out[s].mean()
    return out


def slope(s: Serie) -> float:
    y, x = _demean(s.y, s.mes_cal), _demean(s.x, s.mes_cal)
    if s.cov is None:
        return float((x * y).sum() / (x * x).sum())
    X = np.column_stack([x, _demean(s.cov, s.mes_cal)])
    return float(np.linalg.lstsq(X, y, rcond=None)[0][0])


def fit_parts(s: Serie) -> tuple[float, np.ndarray, np.ndarray]:
    """b, valores ajustados SIN el término de lluvia (EF + covariable) y residuos."""
    y = s.y
    x = _demean(s.x, s.mes_cal)
    yd = _demean(y, s.mes_cal)
    if s.cov is None:
        b = float((x * yd).sum() / (x * x).sum())
        rest = y - yd                                   # EF de mes
        res = yd - b * x
        return b, rest, res
    c = _demean(s.cov, s.mes_cal)
    bb = np.linalg.lstsq(np.column_stack([x, c]), yd, rcond=None)[0]
    rest = (y - yd) + bb[1] * c
    res = yd - bb[0] * x - bb[1] * c
    return float(bb[0]), rest, res


def month_blocks(m0: int, m1: int, L: int, rng) -> np.ndarray:
    """Secuencia de meses (m0..m1) remuestreada por bloques móviles de L meses."""
    n = m1 - m0 + 1
    nb = int(np.ceil(n / L))
    st = rng.integers(0, max(1, n - L + 1), nb)
    return (m0 + (st[:, None] + np.arange(L)[None, :]).ravel())[:n]


def _groups(s: Serie) -> dict:
    g = {}
    for k, m in enumerate(s.mes_idx):
        g.setdefault(int(m), []).append(k)
    return {m: np.array(v) for m, v in g.items()}


def boot_pair(A: Serie, B: Serie, n_boot: int = 999, L: int = 3, seed: int = 2026) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    gA, gB = _groups(A), _groups(B)
    m0 = int(min(A.mes_idx.min(), B.mes_idx.min()))
    m1 = int(max(A.mes_idx.max(), B.mes_idx.max()))
    bA, bB = np.empty(n_boot), np.empty(n_boot)
    for b in range(n_boot):
        ms = month_blocks(m0, m1, L, rng)
        ia = np.concatenate([gA[m] for m in ms if m in gA] or [np.array([], int)])
        ib = np.concatenate([gB[m] for m in ms if m in gB] or [np.array([], int)])
        bA[b] = slope(A.take(ia)) if ia.size > 10 else np.nan
        bB[b] = slope(B.take(ib)) if ib.size > 10 else np.nan
    return bA, bB


def test_pair(A: Serie, B: Serie, n_boot: int = 999, L: int = 3, seed: int = 2026) -> dict:
    A, B = A.ok(), B.ok()
    eA, eB = slope(A), slope(B)
    bA, bB = boot_pair(A, B, n_boot, L, seed)
    D = bA - bB
    D = D[np.isfinite(D)]
    d = eA - eB
    se = float(D.std(ddof=1))
    p = (1 + int((np.abs(D - d) >= abs(d)).sum())) / (D.size + 1)
    return {"n_A": A.n, "n_B": B.n, "e_A": eA, "e_B": eB,
            "e_A_ic95": np.nanpercentile(bA, [2.5, 97.5]).tolist(), "e_B_ic95": np.nanpercentile(bB, [2.5, 97.5]).tolist(),
            "delta": d, "delta_ic95": np.percentile(D, [2.5, 97.5]).tolist(), "ee": se,
            "z": d / se if se > 0 else np.nan, "p": float(p)}


def surrogates(A: Serie, B: Serie, n_sur: int = 200, n_boot: int = 199, L: int = 3, seed: int = 7) -> dict:
    """Sustitutos con la MISMA eficiencia (promedio de las dos) y residuos propios remuestreados por los mismos
    bloques de meses en las dos celdas. Devuelve la tasa de p < 0.05 y el factor de inflación σ."""
    A, B = A.ok(), B.ok()
    rng = np.random.default_rng(seed)
    bA, restA, resA = fit_parts(A)
    bB, restB, resB = fit_parts(B)
    common = (bA + bB) / 2
    gA, gB = _groups(A), _groups(B)
    m0 = int(min(A.mes_idx.min(), B.mes_idx.min()))
    m1 = int(max(A.mes_idx.max(), B.mes_idx.max()))
    xA, xB = _demean(A.x, A.mes_cal), _demean(B.x, B.mes_cal)
    zs, ps = [], []
    for _ in range(n_sur):
        src = month_blocks(m0, m1, L, rng)          # mes fuente para cada mes destino (compartido)
        mapping = {m0 + k: int(s) for k, s in enumerate(src)}
        eA = _draw(A.mes_idx, gA, resA, mapping, rng)
        eB = _draw(B.mes_idx, gB, resB, mapping, rng)
        sA = Serie(restA + common * xA + eA, A.x, A.cov, A.mes_cal, A.mes_idx)
        sB = Serie(restB + common * xB + eB, B.x, B.cov, B.mes_cal, B.mes_idx)
        r = test_pair(sA, sB, n_boot=n_boot, L=L, seed=int(rng.integers(1 << 30)))
        zs.append(r["z"])
        ps.append(r["p"])
    zs = np.asarray(zs, float)
    sig = float(np.nanmedian(np.abs(zs)) / 0.6745)
    return {"n_sustitutos": n_sur, "tasa_p05": float(np.mean(np.asarray(ps) < 0.05)), "sigma_inflacion": sig,
            "eficiencia_comun": float(common)}


def _draw(midx, groups, res, mapping, rng):
    out = np.empty(midx.size)
    keys = np.array(sorted(groups))
    for k, m in enumerate(midx):
        src = mapping.get(int(m), int(m))
        if src not in groups:                       # mes fuente sin datos: el mes con datos más cercano
            src = int(keys[np.argmin(np.abs(keys - src))])
        out[k] = res[groups[src][rng.integers(groups[src].size)]]
    return out


def calibrated_p(z: float, sigma: float) -> float:
    return float(2 * sstats.norm.sf(abs(z) / max(sigma, 1.0)))


# ------------------------------------------------------------------ construcción de series

def monthly_series(S: np.ndarray, P: np.ndarray, months: np.ndarray) -> Serie:
    """S, P mensuales (T,). y = S_t − S_{t−1}; x = anomalía de lluvia del mes t (respecto a su mes calendario)."""
    mo = months.astype("datetime64[M]").astype(int)
    cal = mo % 12
    clim = np.array([np.nanmean(P[cal == m]) for m in range(12)])
    Pa = P - clim[cal]
    y = np.full(S.size, np.nan)
    y[1:] = S[1:] - S[:-1]
    return Serie(y[1:], Pa[1:], None, cal[1:], mo[1:])


def event_series(t: np.ndarray, X: np.ndarray, days: np.ndarray, rain: np.ndarray, max_gap_h: int = 72,
                 rain_hour: int = 18) -> Serie:
    """t: tiempos de paso (datetime64[h]); X: humedad (NaN = sin retrieval válido); days/rain: IMERG diario."""
    ok = np.flatnonzero(np.isfinite(X))
    rt = days.astype("datetime64[h]") + np.timedelta64(rain_hour, "h")
    cr = np.concatenate([[0.0], np.cumsum(np.nan_to_num(rain))])
    ys, xs, cs, mc, mi = [], [], [], [], []
    for a, b in zip(ok[:-1], ok[1:]):
        gap = (t[b] - t[a]).astype(int)
        if gap > max_gap_h or gap < 1:
            continue
        i0 = np.searchsorted(rt, t[a], side="right")
        i1 = np.searchsorted(rt, t[b], side="right")
        if i0 >= rt.size or i1 > rt.size or i1 <= 0:
            continue
        seg = rain[i0:i1]
        if seg.size and np.isnan(seg).any():
            continue
        ys.append(X[b] - X[a])
        xs.append(cr[i1] - cr[i0])
        cs.append(X[a])
        m = t[b].astype("datetime64[M]").astype(int)
        mc.append(m % 12)
        mi.append(m)
    return Serie(np.array(ys), np.array(xs), np.array(cs), np.array(mc, int), np.array(mi, int))
