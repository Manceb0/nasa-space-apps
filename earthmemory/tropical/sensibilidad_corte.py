"""Sensibilidad del recálculo A_frec al año del corte: si el escalón es real y está en 2013-10, el número de celdas
en disputa en los índices ANUALES de frecuencia debería ser mínimo con el corte en 2014 (o 2013)."""
import pickle

import pandas as pd

from ..hr.common import ROOT
from ..tendencias import datos, motor
from . import recalculo as rc

ANUALES = ["SDII", "R1mm", "CDD", "CWD", "RACHAS10", "RACHAS15"]


def main():
    with (datos.DER / "estado_corrida.pkl").open("rb") as fh:
        st = pickle.load(fh)
    S, series = st["S"], st["series"]
    keys = [k for k in series["IMERG"] if not isinstance(k, str) and k[0] in rc.FRECUENCIA]
    sub = {p: {k: series[p][k] for k in keys} for p in ("IMERG", "CHIRPS")}
    rows = []
    for corte in [None] + list(range(2006, 2021)):
        if corte is None:
            s2 = sub
        else:
            rc.CORTE = corte
            s2 = {"IMERG": rc.corregir(sub, "A_frec"), "CHIRPS": sub["CHIRPS"]}
        tc = motor.run_all(s2, S, log=lambda *a: None)["celdas"]
        t = tc[tc["fuente"] == "IMERG"]
        an = t[t["periodo"] == "anual"]
        rows.append({"corte": "sin corrección" if corte is None else corte,
                     "disputa_anuales": int((an["clase_confianza"] == "en disputa").sum()),
                     "disputa_todas_frecuencia": int((t["clase_confianza"] == "en disputa").sum()),
                     "sig_IMERG_anuales": int(an["sig_fdr"].sum())})
        print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(ROOT / "results" / "tropical" / "recalculo" / "sensibilidad_corte.csv", index=False)


if __name__ == "__main__":
    main()
