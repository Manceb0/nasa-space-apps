"""Pruebas del cálculo de recuperación con DATOS SINTÉTICOS."""

import pandas as pd
import pytest

from phantom.recovery import event_gap, robust_seasonal_z, robustness_label, sensitivity
from tests.synthetic import signal

EV_START, EV_END = "2015-04-01", "2015-10-31"
STOP = "2016-10-31"


def z_of(s, period):
    return robust_seasonal_z(pd.Series(s.index), s.reset_index(drop=True), period)


def test_known_lag_complete_recovery():
    green = signal(16, [(EV_START, "2015-12-15", 0.15)])
    func = signal(8, [(EV_START, "2016-03-01", 0.15)], seed=2)
    r = event_gap(z_of(green, 16), z_of(func, 8), EV_START, EV_END, STOP)
    assert r["estado"] == "ambos_recuperados"
    assert r["dt_dias"] == pytest.approx(77, abs=16)  # resolución de 16 días


def test_no_difference_gives_near_zero_gap():
    green = signal(16, [(EV_START, "2016-01-10", 0.15)])
    func = signal(8, [(EV_START, "2016-01-10", 0.15)], seed=3)
    r = event_gap(z_of(green, 16), z_of(func, 8), EV_START, EV_END, STOP)
    assert r["estado"] == "ambos_recuperados"
    assert abs(r["dt_dias"]) <= 32  # precisión: ±2 compuestos de 16 días


def test_incomplete_function_recovery_is_censored_with_lower_bound():
    green = signal(16, [(EV_START, "2015-12-15", 0.15)])
    func = signal(8, [(EV_START, "2017-06-01", 0.15)], seed=4)  # no vuelve antes de STOP
    r = event_gap(z_of(green, 16), z_of(func, 8), EV_START, EV_END, STOP)
    assert r["estado"] == "funcion_censurada"
    assert r["dt_es_cota_inferior"]
    assert r["dt_dias"] > 250


def test_missing_values_still_recover():
    green = signal(16, [(EV_START, "2015-12-15", 0.15)], missing_frac=0.3, seed=5)
    func = signal(8, [(EV_START, "2016-03-01", 0.15)], missing_frac=0.3, seed=6)
    r = event_gap(z_of(green, 16), z_of(func, 8), EV_START, EV_END, STOP)
    assert r["estado"] == "ambos_recuperados"
    assert r["dt_dias"] == pytest.approx(77, abs=48)


def test_overlapping_next_event_censors_recovery():
    green = signal(16, [(EV_START, "2015-12-01", 0.15)])
    func = signal(8, [(EV_START, "2016-06-01", 0.15)], seed=7)
    next_event_start = "2016-03-01"  # la siguiente sequía corta la ventana
    r = event_gap(z_of(green, 16), z_of(func, 8), EV_START, EV_END, next_event_start)
    assert r["estado"] == "funcion_censurada"


def test_no_impact_detected():
    green = signal(16, [(EV_START, "2015-12-15", 0.002)])
    func = signal(8, [(EV_START, "2016-03-01", 0.002)], seed=8)
    r = event_gap(z_of(green, 16), z_of(func, 8), EV_START, EV_END, STOP, threshold=-1.0)
    assert r["estado"] in {"sin_impacto", "sin_impacto_verde", "sin_impacto_funcion"}
    assert r["dt_dias"] is None


def test_inverted_signal_hot_canopy_is_negative():
    hot = signal(8, [(EV_START, "2016-01-01", -2.0)], base=30, amp=2, noise=0.1)  # +2 °C
    z = robust_seasonal_z(pd.Series(hot.index), hot.reset_index(drop=True), 8, invert=True)
    assert z[(z.index >= "2015-06-01") & (z.index < "2015-10-01")].mean() < -3


def test_sensitivity_and_robust_label():
    green = signal(16, [(EV_START, "2015-12-15", 0.15)])
    func = signal(8, [(EV_START, "2016-04-01", 0.15)], seed=9)
    gz, fz = z_of(green, 16), z_of(func, 8)
    sens = sensitivity({"ndvi": gz, "evi": gz}, fz, EV_START, EV_END, STOP)
    assert len(sens) == 2 * 3 * 3
    prim = event_gap(gz, fz, EV_START, EV_END, STOP)
    lab = robustness_label(sens, prim["dt_dias"])
    assert lab["etiqueta"] == "ROBUSTO"


def test_robust_label_needs_enough_combinations():
    sens = pd.DataFrame({"estado": ["ambos_recuperados"] * 3, "dt_dias": [40.0, 50.0, 60.0]})
    assert robustness_label(sens, 50.0)["etiqueta"] == "SIN DATOS SUFICIENTES"


def test_robust_label_flags_sign_flips():
    sens = pd.DataFrame({"estado": ["ambos_recuperados"] * 10,
                         "dt_dias": [40, 50, -30, -20, 60, -10, 45, -40, 35, -25]})
    assert robustness_label(sens, 40.0)["etiqueta"] == "SENSIBLE A SUPUESTOS"
