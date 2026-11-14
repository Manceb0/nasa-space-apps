"""Tendencias de la herramienta de detective, con DATOS SINTÉTICOS."""

import numpy as np
import pandas as pd
import pytest

from phantom import trends


def monthly(slope_per_year=0.0, noise=0.3, amp=10.0, seed=0):
    idx = pd.date_range("2001-01-01", "2024-12-01", freq="MS")
    rng = np.random.default_rng(seed)
    t = (idx.year - 2001) + (idx.month - 1) / 12
    v = 50 + amp * np.sin(2 * np.pi * idx.month / 12) + slope_per_year * t + rng.normal(0, noise, idx.size)
    return pd.Series(v, index=idx)


def test_known_trend_is_recovered_and_significant():
    a = trends.analyze(monthly(slope_per_year=0.2))
    full = a["completa"]
    assert full["pendiente_decada"] == pytest.approx(2.0, abs=0.2)
    assert full["veredicto"] == "sube"
    assert full["ic95_decada"][0] < 2.0 < full["ic95_decada"][1]


def test_seasonal_cycle_alone_is_not_a_trend():
    a = trends.analyze(monthly(slope_per_year=0.0, noise=0.3, amp=40))
    assert a["completa"]["veredicto"] in ("sin_evidencia", "indicio")
    assert a["amplitud_estacional"] > 70  # el ciclo es grande, pero no es tendencia


def test_windows_cover_all_spans_of_10_years_or_more():
    a = trends.analyze(monthly(slope_per_year=0.1))
    spans = {(w["inicio"], w["fin"]) for w in a["ventanas"]}
    assert len(spans) == sum(25 - L for L in range(10, 25))  # 24 años: 120 ventanas
    assert all(f - i + 1 >= 10 for i, f in spans)


def test_no_significance_is_reported_with_its_interval():
    a = trends.analyze(monthly(slope_per_year=0.0, noise=3.0, seed=4))
    full = a["completa"]
    assert full["veredicto"] in ("sin_evidencia", "indicio")
    lo, hi = full["ic95_decada"]
    assert lo < 0 < hi  # el IC dice qué cambios no se pueden descartar


def test_misleading_windows_contradict_full_series():
    a = trends.analyze(monthly(slope_per_year=0.0, noise=3.0, seed=11))
    for w in a["ventanas_que_enganan"]:
        assert w["veredicto"] in ("sube", "baja")
        assert w["veredicto"] != a["completa"]["veredicto"]


def test_ar1_correction_reduces_false_positives():
    """Ruido AR(1) sin tendencia: el p corregido rechaza menos que el simple (DATOS SINTÉTICOS)."""
    from phantom import stats
    rng = np.random.default_rng(7)
    naive = adj = 0
    for _ in range(300):
        e = np.zeros(24)
        for i in range(1, 24):
            e[i] = 0.6 * e[i - 1] + rng.normal()
        r = stats.mann_kendall_ar1(np.arange(24), e)
        naive += r["p"] < 0.05
        adj += r["p_ajustado"] < 0.05
    assert adj < naive
    assert adj / 300 < 0.12
