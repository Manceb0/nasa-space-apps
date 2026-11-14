"""Pruebas de lectura (Giovanni, AppEEARS), sequías y estadística con DATOS SINTÉTICOS."""

import numpy as np
import pandas as pd
import pytest

from phantom import appeears, drought, giovanni, stats


def write_giovanni(tmp_path, values, months=None, note=False):
    months = months or pd.date_range("2001-01-01", periods=len(values), freq="MS")
    lines = [
        'Title:,"DATOS SINTETICOS DE PRUEBA"',
        'User Bounding Box:,"-71.6,19.75,-71.35,19.92"',
        "Fill Value (mean_X):, -9999.9",
    ]
    if note:
        lines.append('Note:,"Reconstruido para prueba"')
    lines += ["", "time, mean_X"]
    lines += [f"{m:%Y-%m-%d} 00:00:00,{v}" for m, v in zip(months, values)]
    p = tmp_path / "x.csv"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_giovanni_reader_fill_and_validation(tmp_path):
    vals = [1.0] * 288
    vals[5] = -9999.9
    gs = giovanni.read_giovanni_csv(write_giovanni(tmp_path, vals, note=True))
    assert gs.reconstructed
    assert np.isnan(gs.values.iloc[5])
    v = giovanni.validate_monthly(gs)
    assert v["faltantes"] == 1 and not v["ok"]


def test_giovanni_validation_detects_missing_months(tmp_path):
    months = list(pd.date_range("2001-01-01", "2024-12-01", freq="MS").delete(10))
    gs = giovanni.read_giovanni_csv(write_giovanni(tmp_path, [1.0] * len(months), months))
    v = giovanni.validate_monthly(gs)
    assert "faltan 1 meses" in v["problemas"]


def test_spi_is_standard_normal_on_gamma_rain():
    rng = np.random.default_rng(0)
    idx = pd.date_range("2001-01-01", "2024-12-01", freq="MS")
    rain = pd.Series(rng.gamma(2.0, 40.0, idx.size), index=idx)
    rain.iloc[::17] = 0.0  # meses sin lluvia
    s = drought.spi(rain, 3).dropna()
    assert abs(s.mean()) < 0.15 and 0.8 < s.std() < 1.2


def test_runs_below_finds_events_and_recovery():
    idx = pd.date_range("2010-01-01", periods=12, freq="MS")
    x = pd.Series([0.5, -1.2, -1.5, -0.3, -1.1, 0.2, -1.4, -1.6, -1.2, -0.5, 0.1, 0.4], index=idx)
    ev = drought.runs_below(x, -1.0, min_len=2)
    assert len(ev) == 2
    assert ev.iloc[1]["duracion_meses"] == 3
    assert ev.iloc[1]["recuperacion_candidata"] == pd.Timestamp("2010-11-01")


def appeears_csv(tmp_path, product, cols: dict, n_dates=30, period=16):
    dates = pd.date_range("2005-01-01", periods=n_dates, freq=f"{period}D")
    df = pd.DataFrame({"ID": "p1", "Category": "noroeste", "Latitude": 19.87, "Longitude": -71.5,
                       "Date": dates.strftime("%Y-%m-%d")})
    for k, v in cols.items():
        df[f"{product}_061_{k}"] = v
    p = tmp_path / f"prueba-{product}-061-results.csv"
    df.to_csv(p, index=False)
    return p


def test_mod13_scaling_and_quality(tmp_path):
    rel = [0] * 25 + [1, 2, 3, -1, 0]
    appeears_csv(tmp_path, "MOD13Q1", {"_250m_16_days_NDVI": [6500] * 29 + [-3000],
                                       "_250m_16_days_EVI": [4000] * 30,
                                       "_250m_16_days_pixel_reliability": rel})
    log = []
    out = appeears.read_mod13(tmp_path / "prueba-MOD13Q1-061-results.csv", log)
    assert out["ndvi"].iloc[0] == pytest.approx(0.65)
    assert out["ndvi"].notna().sum() == 26  # 25 buenos + 1 marginal; relleno fuera
    assert any("crudos" in l for l in log)


