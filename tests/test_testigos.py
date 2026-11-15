"""Pruebas con datos SINTÉTICOS (etiquetados así) del motor de testigos: API, modelos anidados, pares y umbral."""

import numpy as np
import pandas as pd

from earthmemory.testigos import memoria, pares, umbral


# ------------------------------------------------------------------ API (sintético)

def test_api_impulso_y_constante():
    P = np.zeros(120)
    P[40] = 10.0
    A = memoria.api_window(P, 0.9, 30)
    assert np.isnan(A[:29]).all()
    assert np.isclose(A[40], 10.0)
    assert np.isclose(A[40 + 29], 10.0 * 0.9 ** 29)
    assert A[40 + 30] == 0.0                       # la lluvia sale de la ventana
    C = memoria.api_window(np.ones(200), 0.85, 60)
    assert np.isclose(C[-1], (1 - 0.85 ** 60) / (1 - 0.85))


def test_api_columnas_independientes_y_mensual():
    P = np.random.default_rng(0).gamma(0.5, 8, size=(400, 3))
    A = memoria.api_window(P, 0.95, 90)
    for c in range(3):
        assert np.allclose(A[:, c], memoria.api_window(P[:, c], 0.95, 90), equal_nan=True)
    Pm = np.arange(1, 13, dtype=float)
    Am = memoria.api_monthly(Pm, 0.9, 90)
    assert np.isnan(Am[:2]).all()
    w = [0.9 ** (30 * j + 15) for j in range(3)]
    assert np.isclose(Am[5], w[0] * 6 + w[1] * 5 + w[2] * 4)


def test_z_por_mes():
    idx = pd.date_range("2001-01-01", periods=120, freq="MS")
    df = pd.DataFrame({"a": np.arange(120.0) + 100 * idx.month}, index=idx)
    z = memoria.z_by_month(df)
    assert np.allclose(z.groupby(idx.month).mean().to_numpy(), 0, atol=1e-12)


# ------------------------------------------------------------------ modelos anidados (sintético)

def _synth(n=600, soil_effect=0.0, seed=1):
    rng = np.random.default_rng(seed)
    year = rng.integers(2001, 2025, n)
    rain = rng.normal(size=n)
    soil = 0.9 * rain + 0.3 * rng.normal(size=n)        # el 'suelo' es lluvia filtrada + ruido
    sev = rng.normal(size=n)
    own = soil - 0.9 * rain                              # parte del suelo que NO viene de la lluvia
    y = 0.5 * rain + soil_effect * own / own.std() + 0.2 * sev + rng.normal(scale=0.5, size=n)
    return pd.DataFrame({"y": y, "rain": rain, "soil": soil, "sev": sev, "anio_cluster": year,
                         "mes": rng.integers(1, 13, n)})


def test_anidado_memoria_de_lluvia():
    d = _synth(soil_effect=0.0)
    r = memoria.nested(d, "y", ["sev"], ["mes"], ["rain"], "soil")
    assert r["r2p_suelo_dado_lluvia"] < 0.01           # el suelo no añade nada
    assert r["r2p_lluvia_dado_suelo"] > 0.02
    assert r["r2p_suelo_solo"] > 0.2                   # ...aunque solo, el suelo 'parece' fuerte
    assert abs(r["beta_suelo_M3"]) < 0.1
    assert r["varianza_comun"] > 0.2


def test_anidado_memoria_propia_del_suelo():
    d = _synth(soil_effect=0.4, seed=2)
    b = memoria.nested_boot(d, "y", ["sev"], ["mes"], ["rain"], "soil", B=200, seed=3)
    assert b["r2p_suelo_dado_lluvia"] > 0.05
    lo, hi = b["beta_suelo_M3_ic95"]
    assert lo > 0 and b["p_beta_suelo_M3"] < 0.01


def test_veredicto():
    row = pd.Series({"beta_suelo_M3": 0.05, "beta_suelo_M3_ic95": [-0.1, 0.2], "q_beta_suelo_M3": 0.6})
    assert memoria.verdict(row, 0.46) == "se cae"
    row = pd.Series({"beta_suelo_M3": 0.15, "beta_suelo_M3_ic95": [0.05, 0.25], "q_beta_suelo_M3": 0.01})
    assert memoria.verdict(row, 0.46) == "se debilita"
    row = pd.Series({"beta_suelo_M3": 0.40, "beta_suelo_M3_ic95": [0.2, 0.6], "q_beta_suelo_M3": 0.001})
    assert memoria.verdict(row, 0.46) == "sostiene"


# ------------------------------------------------------------------ pares (sintético)

def _serie(b, n=1200, seed=0):
    rng = np.random.default_rng(seed)
    mi = np.sort(rng.integers(0, 117, n))
    x = rng.gamma(0.6, 6, n)
    c = rng.uniform(0.1, 0.4, n)
    y = b * x - 0.3 * c + 0.01 * np.sin(mi % 12) + rng.normal(scale=0.02, size=n)
    return pares.Serie(y, x, c, mi % 12, mi)


def test_pendiente_recupera_valor():
    s = _serie(0.004)
    assert abs(pares.slope(s) - 0.004) < 3e-4


def test_par_distinto_y_par_igual():
    A, B = _serie(0.004, seed=1), _serie(0.002, seed=2)
    r = pares.test_pair(A, B, n_boot=299)
    assert r["delta"] > 0 and r["p"] < 0.01 and r["delta_ic95"][0] > 0
    A2, B2 = _serie(0.003, seed=3), _serie(0.003, seed=4)
    r2 = pares.test_pair(A2, B2, n_boot=299)
    assert r2["delta_ic95"][0] < 0 < r2["delta_ic95"][1]


def test_eventos_suman_lluvia_entre_pasos():
    days = np.arange(np.datetime64("2020-01-01"), np.datetime64("2020-01-11"))
    rain = np.arange(10, dtype=float)                   # día k llueve k mm (fechado a las 18 UTC)
    t = np.array([np.datetime64("2020-01-02T10"), np.datetime64("2020-01-03T22"), np.datetime64("2020-01-05T10")])
    X = np.array([0.20, 0.25, 0.22])
    s = pares.event_series(t, X, days, rain)
    assert np.allclose(s.y, [0.05, -0.03])
    assert np.allclose(s.x, [1 + 2, 3])                  # (2-ene 10h, 3-ene 22h] → días 2 y 3; luego día 4


# ------------------------------------------------------------------ umbral (sintético)

def test_umbral_agrupado_con_huecos():
    rng = np.random.default_rng(5)
    T, C = 240, 30
    mo = np.arange(T) % 12
    F = rng.uniform(0, 1, (T, C))
    PA = rng.normal(0, 50, (T, C))
    th = 0.6
    eff = 0.3 - 0.5 * np.clip(F - th, 0, None) / (1 - th) * 0.5
    Y = eff * PA + rng.normal(0, 3, (T, C))
    Y[rng.uniform(size=(T, C)) < 0.15] = np.nan          # huecos como en SMAP
    r = umbral.pooled(Y, PA, F, mo, n_boot=40, L=12)
    assert abs(r["theta"] - th) < 0.08
    assert r["b5_excluye_0"] and r["b5"] < 0
    Y2 = 0.3 * PA + rng.normal(0, 3, (T, C))
    r2 = umbral.pooled(Y2, PA, F, mo, n_boot=40, L=12)
    assert not r2["b5_excluye_0"] or abs(r2["b5"]) < 0.05
