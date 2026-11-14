"""Auditoría Recovery Integrity con DATOS SINTÉTICOS."""

import pandas as pd

from phantom.audit import audit_recovery
from phantom.recovery import robust_seasonal_z
from tests.synthetic import signal

EV_START, EV_END = "2015-04-01", "2015-10-31"
STOP = "2016-10-31"


def z(s, period):
    return robust_seasonal_z(pd.Series(s.index), s.reset_index(drop=True), period)


def signals(green_end, func_end, depth=0.15, seed=1):
    g = signal(16, [(EV_START, green_end, depth)], seed=seed)
    e = signal(16, [(EV_START, green_end, depth)], seed=seed + 10)
    f1 = signal(8, [(EV_START, func_end, depth)], seed=seed + 20)
    f2 = signal(8, [(EV_START, func_end, depth)], seed=seed + 30)
    return {"ndvi": z(g, 16), "evi": z(e, 16), "gpp_modelo": z(f1, 8), "lst_menos_aire": z(f2, 8)}


def test_consistent_when_all_signals_return_together():
    a = audit_recovery(signals("2015-12-15", "2015-12-20"), EV_START, EV_END, STOP)
    assert a["veredicto"] == "consistente"
    assert a["estabilidad"] >= 0.6


def test_phantom_when_function_lags_far_behind():
    a = audit_recovery(signals("2015-12-15", "2016-05-01"), EV_START, EV_END, STOP)
    assert a["categoria_principal"] == "fantasma"


def test_green_late_when_function_returns_first():
    a = audit_recovery(signals("2016-05-01", "2015-12-15"), EV_START, EV_END, STOP)
    assert a["categoria_principal"] == "verdor_tarde"


def test_collision_censors_the_claim():
    nxt = "2016-02-01"
    a = audit_recovery(signals("2015-12-15", "2016-06-01"), EV_START, EV_END, nxt, next_event_start=nxt)
    assert a["veredicto"] == "censurada" and a["colision"]


def test_no_impact():
    a = audit_recovery(signals("2015-12-15", "2016-03-01", depth=0.0005), EV_START, EV_END, STOP)
    assert a["veredicto"] == "sin_impacto"


def test_poor_quality_is_inconclusive():
    s = signals("2015-12-15", "2016-05-01")
    s = {k: v[(v.index < "2015-03-01") | (v.index > "2015-09-30")] for k, v in s.items()}  # sin datos en la sequía
    a = audit_recovery(s, EV_START, EV_END, STOP)
    assert a["veredicto"] in ("inconclusa", "sin_impacto")
    if a["veredicto"] == "inconclusa":
        assert a["motivo_inconclusa"] == "calidad"


def test_invisible_stress_when_only_function_drops():
    g = signal(16, [], seed=3)
    e = signal(16, [], seed=4)
    f = signal(8, [(EV_START, "2016-01-01", 0.15)], seed=5)
    s = {"ndvi": z(g, 16), "evi": z(e, 16), "gpp_modelo": z(f, 8), "lst_menos_aire": z(f, 8)}
    a = audit_recovery(s, EV_START, EV_END, STOP)
    assert a["categoria_principal"] == "estres_invisible"


def test_late_dip_is_not_phantom():
    g = signal(16, [(EV_START, "2015-09-01", 0.15)], seed=6)
    f = signal(8, [("2015-11-01", "2016-02-01", 0.15)], seed=7)
    s = {"ndvi": z(g, 16), "evi": z(g, 16), "gpp_modelo": z(f, 8), "lst_menos_aire": z(signal(8, [], seed=8), 8)}
    a = audit_recovery(s, EV_START, EV_END, STOP)
    assert a["categoria_principal"] == "caida_posterior"


def test_gpp_only_drop_is_model_only_not_invisible_stress():
    g = signal(16, [], seed=13)
    f = signal(8, [(EV_START, "2016-01-01", 0.15)], seed=14)
    s = {"ndvi": z(g, 16), "evi": z(g, 16), "gpp_modelo": z(f, 8), "lst_menos_aire": z(signal(8, [], seed=15), 8)}
    a = audit_recovery(s, EV_START, EV_END, STOP)
    assert a["categoria_principal"] == "solo_modelo"
