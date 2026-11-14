"""Pruebas del motor nacional Earth Memory. TODO lo que usan estas pruebas son DATOS SINTÉTICOS DE PRUEBA
(generados aquí con semillas fijas); nada de esto se usa en results/ ni en figures/."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from earthmemory import appeears_hook, boundaries, calibration, earthdata, grid
from earthmemory.nacional import match_episodes_across_products, whiplash_events
from phantom import stats as pstats

SYNTHETIC = "DATOS SINTETICOS DE PRUEBA"


def _ar1(n, phi, rng, cols=1):
    e = rng.normal(size=(n, cols))
    x = np.zeros((n, cols))
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return x


# ------------------------------------------------------------------ Mann-Kendall vectorizado

def test_mk_ar1_matrix_equals_phantom():
    rng = np.random.default_rng(1)
    x = np.arange(2001, 2025, dtype=float)
    Y = rng.normal(size=(20, x.size)) + 0.05 * (x - x.mean())[None, :]  # sintético
    res = calibration.mk_ar1_matrix(Y, x)
    for k in range(Y.shape[0]):
        ref = pstats.mann_kendall_ar1(x, Y[k])
        assert res["p"][k] == pytest.approx(ref["p_ajustado"], rel=1e-9, abs=1e-12)
        assert res["p_simple"][k] == pytest.approx(ref["p"], rel=1e-9, abs=1e-12)
        assert res["S"][k] == ref["S"]


# ------------------------------------------------------------------ sustitutos

def test_phase_surrogate_keeps_spectrum_and_cross_correlation():
    rng = np.random.default_rng(2)
    base = _ar1(288, 0.8, rng)
    R = np.hstack([base, base + 0.3 * rng.normal(size=(288, 1))])  # dos celdas correlacionadas (sintético)
    R -= R.mean(0)
    S = calibration.phase_surrogate(R, np.random.default_rng(3))
    assert np.allclose(np.abs(np.fft.rfft(R, axis=0)), np.abs(np.fft.rfft(S, axis=0)), atol=1e-8)
    assert np.corrcoef(S.T)[0, 1] == pytest.approx(np.corrcoef(R.T)[0, 1], abs=1e-8)
    assert not np.allclose(S, R)


def test_trend_test_is_calibrated_on_null_data():
    """Sin tendencia (AR(1) mensual + ciclo), la tasa empírica de p<0.05 debe rondar el 5 %."""
    rng = np.random.default_rng(4)
    idx = pd.date_range("2001-01-01", "2024-12-01", freq="MS")
    X = _ar1(len(idx), 0.6, rng, cols=40) + 3 * np.sin(2 * np.pi * idx.month.to_numpy() / 12)[:, None]
    df = pd.DataFrame(X, index=idx, columns=[f"c{k}" for k in range(40)])
    summ, cells = calibration.trend_calibration(df, n_surr=150, seed=5)
    assert 0.01 <= summ["tasa_empirica_p05"] <= 0.10
    assert len(cells) == 40 and cells["p_empirico"].between(0, 1).all()


def test_block_surrogate_is_permutation_of_blocks():
    R = np.arange(48, dtype=float)[:, None]
    S = calibration.block_surrogate(R, np.random.default_rng(0), block=12)
    assert S.shape == R.shape and set(S.ravel()) <= set(R.ravel())


# ------------------------------------------------------------------ calibración de pares

def test_inflation_calibration_restores_nominal_rate():
    rng = np.random.default_rng(6)
    z = rng.normal(scale=2.0, size=4000)  # Δ/EE nulo inflado ×2 (sintético)
    null = pd.DataFrame({"respuesta": "R", "metrica": "phi", "z": z,
                         "p": 2 * (1 - __import__("scipy").stats.norm.cdf(np.abs(z)))})
    s = calibration.pair_null_summary(null)
    row = s[s["respuesta"] == "R"].iloc[0]
    assert row["tasa_empirica_p05"] > 0.25
    assert row["factor_inflacion_EE"] == pytest.approx(2.0, rel=0.08)
    assert row["tasa_p05_tras_calibrar"] == pytest.approx(0.05, abs=0.015)
    tests = pd.DataFrame({"respuesta": ["R"], "metrica": ["phi"], "delta": [4.0], "ee_boot": [1.0]})
    assert calibration.calibrated_p(tests, null).iloc[0] == pytest.approx(0.0455, abs=0.01)


# ------------------------------------------------------------------ rejillas y pesos

def _square_unit(name, x0, x1, y0, y1, code="X-1"):
    ext = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]], float)
    return boundaries.Unit(name, code, [(ext, [])], (x0, y0, x1, y1))


def test_fractions_and_province_weights_on_synthetic_country():
    g = grid.Grid("sintética", 0.25, np.array([18.125, 18.375, 18.625, 18.875]), np.array([-70.875, -70.625, -70.375, -70.125]))
    units = [_square_unit("Oeste", -71.0, -70.5, 18.0, 19.0, "X-1"), _square_unit("Este", -70.5, -70.0, 18.0, 18.5, "X-2")]
    cells, w = grid.fractions(g, units, {}, n=20)
    c = cells.set_index("celda")
    assert c.loc[grid.cell_id(18.125, -70.875), "frac_pais"] == pytest.approx(1.0)
    assert c.loc[grid.cell_id(18.875, -70.125), "frac_pais"] == pytest.approx(0.0)
    assert set(w["provincia"]) == {"Oeste", "Este"}
    assert w.groupby("celda")["fraccion"].sum().max() <= 1.0 + 1e-9
    pw = grid.province_weights(w, cells)
    const = pd.DataFrame({cid: [5.0, 5.0] for cid in cells["celda"]}, index=pd.date_range("2001-01-01", periods=2, freq="MS"))
    ps = grid.province_series(const, pw)
    assert np.allclose(ps.to_numpy(), 5.0)


def test_remap_is_conservative_for_constant_field():
    fine = grid.Grid("f", 0.1, np.round(np.arange(18.05, 19.0, 0.1), 3), np.round(np.arange(-70.95, -70.0, 0.1), 3))
    coarse = grid.Grid("c", 0.25, np.array([18.125, 18.375, 18.625, 18.875]), np.array([-70.875, -70.625, -70.375, -70.125]))
    w = grid.remap_weights(fine, coarse, np.ones(fine.n))
    tot = w.groupby("celda_gruesa")["peso"].sum()
    area = pd.Series(grid.cell_area_km2(coarse.mesh()[0], 0.25), index=coarse.ids())
    assert np.allclose(tot.reindex(area.index).to_numpy(), area.to_numpy(), rtol=1e-6)
    const = pd.DataFrame(7.0, index=[0, 1], columns=fine.ids())
    out = grid.apply_weights(const, w, "celda_fina", "celda_gruesa")
    assert np.allclose(out.to_numpy(), 7.0)


def test_cell_area_matches_sphere():
    lat = np.arange(-89.875, 90, 0.25)
    total = grid.cell_area_km2(lat, 0.25).sum() * (360 / 0.25)
    assert total == pytest.approx(4 * np.pi * grid.R_EARTH ** 2, rel=1e-9)


def test_imerg_indices_for_dr_box():
    i0, i1, j0, j1 = earthdata.bbox_to_edges((-72.0598, 17.4956, -68.2786, 19.9877), earthdata.IMERG_GRID)
    assert (i0, i1, j0, j1) == (1079, 1117, 1074, 1099)
    lon = earthdata.IMERG_GRID.centers(i0, i1, "lon")
    assert lon[0] == pytest.approx(-72.05) and lon[-1] == pytest.approx(-68.25)


# ------------------------------------------------------------------ credencial

def test_token_never_in_error_message(tmp_path, monkeypatch):
    secret = "SINTETICO-" + "x" * 40
    f = tmp_path / "tok"
    f.write_text(secret)
    monkeypatch.setenv("EARTHDATA_TOKEN_FILE", str(f))
    monkeypatch.setattr(earthdata.time, "sleep", lambda s: None)
    with pytest.raises(earthdata.EarthdataError) as e:
        earthdata.get("http://127.0.0.1:9/nada", retries=1, timeout=2)
    assert secret not in str(e.value)


# ------------------------------------------------------------------ latigazos y etiquetas

def test_whiplash_counts():
    s = pd.Series([0, -1.0, -0.2, 1.0, 0, 0, 1.2, 0.1, -0.9, 0, 0, 0, -1, 0, 0, 0, 1])  # sintético
    out = whiplash_events(s)
    assert out["seco_a_humedo"] == 1   # −1.0 → +1.0 en 2 meses; −1 → +1 tarda 4 meses (no cuenta)
    assert out["humedo_a_seco"] == 1   # +1.2 → −0.9 en 2 meses


def test_contradiction_labels_across_products():
    t = pd.Timestamp
    ep = pd.DataFrame({"celda": ["a", "a"], "inicio": [t("2015-01-01"), t("2019-01-01")],
                       "fin": [t("2015-06-01"), t("2019-05-01")], "contradiccion_A_SM_RAIZ": [True, True]})
    ep_mod = pd.DataFrame({"celda": ["a"], "inicio": [t("2015-02-01")], "fin": [t("2015-07-01")],
                           "contradiccion_A_SM_RAIZ": [True]})
    lab = match_episodes_across_products(ep, ep_mod)["contradiccion_A_SM_RAIZ_etiqueta"].tolist()
    assert lab == ["también con la lluvia del modelo", "posible diferencia entre productos"]


def test_appeears_hook_empty_without_files(tmp_path):
    g = grid.Grid("c", 0.25, np.array([18.125]), np.array([-70.125]))
    assert appeears_hook.load_monthly(tmp_path, g, pd.date_range("2001-01-01", periods=3, freq="MS")) == {}
    assert appeears_hook.annual_npp(tmp_path, g).empty
