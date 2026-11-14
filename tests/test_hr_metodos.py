"""Pruebas de earthmemory/hr. TODO lo que usan son DATOS SINTÉTICOS DE PRUEBA generados aquí con semillas fijas;
nada de esto entra en results/ ni en figures/."""

from __future__ import annotations

import numpy as np
import pytest

from earthmemory.hr import changepoints, drivers, pair, thresholds
from earthmemory.hr.common import GRID, RGrid, bh_fdr, conservative_regrid, overlap_matrix
from earthmemory.hr.download import ease2_xy

SYNTHETIC = "DATOS SINTETICOS DE PRUEBA"


# ------------------------------------------------------------------ remapeo conservativo

def test_regrid_constant_and_block_mean():
    g_src = RGrid(-72.10, 17.40, 0.025, 156, 108)          # 2×2 celdas por celda destino
    rng = np.random.default_rng(0)
    a = rng.normal(size=(g_src.ny, g_src.nx))              # sintético
    out = conservative_regrid(a, g_src.lat_edges, g_src.lon_edges, GRID)
    # media ponderada por área de cada bloque 2×2 (pesos sin φ por fila)
    w = np.diff(np.sin(np.radians(g_src.lat_edges)))
    blk = (a * w[:, None]).reshape(GRID.ny, 2, GRID.nx, 2).sum((1, 3)) / w.reshape(GRID.ny, 2).sum(1)[:, None] / 2
    assert np.allclose(out, blk, atol=1e-12)
    c = conservative_regrid(np.full((g_src.ny, g_src.nx), 3.5), g_src.lat_edges, g_src.lon_edges, GRID)
    assert np.allclose(c, 3.5)


def test_regrid_coarse_replicates_and_nan_cover():
    g = RGrid(-72.10, 17.40, 0.25, 16, 11)
    a = np.arange(g.ny * g.nx, dtype=float).reshape(g.ny, g.nx)  # sintético
    out = conservative_regrid(a, g.lat_edges, g.lon_edges, GRID)
    assert out[0, 0] == a[0, 0] and out[0, 4] == a[0, 0] and out[0, 5] == a[0, 1]
    a[0, 0] = np.nan
    out = conservative_regrid(a, g.lat_edges, g.lon_edges, GRID)
    assert np.isnan(out[0, 0])


def test_overlap_rows_sum_to_cell_area():
    W = overlap_matrix(np.linspace(0, 1, 7), np.linspace(0, 1, 4), lat=False)
    assert np.allclose(W.sum(1), 1 / 3)


# ------------------------------------------------------------------ umbral (regresión segmentada)

def _bucket(theta, n=288, seed=1):
    """Serie sintética: eficiencia 0.6 bajo θ y 0.1 sobre θ (saturación), con efecto de mes."""
    rng = np.random.default_rng(seed)
    months = np.arange(np.datetime64("2001-01"), np.datetime64("2001-01") + np.timedelta64(n, "M"))
    mo = months.astype(int) % 12
    Pa = rng.normal(0, 60, n)
    f = np.clip(rng.beta(2, 2, n), 0, 1)
    eff = np.where(f < theta, 0.6, 0.6 - 2.5 * (f - theta))
    y = eff * Pa + 5 * np.sin(2 * np.pi * mo / 12) + rng.normal(0, 8, n)
    return y, Pa, f, mo


def test_threshold_detected_with_ci():
    y, Pa, f, mo = _bucket(0.55)
    r = thresholds.fit_cell(y, Pa, f, mo, n_boot=199, rng=np.random.default_rng(3))
    assert r["p"] < 0.01 and r["dBIC"] > 2
    assert abs(r["theta"] - 0.55) < 0.08
    lo, hi = thresholds.theta_ci(*r["_ci_args"], n_ci=60, rng=np.random.default_rng(4))
    assert lo <= r["theta"] <= hi and hi - lo < 0.3


def test_threshold_null_not_significant():
    rng = np.random.default_rng(7)
    n = 288
    mo = np.arange(n) % 12
    Pa, f = rng.normal(0, 60, n), rng.uniform(0, 1, n)
    y = 0.4 * Pa - 0.2 * Pa * f + rng.normal(0, 8, n)       # lineal: sin quiebre (sintético)
    r = thresholds.fit_cell(y, Pa, f, mo, n_boot=199, rng=np.random.default_rng(5))
    assert r["p"] > 0.05


