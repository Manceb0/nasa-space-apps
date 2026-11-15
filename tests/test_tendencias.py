"""Comprobaciones sintéticas (datos SINTÉTICOS, generados aquí) del motor de tendencias P0."""

from __future__ import annotations

import numpy as np
import pytest

from earthmemory.tendencias import estadistica as st
from earthmemory.tendencias import indices as ix


def test_indices_serie_conocida():
    # 20 días: 3 húmedos, 12 secos, 2 húmedos, 3 secos
    p = np.array([5, 25, 60] + [0.2] * 12 + [1.0, 10] + [0, 0, 0.5], float)[:, None]
    thr = {95: np.array([30.0]), 99: np.array([55.0])}
    r = ix.block_indices(p, thr)
    assert r["PRCPTOT"][0] == pytest.approx(5 + 25 + 60 + 1 + 10)
    assert r["SDII"][0] == pytest.approx(101 / 5)
    assert r["R20mm"][0] == 2 and r["R50mm"][0] == 1
    assert r["Rx1day"][0] == 60
    assert r["Rx5day"][0] == pytest.approx(5 + 25 + 60 + 0.2 + 0.2)
    assert r["CDD"][0] == 12 and r["CWD"][0] == 3
    assert r["R95pTOT"][0] == 60 and r["R99pTOT"][0] == 60
    assert r["RACHAS10"][0] == 1 and r["RACHAS15"][0] == 0


def test_rachas_abiertas_y_nan():
    p = np.zeros((16, 2))
    p[0, :] = 5
    p[3, 1] = np.nan
    r = ix.block_indices(p, {95: np.array([9.0, 9.0]), 99: np.array([9.0, 9.0])})
    assert r["CDD"][0] == 15 and r["RACHAS15"][0] == 1  # racha abierta al final cuenta
    assert np.isnan(r["CDD"][1])                         # día faltante -> índice NaN


def test_estacion_seca_cruza_el_anio():
    days = np.arange(np.datetime64("2001-01-01"), np.datetime64("2003-01-01"))
    b = ix.period_blocks(days, "seca", (2001, 2002))
    assert [y for y, _ in b] == [2002]
    d = days[b[0][1]]
    assert str(d[0]) == "2001-12-01" and str(d[-1]) == "2002-04-30"


def test_theil_sen_pendiente_conocida():
    x = np.arange(2001, 2025, dtype=float)
    rng = np.random.default_rng(1)
    Y = 0.3 * (x - 2001)[None, :] + rng.normal(0, 0.05, (50, x.size))
    r = st.trend_rows(Y, x)
    assert np.allclose(r["pendiente"], 0.3, atol=0.01)
    assert np.all((r["ic_inf"] <= 0.3) & (r["ic_sup"] >= 0.3) | (np.abs(r["pendiente"] - 0.3) < 0.01))
    exact = st.trend_rows((2.0 * x)[None, :], x)
    assert exact["pendiente"][0] == pytest.approx(2.0) and exact["p"][0] < 1e-6


def test_mk_ruido_blanco_fpr_cerca_de_alfa():
    rng = np.random.default_rng(2026)
    x = np.arange(24, dtype=float)
    r = st.trend_rows(rng.standard_normal((4000, 24)), x)
    fpr = np.mean(r["p"] < 0.05)
    assert 0.02 <= fpr <= 0.065, fpr
    fpr0 = np.mean(r["p_sin_correccion"] < 0.05)
    assert 0.03 <= fpr0 <= 0.07, fpr0


def test_mk_ar1_corrige():
    rng = np.random.default_rng(5)
    n, phi = 24, 0.6
    E = rng.standard_normal((3000, n + 50))
    Y = np.zeros_like(E)
    for t in range(1, E.shape[1]):
        Y[:, t] = phi * Y[:, t - 1] + E[:, t]
    Y = Y[:, 50:]
    r = st.trend_rows(Y, np.arange(n, dtype=float))
    assert np.mean(r["p"] < 0.05) < np.mean(r["p_sin_correccion"] < 0.05)


def test_varianza_con_empates():
    y = np.array([[1, 1, 2, 2, 2, 3, 4, 5, 5, 6, 7, 8]], float)
    r = st._complete_rows(y, np.arange(12.0), hamed_rao=False)
    n = 12
    var = (n * (n - 1) * (2 * n + 5) - (2 * 1 * 9 + 3 * 2 * 11 + 2 * 1 * 9)) / 18
    assert r["Z"][0] == pytest.approx((r["S"][0] - 1) / np.sqrt(var))


def test_constante_no_significativa():
    r = st.trend_rows(np.zeros((1, 24)), np.arange(24.0))
    assert r["p"][0] == 1.0 and r["pendiente"][0] == 0


def test_spi_aproximadamente_normal():
    rng = np.random.default_rng(3)
    months = np.arange(np.datetime64("1901-01"), np.datetime64("2001-01"))
    M = rng.gamma(2.0, 50.0, size=(months.size, 3))
    s = ix.spi(M, months, 3)
    v = s[np.isfinite(s)]
    assert abs(v.mean()) < 0.1 and abs(v.std() - 1) < 0.1


def test_metricas_de_sequia():
    months = np.arange(np.datetime64("2002-01"), np.datetime64("2004-01"))
    S = np.zeros((24, 1))
    S[[2, 3, 4], 0] = -1.5          # evento de 3 meses en 2002
    S[[11, 12], 0] = -1.2           # evento dic-2002 -> ene-2003 (empieza en 2002)
    S[20, 0] = -2.0                 # evento de 1 mes en 2003
    m = ix.drought_metrics(S, months, (2002, 2003))
    assert list(m["MESES"][1][:, 0]) == [4, 2]
    assert list(m["EVENTOS"][1][:, 0]) == [2, 1]
    assert m["DURAC"][1][0, 0] == pytest.approx(2.5) and m["DURAC"][1][1, 0] == 1
    assert m["SEVER"][1][0, 0] == pytest.approx(4.5 + 1.2)


def test_clases_de_confianza():
    c = st.confidence_class(np.array([1, 1, 1, 0, 0]), np.array([1, 0, 1, 0, 1]),
                            np.array([1, 1, 1, 1, -1.0]), np.array([1, 1, -1, -1, 1.0]))
    assert list(c) == ["robusta", "consistente", "en disputa", "sin señal detectable", "en disputa"]


def test_mdt_coherente_con_formula_analitica():
    n = 24
    c = st.mdt_factor(n, n_sim=1500)
    analitico = 2.80 * np.sqrt(12 / (n * (n ** 2 - 1)))
    assert 0.8 * analitico < c < 1.35 * analitico


def test_totales_mensuales_nan_no_contamina_otras_celdas():
    days = np.arange(np.datetime64("2001-01-01"), np.datetime64("2001-03-01"))
    X = np.ones((days.size, 2))
    X[5, 1] = np.nan                       # una celda con un día faltante (p. ej. mar en CHIRPS)
    months, M = ix.monthly_totals(X, days)
    assert M[0, 0] == 31 and M[1, 0] == 28
    assert np.isnan(M[0, 1]) and M[1, 1] == 28
