"""Pares de celdas con lluvia parecida y respuesta distinta.

"Lluvia parecida" (criterio principal; se varía en la sensibilidad):
- distancia entre centros <= 150 km;
- correlación de SPI-3 entre las dos celdas >= 0.70 (las anomalías de lluvia ocurren a la vez);
- lluvia media anual con diferencia relativa <= 25 % (climatología parecida).

"Respuesta distinta": diferencia Δ = métrica(A) − métrica(B) con bootstrap conjunto por bloques
(mismos meses remuestreados en las dos celdas). Benjamini-Hochberg sobre TODAS las pruebas par ×
respuesta × métrica de la corrida principal. Las celdas vecinas comparten forzamiento y los pares
comparten celdas: las pruebas no son independientes (BH es válido bajo dependencia positiva, PRDS,
pero dos pares que comparten una celda no son dos hallazgos).
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from phantom import stats

from . import coupling, region

MAIN = {"max_km": 150.0, "min_r": 0.70, "max_clim": 0.25}
STRICT = {"max_km": 100.0, "min_r": 0.80, "max_clim": 0.15}


def candidate_pairs(cells: pd.DataFrame, precip_mm: pd.DataFrame, spi3: pd.DataFrame,
                    max_km: float = MAIN["max_km"], min_r: float = MAIN["min_r"],
                    max_clim: float = MAIN["max_clim"]) -> pd.DataFrame:
    inc = cells[cells["incluida"]].set_index("celda")
    elev_col = next((c for c in ("elevacion_m", "elevacion_merra2_m") if c in inc.columns), None)
    annual = precip_mm.groupby(precip_mm.index.year).sum().mean()
    seas = precip_mm.groupby(precip_mm.index.month).mean()
    rows = []
    for a, b in itertools.combinations(sorted(inc.index), 2):
        dkm = region.haversine_km(inc.loc[a, "lat"], inc.loc[a, "lon"], inc.loc[b, "lat"], inc.loc[b, "lon"])
        d = pd.DataFrame({"a": spi3[a], "b": spi3[b]}).dropna()
        r = float(np.corrcoef(d["a"], d["b"])[0, 1])
        pa, pb = float(annual[a]), float(annual[b])
        rel = abs(pa - pb) / ((pa + pb) / 2)
        rows.append({"celda_a": a, "celda_b": b, "distancia_km": dkm, "r_spi3": r,
                     "lluvia_anual_a_mm": pa, "lluvia_anual_b_mm": pb, "dif_rel_lluvia_anual": rel,
                     "r_ciclo_estacional": float(np.corrcoef(seas[a], seas[b])[0, 1]),
                     "dif_elevacion_m": (float(inc.loc[a, elev_col] - inc.loc[b, elev_col]) if elev_col else np.nan),
                     "frac_pais_min": float(min(inc.loc[a, "frac_pais"], inc.loc[b, "frac_pais"]))})
    df = pd.DataFrame(rows)
    df["lluvia_parecida"] = (df["distancia_km"] <= max_km) & (df["r_spi3"] >= min_r) & (df["dif_rel_lluvia_anual"] <= max_clim)
    df["pasa_criterio_estricto"] = ((df["distancia_km"] <= STRICT["max_km"]) & (df["r_spi3"] >= STRICT["min_r"])
                                    & (df["dif_rel_lluvia_anual"] <= STRICT["max_clim"]))
    return df


def pair_delta(cm: coupling.CellMetrics, a: str, b: str, resp: str, metric: str) -> dict:
    pt = cm.point.set_index(["celda", "respuesta", "metrica"])["valor"]
    va, vb = float(pt[(a, resp, metric)]), float(pt[(b, resp, metric)])
    bd = cm.boot[(a, resp, metric)] - cm.boot[(b, resp, metric)]
    delta = va - vb
    return {"valor_a": va, "valor_b": vb, "delta": delta, "ic95_bajo": float(np.percentile(bd, 2.5)),
            "ic95_alto": float(np.percentile(bd, 97.5)), "ee_boot": float(bd.std(ddof=1)),
            "p": coupling.p_from_boot(delta, bd)}


def test_pairs(pairs: pd.DataFrame, cm: coupling.CellMetrics, responses: list) -> pd.DataFrame:
    rows = []
    for _, pr in pairs[pairs["lluvia_parecida"]].iterrows():
        for resp in responses:
            for m in coupling.METRICS:
                rows.append({"celda_a": pr["celda_a"], "celda_b": pr["celda_b"], "respuesta": resp, "metrica": m,
                             **pair_delta(cm, pr["celda_a"], pr["celda_b"], resp, m)})
    df = pd.DataFrame(rows)
    if len(df):
        df["q_bh"] = stats.benjamini_hochberg(df["p"].tolist())
        df["n_pruebas_bh"] = int(df["p"].notna().sum())
    return df


def sensitivity(targets: pd.DataFrame, variants: dict) -> pd.DataFrame:
    """variants: {etiqueta: CellMetrics}. Para cada prueba objetivo, Δ e IC en cada variante."""
    rows = []
    for _, t in targets.iterrows():
        for lab, cm in variants.items():
            d = pair_delta(cm, t["celda_a"], t["celda_b"], t["respuesta"], t["metrica"])
            rows.append({"celda_a": t["celda_a"], "celda_b": t["celda_b"], "respuesta": t["respuesta"],
                         "metrica": t["metrica"], "variante": lab, **d,
                         "mismo_signo": bool(np.sign(d["delta"]) == np.sign(t["delta"])),
                         "ic_excluye_0": bool(d["ic95_bajo"] > 0 or d["ic95_alto"] < 0)})
    return pd.DataFrame(rows)


def rank(tests: pd.DataFrame, sens: pd.DataFrame, pairs: pd.DataFrame, cells: pd.DataFrame) -> pd.DataFrame:
    key = ["celda_a", "celda_b", "respuesta", "metrica"]
    rob = (sens.assign(ok=sens["mismo_signo"] & sens["ic_excluye_0"]).groupby(key)
           .agg(n_variantes=("ok", "size"), variantes_ok=("ok", "sum"),
                variantes_mismo_signo=("mismo_signo", "sum")).reset_index())
    rob["robustez"] = rob["variantes_ok"] / rob["n_variantes"]
    df = tests.merge(rob, on=key, how="inner").merge(
        pairs[["celda_a", "celda_b", "distancia_km", "r_spi3", "dif_rel_lluvia_anual", "dif_elevacion_m",
               "frac_pais_min", "pasa_criterio_estricto"]], on=["celda_a", "celda_b"], how="left")
    df["efecto_abs"] = df["delta"].abs()
    df["mascara_estricta_ok"] = df["frac_pais_min"] >= 0.5
    df = df.sort_values(["robustez", "pasa_criterio_estricto", "mascara_estricta_ok", "q_bh", "efecto_abs"],
                        ascending=[False, False, False, True, False]).reset_index(drop=True)
    df.insert(0, "rango", np.arange(1, len(df) + 1))
    return df
