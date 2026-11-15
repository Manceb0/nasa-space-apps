"""Cuarto testigo, a escala nacional: MERRA-2 (PRECTOTCORR diario de NASA POWER) en las 15 celdas de 0,5° x 0,625°
que cubren la República Dominicana. Los datos YA estaban en disco (data/nacional/power/diario): no hay descarga nueva.

Pregunta: ¿IMERG pierde días de lluvia (>= 1 mm) frente a un testigo en todo el país, o solo en los 6 puntos de ERA5?
Corte prefijado: 2018-02, la fecha del escalón nacional que eligió el modelo (forma_cambio). No se busca otro.

Limites que se dicen siempre:
- MERRA-2 corregido cuelga de CPC Unified (pluviometros del GTS): comparte estaciones con CHIRPS y GPCC.
- IMERG usa campos de MERRA-2 en el morphing; no son independientes.
- Un modelo de 0,5° llovizna mucho: el NIVEL de frecuencia no es comparable, el CAMBIO si.
- El tramo mas reciente de POWER viene de GEOS FP-IT, no de MERRA-2 (por eso N4 prueba al propio testigo).
Las PREDICCIONES se escriben a disco ANTES de leer los datos.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.merra2_testigo
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..hr.common import ROOT, write_json
from ..tendencias import datos
from .era5_testigo import prueba
from .run import SEED

OUT = ROOT / "results" / "tropical" / "merra2"
SRC = ROOT / "data" / "nacional" / "power" / "diario"
CORTE = "2018-02-01"
PREDICCIONES = {
    "N1": "En al menos 10 de las 15 celdas MERRA-2, la frecuencia de dias >= 1 mm de IMERG cae mas que la de MERRA-2 "
          "(despues - antes de 2018-02).",
    "N2": "Mediana de las 15 celdas: IMERG cae al menos 4 pp y MERRA-2 cambia menos de 2 pp en valor absoluto.",
    "N3": "La diferencia mensual desestacionalizada IMERG - MERRA-2 (media nacional) tiene un punto de cambio entre "
          "2016-01 y 2019-12 con p < 0,05 (permutacion de bloques de 12 meses).",
    "N4": "Control del testigo: MERRA-2 solo NO tiene un punto de cambio significativo entre 2016-01 y 2019-12. "
          "Si lo tiene, el testigo esta comprometido y N1-N3 no pueden atribuirse a IMERG.",
    "refutacion": "Si MERRA-2 cae tanto como IMERG (N2 falla por MERRA-2) o el propio MERRA-2 salta (N4 falla), la "
                  "perdida de dias deja de ser una propiedad solo de IMERG a escala nacional.",
}


def registrar():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "predicciones_registradas.json"
    if not p.exists():
        write_json(p, {"registradas_utc": datetime.now(timezone.utc).isoformat(), **PREDICCIONES})


def leer(f):
    J = json.loads(f.read_text())
    lon, lat = J["geometry"]["coordinates"][:2]
    d = J["properties"]["parameter"]["PRECTOTCORR"]
    s = pd.Series(d, dtype=float)
    s.index = pd.to_datetime(s.index, format="%Y%m%d")
    return s.where(s >= 0), float(lat), float(lon)


def caja(P, lat, lon, hla=0.25, hlo=0.3125):
    """Media de las celdas de 0,1° ponderada por el area que comparten con la celda MERRA-2 (0,5° x 0,625°)."""
    g = datos.GRID01
    e_la = g.lat0 + g.res * np.arange(g.ny + 1)
    e_lo = g.lon0 + g.res * np.arange(g.nx + 1)
    w_la = np.clip(np.minimum(e_la[1:], lat + hla) - np.maximum(e_la[:-1], lat - hla), 0, None)
    w_lo = np.clip(np.minimum(e_lo[1:], lon + hlo) - np.maximum(e_lo[:-1], lon - hlo), 0, None)
    W = np.outer(w_la, w_lo)
    ok = np.isfinite(P)
    num = np.nansum(P * W[None], (1, 2))
    den = np.where(ok, W[None], 0).sum((1, 2))
    return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan), float(W.sum())


def main():
    registrar()
    Pi = np.load(datos.DER / "imerg_diario_01.npz")["P"].astype(float)
    Pc = np.load(datos.DER / "chirps_diario_01.npz")["P"].astype(float)
    days = pd.DatetimeIndex(datos.DAYS.astype("datetime64[D]"))
    rows, wet = [], {}
    for f in sorted(SRC.glob("PRECTOTCORR_*.json")):
        m2, la, lo = leer(f)
        bi, area = caja(Pi, la, lo)
        bc, _ = caja(Pc, la, lo)
        if area < 0.05:          # celda casi fuera de la cuadricula de 0,1°
            continue
        df = pd.DataFrame({"IMERG": bi, "CHIRPS": bc, "MERRA2": m2.reindex(days).to_numpy()}, index=days).dropna()
        n = f"{la:.2f},{lo:.3f}"
        wet[n] = (df >= 1).astype(float)
        for prod in ("IMERG", "CHIRPS", "MERRA2"):
            a = (df.loc[df.index < CORTE, prod] >= 1).mean()
            b = (df.loc[df.index >= CORTE, prod] >= 1).mean()
            rows.append({"celda": n, "lat": la, "lon": lo, "producto": prod, "frec_antes": a, "frec_despues": b,
                         "cambio_pp": 100 * (b - a), "dias": len(df)})
    T = pd.DataFrame(rows)
    T.to_csv(OUT / "cambio_frecuencia_por_celda.csv", index=False, float_format="%.4f")
    piv = T.pivot(index="celda", columns="producto", values="cambio_pp")
    W = pd.concat(wet).groupby(level=1).mean()
    m = W.groupby(W.index.to_period("M")).mean()
    rng = np.random.default_rng(SEED)
    res, series = {}, {}
    for name, s in (("IMERG_menos_MERRA2", m["IMERG"] - m["MERRA2"]), ("CHIRPS_menos_MERRA2", m["CHIRPS"] - m["MERRA2"]),
                    ("MERRA2_solo", m["MERRA2"]), ("IMERG_solo", m["IMERG"]), ("CHIRPS_solo", m["CHIRPS"])):
        res[name], series[name] = prueba(s, rng)
    pd.DataFrame(series).to_csv(OUT / "series_mensuales_desestacionalizadas.csv", float_format="%.5f")
    med = piv.median().to_dict()

    def en_ventana(r):
        return "2016-01" <= r["punto_de_cambio"] <= "2019-12"

    sig = lambda r: r["p_bloques_12m"] < 0.05 and en_ventana(r)  # noqa: E731
    veredicto = {
        "N1": bool((piv["IMERG"] < piv["MERRA2"]).sum() >= 10),
        "N2": bool(med["IMERG"] <= -4 and abs(med["MERRA2"]) < 2),
        "N3": bool(sig(res["IMERG_menos_MERRA2"])),
        "N4": bool(not sig(res["MERRA2_solo"])),
    }
    resumen = {"corte": CORTE, "celdas": int(piv.shape[0]),
               "celdas_IMERG_cae_mas_que_MERRA2": int((piv["IMERG"] < piv["MERRA2"]).sum()),
               "celdas_IMERG_cae_mas_que_CHIRPS": int((piv["IMERG"] < piv["CHIRPS"]).sum()),
               "cambio_mediano_pp": med, "cambio_medio_pp": piv.mean().to_dict(),
               "pettitt": res, "veredicto": veredicto}
    write_json(OUT / "resumen.json", resumen)
    print(piv.round(2).to_string())
    print(json.dumps(resumen, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