# ------------------------------------------------------------------ Pettitt

def test_pettitt_finds_shift_and_respects_null():
    rng = np.random.default_rng(11)
    n = 288
    X = rng.normal(size=(n, 3))
    X[150:, 0] += 1.2                                       # cambio de nivel sintético en la columna 0
    for t in range(1, n):                                   # AR(1) sin cambio en la columna 2
        X[t, 2] = 0.8 * X[t - 1, 2] + rng.normal()
    r = changepoints.pettitt_grid(X, n_boot=199, L=12, seed=1)
    assert abs(int(r["k"][0]) - 149) <= 3 and r["p"][0] < 0.01
    assert r["p"][1] > 0.05
    # la p asintótica ignora la persistencia; la de bloques debe ser mayor o igual en la serie AR(1)
    assert r["p"][2] >= r["p_asintotica"][2] - 1e-12


def test_bh_matches_definition():
    p = np.array([0.01, 0.04, 0.03, 0.2, np.nan])
    q = bh_fdr(p)
    assert np.isnan(q[-1]) and q[0] == pytest.approx(0.04) and q[3] == pytest.approx(0.2)


# ------------------------------------------------------------------ par y sustitutos

def test_pair_surrogate_fpr_close_to_alpha():
    rng = np.random.default_rng(21)
    n = 240
    mo = np.arange(n) % 12
    x = rng.normal(0, 50, n)
    xa, xb = x + rng.normal(0, 10, n), x + rng.normal(0, 10, n)
    ya, yb = 0.3 * xa + rng.normal(0, 10, n), 0.3 * xb + rng.normal(0, 10, n)
    r = pair.surrogate_fpr(ya, yb, xa, xb, mo, n_sur=80, n_boot=99, seed=2)
    assert r["tasa_falsos_positivos"] <= 0.15


def test_pair_detects_true_difference():
    rng = np.random.default_rng(22)
    n = 288
    months = np.arange(np.datetime64("2001-01"), np.datetime64("2001-01") + np.timedelta64(n, "M"))
    P = np.abs(rng.normal(100, 50, (n, 1))) + np.zeros((1, 2))
    S = np.column_stack([np.cumsum(0.5 * (P[:, 0] - 100)), np.cumsum(0.1 * (P[:, 1] - 100))])
    S += rng.normal(0, 3, S.shape)
    y, x, mo = pair.efficiency_inputs(P, S, months)
    est, B = pair.bootstrap_slopes(y, x, mo, n_boot=199, seed=3)
    t = pair.test_pairs([(0, 1, 30.0, 0.0, 1.0, 0.0)], est, B)
    assert t["p"][0] < 0.01 and t["delta"][0] > 0.3


# ------------------------------------------------------------------ factores y proyección

def test_ridge_spatial_cv_recovers_sign():
    rng = np.random.default_rng(31)
    ii, jj = np.meshgrid(np.arange(30), np.arange(30), indexing="ij")
    ii, jj = ii.ravel(), jj.ravel()
    lat, lon = 17.5 + ii * 0.05, -72 + jj * 0.05
    X = rng.normal(size=(ii.size, 3))
    y = 0.8 * X[:, 0] - 0.3 * X[:, 1] + rng.normal(0, 0.5, ii.size)
    d = drivers.analyse(y, X, ["a", "b", "c"], lat, lon, ii, jj, n_boot=50)
    assert d["coef"]["a"]["beta_z"] > 0.5 and d["coef"]["a"]["excluye_0"]
    assert d["r2_cv_espacial"] > 0.5


def test_ease2_projection_extent():
    x, y = ease2_xy(np.array([0.0, 180.0]), np.array([0.0, 85.0445664]))
    assert x[0] == pytest.approx(0, abs=1e-6) and y[0] == pytest.approx(0, abs=1e-6)
    assert x[1] == pytest.approx(17367530.45, abs=1.0)      # borde de la rejilla EASE-Grid 2.0 global
    assert y[1] == pytest.approx(7314540.83, abs=50.0)
