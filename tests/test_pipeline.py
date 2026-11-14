"""Prueba de punta a punta: Giovanni REAL (solo lectura) + archivos AppEEARS SINTÉTICOS en una carpeta temporal.

Todo lo que escribe va a tmp_path; no toca results/, figures/ ni RESULTS.md del repo.
"""

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from phantom import pipeline
from tests.synthetic import composite_dates

REPO = Path(__file__).resolve().parents[1]


def _write(tmp: Path, product: str, period: int, layers: dict, pid="montecristi_monte_seco_a"):
    d = composite_dates(period, start="2001-01-01", end="2024-12-31")
    df = pd.DataFrame({"ID": pid, "Category": "noroeste", "Latitude": 19.87, "Longitude": -71.5,
                       "Date": d.strftime("%Y-%m-%d")})
    for name, fn in layers.items():
        df[f"{product}_061_{name}"] = fn(d)
    df.to_csv(tmp / f"sintetico-{product}-061-results.csv", index=False)


def test_pipeline_end_to_end_with_synthetic_modis(tmp_path):
    root = tmp_path
    shutil.copytree(REPO / "data" / "giovanni", root / "data" / "giovanni")
    ad = root / "data" / "appeears"
    ad.mkdir(parents=True)
    rng = np.random.default_rng(3)

    def seasonal(d, base, amp, noise):
        return base + amp * np.sin(2 * np.pi * d.day_of_year / 365.25) + rng.normal(0, noise, d.size)

    def dip(d, start, end, depth):
        return np.where((d >= start) & (d < end), depth, 0.0)

    _write(ad, "MOD13Q1", 16, {
        "_250m_16_days_NDVI": lambda d: np.round((seasonal(d, 0.6, 0.1, 0.01) - dip(d, "2015-05-01", "2016-01-15", 0.15)) * 1e4),
        "_250m_16_days_EVI": lambda d: np.round((seasonal(d, 0.4, 0.08, 0.01) - dip(d, "2015-05-01", "2016-01-15", 0.1)) * 1e4),
        "_250m_16_days_pixel_reliability": lambda d: np.zeros(d.size, dtype=int),
    })
    _write(ad, "MOD17A2HGF", 8, {
        "Gpp_500m": lambda d: np.round((seasonal(d, 0.03, 0.01, 0.0005) - dip(d, "2015-05-01", "2016-04-01", 0.012)) * 1e4),
        "Psn_QC_500m": lambda d: np.zeros(d.size, dtype=int),
    })
    _write(ad, "MOD11A2", 8, {
        "LST_Day_1km": lambda d: np.round((seasonal(d, 305, 3, 0.2) + dip(d, "2015-05-01", "2016-03-01", 4)) / 0.02),
        "QC_Day": lambda d: np.zeros(d.size, dtype=int),
    })
    _write(ad, "MCD12Q1", 365, {"LC_Type1": lambda d: np.full(d.size, 7)})

    pipeline.main(["--root", str(root)])

    status = json.loads((root / "results" / "estado_modis.json").read_text(encoding="utf-8"))
    assert status["estado"] == "procesado"
    res = pd.read_csv(root / "results" / "recuperacion_eventos.csv", parse_dates=["evento_inicio"])
    ev2015 = res[(res["evento_inicio"] == "2015-04-01")].set_index("funcion")
    assert ev2015.loc["gpp_modelo", "estado"] == "ambos_recuperados"
    assert ev2015.loc["gpp_modelo", "dt_dias"] > 32  # GPP sintético vuelve ~2.5 meses después
    assert ev2015.loc["lst_menos_aire", "dt_dias"] > 0
    assert (root / "results" / "tendencias.csv").exists()
    assert any(p.name.startswith("evento_") for p in (root / "figures").iterdir())
    assert "Recuperación verde vs. función" in (root / "RESULTS.md").read_text(encoding="utf-8")
