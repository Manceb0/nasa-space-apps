"""Pruebas sintéticas del caso Yuna: puntuación de disparadores, antecedente sin fuga, topología de cuencas, API."""

import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from earthmemory.yuna import analisis as A
from earthmemory.yuna import cuencas as C
from earthmemory.yuna import series as S


def _dias(y0=2001, y1=2004):
    return pd.date_range(f"{y0}-01-01", f"{y1}-12-31", freq="D")


def test_antecedente_no_incluye_lluvia_del_evento():
    idx = _dias(2001, 2001)
    p = pd.Series(0.0, index=idx)
    p["2001-06-10"] = 100.0
    ant = A.antecedente(p, 30, lag=2)
    assert ant["2001-06-10"] == 0 and ant["2001-06-11"] == 0     # el día del evento y el siguiente: fuera
    assert ant["2001-06-12"] == 100                                # entra 2 días después
    assert ant["2001-07-11"] == 100 and ant["2001-07-12"] == 0     # sale tras 30 días


def test_episodios_separa_por_hueco():
    idx = _dias(2001, 2001)
    t = pd.Series(False, index=idx)
    t[["2001-03-01", "2001-03-02", "2001-03-05", "2001-03-20"]] = True
    ep = A.episodios(t, gap=3)
    assert len(ep) == 2 and ep[0] == (pd.Timestamp("2001-03-01"), pd.Timestamp("2001-03-05"))


def test_puntuar_perfecto_y_falsas_alarmas():
    idx = _dias()
    vent = [(pd.Timestamp("2002-05-10"), pd.Timestamp("2002-05-12"), "e1"),
            (pd.Timestamp("2003-10-01"), pd.Timestamp("2003-10-03"), "e2")]
    t = pd.Series(False, index=idx)
    t["2002-05-09"] = True            # dentro de la tolerancia de 2 días
    t["2003-10-02"] = True
    r = A.puntuar(t, vent, (2001, 2004))["tot"]
    assert r == {"h": 2, "m": 0, "fa": 0, "ep": 2}
    m = A.metricas_ep(r["h"], r["m"], r["fa"], r["ep"])
    assert m["POD"] == 1 and m["FAR"] == 0 and m["CSI"] == 1
    t["2004-01-15"] = True            # falsa alarma
    t["2003-10-02"] = False           # un fallo
    r = A.puntuar(t, vent, (2001, 2004))["tot"]
    assert r == {"h": 1, "m": 1, "fa": 1, "ep": 2}
    m = A.metricas_ep(r["h"], r["m"], r["fa"], r["ep"])
    assert m["POD"] == 0.5 and m["FAR"] == 0.5 and m["CSI"] == pytest.approx(1 / 3)


def test_puntuar_respeta_periodo():
    idx = _dias()
    vent = [(pd.Timestamp("2002-05-10"), pd.Timestamp("2002-05-12"), "e1")]
    t = pd.Series(False, index=idx)
    t["2002-05-10"] = True
    assert A.puntuar(t, vent, (2003, 2004))["tot"] == {"h": 0, "m": 0, "fa": 0, "ep": 0}


def test_bootstrap_ic_contiene_estimacion_y_es_determinista():
    por = {y: {"h": 1, "m": 1, "fa": 1, "ep": 2} for y in range(2001, 2011)}
    ci1, ci2 = A.bootstrap(por, b=300), A.bootstrap(por, b=300)
    assert ci1 == ci2
    assert ci1["POD"][0] <= 0.5 <= ci1["POD"][1]


def test_bloques3():
    idx = _dias(2001, 2001)
    vent = [(pd.Timestamp("2001-01-04"), pd.Timestamp("2001-01-05"), "e")]
    t = pd.Series(False, index=idx)
    t["2001-01-06"] = True            # mismo bloque (días 4-6)
    t["2001-02-01"] = True            # bloque sin evento
    b = A.bloques3(t, vent, (2001, 2001))
    assert (b["h"], b["m"], b["fa"]) == (1, 0, 1)


def test_auc_extremos():
    assert A.auc([5, 6, 7], [1, 2, 3]) == 1.0
    assert A.auc([1, 2], [5, 6]) == 0.0


def test_topologia_aguas_arriba():
    recs = [{"HYBAS_ID": 1, "NEXT_DOWN": 0}, {"HYBAS_ID": 2, "NEXT_DOWN": 1}, {"HYBAS_ID": 3, "NEXT_DOWN": 2},
            {"HYBAS_ID": 4, "NEXT_DOWN": 0}, {"HYBAS_ID": 5, "NEXT_DOWN": 1}]
    assert C.upstream(recs, 1) == {1, 2, 3, 5}
    assert C.upstream(recs, 2) == {2, 3}
    assert C.upstream(recs, 4) == {4}


def test_pesos_de_celda_y_media_ponderada():
    lat = np.array([19.05, 19.15]); lon = np.array([-70.05, -69.95])
    w = S.cell_weights(lat, lon, 0.1, box(-70.1, 19.0, -70.0, 19.2)).ravel()   # solo la columna oeste
    assert w[0] > 0 and w[2] > 0 and w[1] == 0 and w[3] == 0
    X = np.array([[10.0, 99.0, 20.0, 99.0], [np.nan, 0.0, 20.0, 0.0]])
    m = S.wmean(X, w)
    assert m[0] == pytest.approx((10 * w[0] + 20 * w[2]) / (w[0] + w[2]))
    assert np.isnan(m[1])                     # falta la mitad del peso: no se informa una media de media cuenca
    X[1, 0] = 0.0
    assert S.wmean(X, w)[1] == pytest.approx(20 * w[2] / (w[0] + w[2]))


def test_pct_mes_rango():
    idx = _dias(2001, 2003)
    s = pd.Series(np.arange(len(idx), dtype=float), index=idx)
    p = A.pct_mes(s)
    assert p.min() > 0 and p.max() == 100
