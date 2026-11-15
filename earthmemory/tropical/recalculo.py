"""Recalcular las tendencias P0 corrigiendo el escalón de IMERG de 2013-10 (ver PRUEBAS_TROPICALES.md).

Usa EXACTAMENTE el motor P0 (motor.run_all: Theil-Sen, Mann-Kendall con Hamed-Rao, BH-FDR, clases de confianza)
sobre las mismas series anuales guardadas por la corrida P0 (data/tendencias/derivados/estado_corrida.pkl). Solo
cambia la serie de IMERG:

- A_frec (PRINCIPAL): como A, pero solo en los índices de frecuencia (R1mm, SDII, CDD, CWD, RACHAS10, RACHAS15),
  porque el escalón se detectó en la frecuencia de días húmedos y no en la cantidad.
- A «homogeneizada con referencia»: por celda e índice, escalón c = media(IMERG − CHIRPS, 2014-2024) −
  media(IMERG − CHIRPS, 2001-2013); IMERG_corr = IMERG − c desde 2014. Supone que CHIRPS es homogéneo en ese salto
  (lo respaldan los pluviómetros GHCN-D, prueba P5). 2013 queda en «antes» (el salto es en octubre).
- B «escalón propio»: ajuste OLS y = a + b·año + c·[año ≥ 2014] en la propia serie de IMERG y se resta c·[año ≥ 2014].
  No usa CHIRPS, pero el escalón y la tendencia se parecen y compiten (estimación menos precisa).
CHIRPS no se toca. Las salidas originales de P0 NO se modifican: todo va a results/tropical/recalculo/.
"""

from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from ..hr.common import ROOT, write_json
from ..tendencias import datos, motor

OUT = ROOT / "results" / "tropical" / "recalculo"
CORTE = 2014
# índices que dependen de CONTAR días húmedos (≥ 1 mm): donde está el escalón (P4: frecuencia p = 0,001; cantidad p = 0,10)
FRECUENCIA = {"R1mm", "SDII", "CDD", "CWD", "RACHAS10", "RACHAS15"}
FOCO = [("SDII", "anual"), ("R1mm", "anual"), ("CDD", "anual"), ("PRCPTOT", "anual"), ("R20mm", "anual"),
        ("Rx1day", "anual"), ("RACHAS15", "seca"), ("R1mm", "seca")]


def corregir(series: dict, modo: str) -> dict:
    """modo A: todos los índices; A_frec: solo los de frecuencia (variante principal); B: escalón propio, todos."""
    out = {}
    for key, val in series["IMERG"].items():
        if isinstance(key, str) or (modo == "A_frec" and key[0] not in FRECUENCIA):
            out[key] = val
            continue
        years, A = val
        A = A.astype(float).copy()
        after = years >= CORTE
        if modo in ("A", "A_frec"):
            yc, C = series["CHIRPS"][key]
            assert np.array_equal(yc, years)
            D = A - C
            c = np.nanmean(D[after], 0) - np.nanmean(D[~after], 0)
        else:
            X = np.column_stack([np.ones(years.size), years - years.mean(), after.astype(float)])
            c = np.full(A.shape[1], np.nan)
            for j in range(A.shape[1]):
                ok = np.isfinite(A[:, j])
                if ok.sum() >= 12:
                    c[j] = np.linalg.lstsq(X[ok], A[ok, j], rcond=None)[0][2]
        c = np.nan_to_num(c)
        A[after] -= c
        out[key] = (years, A)
    return out


def conteo(tc: pd.DataFrame) -> pd.DataFrame:
    t = tc[tc["fuente"] == "IMERG"]
    g = t.groupby(["indice", "periodo", "clase_confianza"]).size().unstack(fill_value=0)
    for c in ("robusta", "consistente", "en disputa", "sin señal detectable"):
        if c not in g:
            g[c] = 0
    sig = tc.groupby(["indice", "periodo", "fuente"])["sig_fdr"].sum().unstack(fill_value=0)
    g = g.join(sig.rename(columns={"IMERG": "sig_IMERG", "CHIRPS": "sig_CHIRPS"}))
    return g[["robusta", "consistente", "en disputa", "sin señal detectable", "sig_IMERG", "sig_CHIRPS"]]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with (datos.DER / "estado_corrida.pkl").open("rb") as fh:
        st = pickle.load(fh)
    S, series = st["S"], st["series"]
    orig = motor.run_all(series, S, log=lambda *a: None)
    tabla = {"original": conteo(orig["celdas"])}
    nat = {"original": orig["regiones"]}
    for modo in ("A_frec", "A", "B"):
        s2 = {"IMERG": corregir(series, modo), "CHIRPS": series["CHIRPS"]}
        r = motor.run_all(s2, S, log=lambda *a: None)
        r["celdas"].to_csv(OUT / f"tendencias_celdas_{modo}.csv", index=False, float_format="%.5g")
        tabla[modo] = conteo(r["celdas"])
        nat[modo] = r["regiones"]
    comp = pd.concat(tabla, axis=1)
    comp.to_csv(OUT / "comparacion_clases.csv")
    # comprobación: la corrida "original" reproduce el CSV publicado
    pub = pd.read_csv(ROOT / "results" / "tendencias" / "tendencias_celdas.csv")
    chk = conteo(pub)
    same = bool((chk.loc[:, ["robusta", "consistente", "en disputa"]].sort_index()
                 == tabla["original"].loc[:, ["robusta", "consistente", "en disputa"]].sort_index()).all().all())
    rows = []
    for v, R in nat.items():
        g = R[(R["region"] == motor.NATIONAL) & (R["fuente"] == "IMERG")]
        for idx, per in FOCO:
            x = g[(g["indice"] == idx) & (g["periodo"] == per)]
            if len(x):
                x = x.iloc[0]
                rows.append({"variante": v, "indice": idx, "periodo": per, "pendiente_decada": x["pendiente_decada"],
                             "pendiente_pct_decada": x["pendiente_pct_decada"], "p": x["p"],
                             "clase_confianza": x["clase_confianza"]})
    natdf = pd.DataFrame(rows)
    natdf.to_csv(OUT / "nacional_IMERG_foco.csv", index=False, float_format="%.4g")
    foco = comp.loc[[k for k in FOCO if k in comp.index]]
    print("reproduce_P0_publicado:", same)
    pd.set_option("display.width", 250)
    print(foco.to_string())
    print(natdf.pivot_table(index=["indice", "periodo"], columns="variante",
                            values=["pendiente_pct_decada", "p"]).round(3).to_string())
    tot = comp.xs("en disputa", axis=1, level=1).sum()
    rob = comp.xs("robusta", axis=1, level=1).sum()
    print("total celdas-indice en disputa:", tot.to_dict(), " robustas:", rob.to_dict())
    write_json(OUT / "resumen.json", {"reproduce_P0_publicado": same, "corte": CORTE,
                                      "total_en_disputa": tot.to_dict(), "total_robustas": rob.to_dict()})


if __name__ == "__main__":
    main()
