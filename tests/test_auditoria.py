"""Pruebas sintéticas (datos inventados, etiquetados como tales) de la lógica de la auditoría:
tasa de cambio de decisión, desplazamientos de un día, acumulados de 48 h y métricas contra estaciones."""

import numpy as np
import pandas as pd

from earthmemory.auditoria import decision, estaciones


def test_flip_unanimous_and_disagree():
    # 4 casos (T=4, n=1) con 3 productos SINTÉTICOS
    a = np.array([[1.], [0.], [1.], [np.nan]])
    b = np.array([[1.], [0.], [0.], [1.]])
    c = np.array([[1.], [1.], [0.], [1.]])
    comp = decision.flip_components({"a": a, "b": b, "c": c})
    r = decision.rates(comp)
    assert r["n_casos"] == 3                       # el caso con NaN no cuenta
    assert r["n_no_unanime"] == 2                  # casos 2 y 3
    assert r["n_alguna_alarma"] == 3
    assert np.isclose(r["tasa_global"], 2 / 3) and np.isclose(r["tasa_condicional"], 2 / 3)


def test_identical_products_never_flip():
    rng = np.random.default_rng(0)
    f = (rng.random((50, 5)) < 0.2).astype(float)
    r = decision.rates(decision.flip_components({"x": f, "y": f.copy()}))
    assert r["n_no_unanime"] == 0 and r["tasa_condicional"] == 0


def test_pair_disagreement_is_one_minus_jaccard():
    a = np.array([1., 1., 0., 0., 1.])
    b = np.array([1., 0., 1., 0., 1.])
    d = decision.pair_disagreement(a, b)
    assert d["n_union"] == 4 and d["n_desacuerdo"] == 2 and np.isclose(d["tasa_condicional"], 0.5)


def test_accum_48h_and_nan():
    P = np.array([10., 95., 10., np.nan, 120.])[:, None]
    s = decision.accum(P, 2)
    assert np.isnan(s[0, 0]) and s[1, 0] == 105 and s[2, 0] == 105
    assert np.isnan(s[3, 0]) and np.isnan(s[4, 0])  # un día faltante anula la ventana


def test_shift_one_day_aligns_lagged_series():
    rng = np.random.default_rng(1)
    x = rng.gamma(0.5, 10, 400)
    y = np.r_[np.nan, x[:-1]]          # y es x con un día de retraso (sintético)
    best = estaciones.best_lag(pd.Series(y), pd.Series(x), lags=(-1, 0, 1))
    assert best["lag_dias"] == 1 and best["r"] > 0.99


def test_trigger_tolerance_recovers_one_day_offset():
    fa = np.zeros((10, 1)); fb = np.zeros((10, 1))
    fa[3] = 1; fb[4] = 1                 # mismo evento, un día de diferencia (sintético)
    assert decision.trigger_agreement(fa, fb, tol=0)["tasa_cambio_decision"] == 1.0
    assert decision.trigger_agreement(fa, fb, tol=1)["tasa_cambio_decision"] == 0.0


def test_year_bootstrap_ci_contains_point():
    years = np.repeat(np.arange(2001, 2025), 12)
    num = (np.arange(years.size) % 3 == 0).astype(float)
    den = np.ones_like(num)
    lo, hi, _ = decision.ratio_bootstrap(num, den, years, B=300)
    assert lo <= num.sum() / den.sum() <= hi


def test_kge_perfect_and_categorical():
    o = pd.Series([0, 60, 120, 5, 0, 55.] * 6)  # 36 días sintéticos (metrics pide >= 30)
    m = estaciones.metrics(o, o)
    assert np.isclose(m["kge"], 1) and np.isclose(m["sesgo_rel"], 0)
    assert m["pod_50"] == 1 and m["far_50"] == 0 and m["csi_100"] == 1