def test_mod13_already_scaled_is_left_alone(tmp_path):
    appeears_csv(tmp_path, "MOD13Q1", {"_250m_16_days_NDVI": [0.65] * 30, "_250m_16_days_EVI": [0.4] * 30,
                                       "_250m_16_days_pixel_reliability": [0] * 30})
    log = []
    out = appeears.read_mod13(tmp_path / "prueba-MOD13Q1-061-results.csv", log)
    assert out["ndvi"].iloc[0] == pytest.approx(0.65)


def test_mod11_qc_bits_and_kelvin(tmp_path):
    # 0b00000000 bueno; 0b01000001 otra calidad con error <=2K; 0b10000001 error <=3K (fuera); 0b10 sin producir
    qc = [0, 0b01000001, 0b10000001, 0b10] + [0] * 26
    appeears_csv(tmp_path, "MOD11A2", {"LST_Day_1km": [15000] * 30, "QC_Day": qc}, period=8)
    out = appeears.read_mod11(tmp_path / "prueba-MOD11A2-061-results.csv", [])
    assert out["lst_c"].iloc[0] == pytest.approx(15000 * 0.02 - 273.15)
    assert out["lst_c"].iloc[1] == pytest.approx(26.85)
    assert np.isnan(out["lst_c"].iloc[2]) and np.isnan(out["lst_c"].iloc[3])


def test_mod17_fill_removed(tmp_path):
    appeears_csv(tmp_path, "MOD17A2HGF", {"Gpp_500m": [250] * 29 + [32767], "Psn_QC_500m": [0] * 30}, period=8)
    out = appeears.read_mod17(tmp_path / "prueba-MOD17A2HGF-061-results.csv", [])
    assert out["gpp"].iloc[0] == pytest.approx(0.025)
    assert np.isnan(out["gpp"].iloc[-1])


def test_landcover_stability_excludes_changes():
    lc = pd.DataFrame({"id": ["a"] * 3 + ["b"] * 3, "lc_type1": [7, 7, 7, 7, 12, 7],
                       "anio": [2001, 2010, 2021] * 2})
    res = appeears.landcover_stability(lc).set_index("id")
    assert res.loc["a", "usar"] and res.loc["a", "estable"]
    assert not res.loc["b", "usar"]


def test_mann_kendall_and_theil_sen():
    y = np.arange(20) * 2.0 + np.random.default_rng(1).normal(0, 0.5, 20)
    mk = stats.mann_kendall(y)
    assert mk["p"] < 0.01 and mk["tau"] > 0.8
    assert stats.theil_sen(np.arange(20), y)["pendiente"] == pytest.approx(2.0, abs=0.2)
    assert stats.mann_kendall([1, 2, 3])["p"] is None


def test_benjamini_hochberg():
    q = stats.benjamini_hochberg([0.01, 0.04, None, 0.03, 0.5])
    assert q[2] is None
    assert all(a is None or a >= p for a, p in zip(q, [0.01, 0.04, None, 0.03, 0.5]) if p is not None)



def test_mod09_ndii_and_cloud_filter(tmp_path):
    # estado 0 = despejado; 0b01 = nube; 0b100 = sombra; 1<<13 = junto a nube (DATOS SINTÉTICOS)
    state = [0] * 26 + [0b01, 0b100, 1 << 13, 0]
    appeears_csv(tmp_path, "MOD09A1", {"sur_refl_b02": [3000] * 30, "sur_refl_b06": [2000] * 29 + [-28672],
                                       "sur_refl_state_500m": state, "sur_refl_qc_500m": [0] * 30}, period=8)
    out = appeears.read_mod09(tmp_path / "prueba-MOD09A1-061-results.csv", [])
    assert out["ndii"].iloc[0] == pytest.approx((0.3 - 0.2) / (0.3 + 0.2))
    assert out["ndii"].notna().sum() == 26  # nube, sombra, adyacente y relleno fuera
