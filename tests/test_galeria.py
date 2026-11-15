"""La galería codifica exactamente los números verificados por los motores (auditoría, tendencias, Yuna).

    docker compose run --rm --entrypoint "uv run --frozen --no-sync pytest -q tests/test_galeria.py" galeria
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

G = Path("figures/galeria")
RA = Path("results/auditoria")


def _prov(nombre):
    return json.loads((G / f"{nombre}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def estados():
    from earthmemory.galeria import datos as D
    spi = D.spi3_provincias()
    return D.estados(spi, -1.0)


def test_barcode_coincide_con_auditoria(estados):
    from earthmemory.galeria import datos as D
    E, cnt = estados
    nat = json.loads((RA / "cambio_decision_sequia_nacional.json").read_text(encoding="utf-8"))[0]
    assert nat["umbral_spi3"] == -1.0 and nat["productos"] == "4 productos"
    assert E.shape == (288, 32)
    assert cnt["unanimous"] == nat["n_unanime_sequia"] == 275
    assert cnt["n_alguna_alarma"] == nat["n_alguna_alarma"] == 3111
    assert cnt["n_no_unanime"] == nat["n_no_unanime"] == 2836
    assert cnt["contradiction"] == nat["n_contradiccion_clara"] == 1201
    assert cnt["majority"] + cnt["split"] + cnt["contradiction"] == 2836
    assert cnt["unanimous"] + cnt["majority"] + cnt["split"] + cnt["contradiction"] + cnt["no_alarm"] == nat["n_casos"]
    D.check_contra_auditoria(E, cnt)          # por año y por provincia
    assert _prov("01_barcode_of_doubt")["numeros_codificados"]["unanimous"] == 275


def test_espiral_suma_no_unanimes():
    s = pd.read_csv(G / "_datos" / "espiral_serie.csv")
    assert len(s) == 288
    assert int(s["provincias_no_unanimes"].sum()) == 2836
    assert s["provincias_no_unanimes"].max() <= 32
    n = _prov("02_spiral_of_disagreement")["numeros_codificados"]
    assert n["suma"] == 2836 and n["meses_validos"] == 286


def test_relieve_clases_sdii():
    d = pd.read_csv("results/tendencias/tendencias_celdas.csv")
    s = d[(d["indice"] == "SDII") & (d["periodo"] == "anual") & (d["fuente"] == "IMERG")]
    vc = s["clase_confianza"].value_counts().to_dict()
    n = _prov("03_ridgeline_relief")["numeros_codificados"]
    assert n["por_clase"] == vc
    assert n["n_celdas"] == len(s) == 442
    assert n["disputa_imerg_sube_chirps_baja"] == vc["en disputa"]


def test_genealogia_es_la_matriz():
    m = pd.read_csv(RA / "procedencia_insumos_compartidos.csv").set_index("insumo").fillna("")
    n = _prov("04_genealogy_of_the_data")["numeros_codificados"]
    v = int((m == "V").sum().sum())
    i = int((m == "I").sum().sum())
    assert n["n_verificadas"] == v and n["n_inferidas"] == i and n["n_aristas"] == v + i
    assert {(a["insumo"], a["producto"], a["estado"]) for a in n["aristas"]} == {
        (k, p, m.loc[k, p]) for k in m.index for p in m.columns if m.loc[k, p] in ("V", "I")}
    sequia = ["IMERG", "CHIRPS", "GLDAS_forzamiento", "MERRA2"]
    esperado = [k for k in m.index if sum(m.loc[k, p] in ("V", "I") for p in sequia) >= 2]
    assert sorted(n["insumos_compartidos_por_productos_de_sequia"]) == sorted(esperado)


def test_bivariado_terciles():
    d = pd.read_csv(RA / "donde_medir_prototipo.csv")
    n = _prov("05_bivariate_where_to_measure")["numeros_codificados"]
    qf = np.nanquantile(d["tasa_cambio_condicional_spi3"], [1 / 3, 2 / 3])
    qs = np.nanquantile(d["dist_estacion_ghcn_activa_km"], [1 / 3, 2 / 3])
    assert np.allclose(qf, n["terciles_tasa_cambio"]) and np.allclose(qs, n["terciles_distancia_km"])
    tot = sum(v for col in n["n_celdas_por_clase_dist_x_cambio"].values() for v in col.values())
    assert tot == len(d) == 443
    hh = ((np.digitize(d["tasa_cambio_condicional_spi3"], qf) == 2)
          & (np.digitize(d["dist_estacion_ghcn_activa_km"], qs) == 2)).sum()
    assert int(hh) == n["n_celdas_clase_alta_alta"]


def test_tormenta_cuadra_con_auditoria():
    sd = json.loads((RA / "santo_domingo_2023-11-18.json").read_text(encoding="utf-8"))
    n = _prov("06_santo_domingo_storm")["numeros_codificados"]
    assert abs(n["imerg_celda_dia_utc_18_mm"] - sd["imerg_diario"]["celda_dia_utc_18"]) < 0.5
    assert n["estacion_mm"] == sd["descomposicion"]["estacion_mm"] == 431.0
    assert n["celda"] == sd["celda"]
    gif = G / "dark" / "06_santo_domingo_storm.gif"
    assert gif.exists() and gif.stat().st_size <= 8 * 2**20


def test_atlas_yuna_km2_y_orden():
    pe = pd.read_csv("results/yuna/mcdwd_por_evento.csv").set_index("id")
    cat = pd.read_csv("results/yuna/catalogo_eventos.csv")
    n = _prov("01b_yuna_flood_atlas")["numeros_codificados"]
    ev = n["eventos"]
    assert [e["id"] for e in ev] == [i for i in cat["id"] if i in pe.index]
    assert len(ev) == 15
    assert [e["dia"] for e in ev] == sorted(e["dia"] for e in ev)          # orden temporal
    for e in ev:
        ref = pe.loc[e["id"], "inund_km2_max_yuna"]
        if np.isfinite(ref):
            assert abs(e["km2_clase3"] - ref) <= max(0.02 * ref, 0.11), e["id"]
            assert e["dia"][:10] == pe.loc[e["id"], "dia_max_yuna"]


def test_metadatos_png_y_procedencia():
    from PIL import Image
    pngs = sorted(G.glob("dark/*.png")) + sorted(G.glob("light/*.png"))
    assert len(pngs) >= 20
    for p in pngs:
        info = Image.open(p).info
        assert "AI assistance (Claude)" in info.get("Software", ""), p
        assert info.get("Description") and info.get("Source"), p
    for j in G.glob("*.json"):
        d = json.loads(j.read_text(encoding="utf-8"))
        assert d["alt_en"] and d["alt_es"] and d["entradas"] and d["archivos"]
        for f in d["archivos"]:
            assert Path(f).exists(), f
