"""¿El salto de IMERG es de 2018 o del paso de la era TRMM a la era GPM (2014)?

Origen (dicho tal cual): hawaii.py registró que el punto de cambio caería en 2017-2018 o en 2019. No cayó en ninguna:
Pettitt lo puso en 2014-04 en Hawái y en 2013-11 en Puerto Rico. Esa observación es POSTERIOR; esta prueba la pone a
prueba con predicciones nuevas, escritas antes de calcular las medias por tramo.

Hipótesis de era: IMERG V07 calibra las microondas al combinado radar-radiómetro de TRMM antes de GPM y al de GPM
después (GPM se lanzó el 27-feb-2014; Joyce, Huffman y otros, EGU 2026, describen esa doble calibración y las
inhomogeneidades que deja V07). Si el salto es de era, la diferencia (IMERG − testigo) ya baja entre 2001-2013 y
2015-2017, antes de NOAA-20 y del GOES-16, y casi no baja más después de 2018-02.
Se excluye todo 2014 (año de transición) para no depender del mes exacto del cambio de era.

Series: mediana entre estaciones de (frecuencia de días >= 1 mm IMERG − pluviómetro), mensual, de hawaii.py (Hawái y
Puerto Rico); y en la RD, IMERG − CHIRPS nacional mensual de forma_cambio.py (CHIRPS es testigo, no pluviómetro).
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.era_gpm
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..hr.common import ROOT, write_json

OUT = ROOT / "results" / "tropical" / "era_gpm"
H = ROOT / "results" / "tropical" / "hawaii"
TRAMOS = {"trmm": ("2001-01", "2013-12"), "gpm_antes_2018": ("2015-01", "2017-11"), "despues": ("2018-02", "2024-12")}
PREDICCIONES = {
    "G1": "En Hawái y en Puerto Rico, la media de (IMERG - pluviómetro) en 2015-01..2017-11 queda al menos 3 pp por "
          "debajo de la de 2001-01..2013-12.",
    "G2": "En Hawái y en Puerto Rico, la media de 2018-02..2024-12 difiere de la de 2015-01..2017-11 en 1,5 pp o "
          "menos (no hay un segundo escalón grande en 2018).",
    "G3": "En la RD (IMERG - CHIRPS), la caída de 2001-2013 a 2015-2017 es al menos la mitad de la caída total de "
          "2001-2013 a 2018-2024.",
    "refutacion": "Si 2015-2017 se parece a 2001-2013 y el escalón aparece en 2018, la fecha buena es 2018 y la "
                  "hipótesis de era cae.",
}


def registrar():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "predicciones_registradas.json"
    if not p.exists():
        write_json(p, {"registradas_utc": datetime.now(timezone.utc).isoformat(), **PREDICCIONES})


def tramos(s):
    s.index = pd.to_datetime(s.index).to_period("M")
    m = {k: float(s[(s.index >= pd.Period(a)) & (s.index <= pd.Period(b))].mean()) for k, (a, b) in TRAMOS.items()}
    anual = s.groupby(s.index.year).mean().round(2).to_dict()
    return m, {int(k): v for k, v in anual.items()}


def main():
    registrar()
    hi = pd.read_csv(H / "serie_mensual.csv", index_col=0).iloc[:, 0]
    pr = pd.read_csv(H / "serie_mensual_puerto_rico.csv", index_col=0).iloc[:, 0]
    rd = 100 * pd.read_csv(ROOT / "results" / "tropical" / "forma" / "serie_nacional.csv", index_col=0).iloc[:, 0]
    res = {}
    for nombre, s in (("hawaii", hi), ("puerto_rico", pr), ("rd_imerg_menos_chirps", rd)):
        m, anual = tramos(s.copy())
        res[nombre] = {"medias_pp": m, "paso_era_pp": m["gpm_antes_2018"] - m["trmm"],
                       "paso_2018_pp": m["despues"] - m["gpm_antes_2018"], "total_pp": m["despues"] - m["trmm"],
                       "medias_anuales_pp": anual}
    g1 = all(res[k]["paso_era_pp"] <= -3 for k in ("hawaii", "puerto_rico"))
    g2 = all(abs(res[k]["paso_2018_pp"]) <= 1.5 for k in ("hawaii", "puerto_rico"))
    rdr = res["rd_imerg_menos_chirps"]
    g3 = bool(rdr["total_pp"] < 0 and rdr["paso_era_pp"] <= 0.5 * rdr["total_pp"])
    res["veredicto"] = {"G1": bool(g1), "G2": bool(g2), "G3": g3}
    write_json(OUT / "resumen.json", res)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
