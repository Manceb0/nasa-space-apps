"""'Misma lluvia, distinta respuesta' a 0.05°: búsqueda del par más sólido, prueba y comprobación con sustitutos.

Respuesta de una celda = eficiencia e = pendiente de ΔS (cambio mensual de humedad del suelo, mm) sobre la
anomalía de lluvia CHIRPS (mm), con efectos fijos de mes calendario: mm de agua que gana el suelo por cada mm
de lluvia por encima de lo normal.

1. Bootstrap por bloques móviles (12 meses) con los MISMOS índices de tiempo para todas las celdas: así la
   diferencia e_A − e_B de cualquier par tiene su distribución bootstrap (conserva autocorrelación y la
   correlación entre las dos celdas). p = (1 + #|Δ* − Δ̂| ≥ |Δ̂|)/(B + 1) (bootstrap centrado en la nula).
2. Candidatos: dos celdas de tierra a 20-60 km (celdas distintas en SMAP 9 km y TerraClimate), lluvia anual
   media con diferencia < 5 %, correlación de anomalías mensuales CHIRPS ≥ 0.85 y distribución mensual
   parecida (Kolmogorov-Smirnov D ≤ 0.10, solo como filtro, no como prueba).
3. FDR (Benjamini-Hochberg) sobre TODOS los candidatos que pasan el filtro de lluvia.
4. Entre los significativos se elige el par con mayor |z| × distancia en factores estáticos (arcilla,
   pendiente, elevación, bosque), y se exige que SMAP L4 (NASA) dé la misma dirección si está disponible.
5. Sustitutos: para el par elegido se generan series con la MISMA eficiencia verdadera en las dos celdas
   (eficiencia común + residuos propios remuestreados en bloques compartidos) y se repite la prueba: la
   fracción de 'significativos' estima la tasa de falsos positivos real del procedimiento.
"""

from __future__ import annotations

import numpy as np

from .common import bh_fdr
from .thresholds import month_demean, moving_block_index


def efficiency_inputs(P: np.ndarray, S: np.ndarray, months: np.ndarray):
    """P, S (T, N). Devuelve y (T−1, N) y Pa (T−1, N) centrados por mes, y el mes."""
    mo = months.astype("datetime64[M]").astype(int) % 12
    Pa = month_demean(P, mo)
    y = np.diff(S, axis=0)
    return month_demean(y, mo[1:]), month_demean(Pa[1:], mo[1:]), mo[1:]


def slopes(y: np.ndarray, x: np.ndarray, mo: np.ndarray, idx: np.ndarray | None = None) -> np.ndarray:
    if idx is not None:
        y, x, mo = y[idx], x[idx], mo[idx]
        y, x = month_demean(y, mo), month_demean(x, mo)
    return (x * y).sum(0) / (x * x).sum(0)


def bootstrap_slopes(y, x, mo, n_boot=999, L=12, seed=2026) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    n = y.shape[0]
    est = slopes(y, x, mo)
    B = np.empty((n_boot, y.shape[1]))
    for b in range(n_boot):
        B[b] = slopes(y, x, mo, moving_block_index(n, L, rng))
    return est, B


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def ks_d(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.sort(a), np.sort(b)
    v = np.concatenate([a, b])
    return float(np.max(np.abs(np.searchsorted(a, v, "right") / a.size - np.searchsorted(b, v, "right") / b.size)))


def candidates(P: np.ndarray, lat, lon, months, dmin=20, dmax=60, max_rel=0.05, min_r=0.85, max_ks=0.10):
    """P (T, N). Devuelve lista de (a, b, dist_km, rel_diff, r, ks)."""
    mo = months.astype("datetime64[M]").astype(int) % 12
    ann = P.mean(0) * 12
    Pa = month_demean(P, mo)
    Z = (Pa - Pa.mean(0)) / Pa.std(0)
    C = (Z.T @ Z) / Z.shape[0]
    out = []
    N = P.shape[1]
    for a in range(N):
        d = haversine_km(lat[a], lon[a], lat[a + 1:], lon[a + 1:])
        rel = np.abs(ann[a] - ann[a + 1:]) / ((ann[a] + ann[a + 1:]) / 2)
        r = C[a, a + 1:]
        sel = np.flatnonzero((d >= dmin) & (d <= dmax) & (rel < max_rel) & (r >= min_r))
        for s in sel:
            b = a + 1 + s
            k = ks_d(P[:, a], P[:, b])
            if k <= max_ks:
                out.append((a, b, float(d[s]), float(rel[s]), float(r[s]), k))
    return out


def test_pairs(cands, est, B) -> dict:
    a = np.array([c[0] for c in cands])
    b = np.array([c[1] for c in cands])
    dhat = est[a] - est[b]
    D = B[:, a] - B[:, b]
    se = D.std(0, ddof=1)
    p = (1 + (np.abs(D - dhat[None, :]) >= np.abs(dhat)[None, :]).sum(0)) / (B.shape[0] + 1)
    return {"a": a, "b": b, "delta": dhat, "se": se, "z": dhat / se, "p": p, "q": bh_fdr(p),
            "ic95": np.percentile(D, [2.5, 97.5], axis=0)}


def surrogate_fpr(yA, yB, xA, xB, mo, n_sur=300, n_boot=199, L=12, alpha=0.05, seed=2026) -> dict:
    """Tasa de falsos positivos del test cuando la eficiencia verdadera es IGUAL en las dos celdas."""
    rng = np.random.default_rng(seed)
    n = yA.size
    eA = slopes(yA[:, None], xA[:, None], mo)[0]
    eB = slopes(yB[:, None], xB[:, None], mo)[0]
    rA, rB = yA - eA * xA, yB - eB * xB
    common = (eA + eB) / 2
    hits = 0
    for _ in range(n_sur):
        ii = moving_block_index(n, L, rng)     # residuos remuestreados en bloques COMPARTIDOS
        sA = month_demean(common * xA + rA[ii], mo)
        sB = month_demean(common * xB + rB[ii], mo)
        Y = np.column_stack([sA, sB])
        X = np.column_stack([xA, xB])
        est, Bs = bootstrap_slopes(Y, X, mo, n_boot=n_boot, L=L, seed=int(rng.integers(1 << 30)))
        d = est[0] - est[1]
        D = Bs[:, 0] - Bs[:, 1]
        p = (1 + (np.abs(D - d) >= abs(d)).sum()) / (n_boot + 1)
        hits += p < alpha
    return {"n_sustitutos": n_sur, "alfa": alpha, "tasa_falsos_positivos": hits / n_sur,
            "eficiencia_comun_simulada": float(common)}
