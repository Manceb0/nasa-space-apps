"""Tercer testigo del escalón de IMERG (2013-10): ERA5, que no comparte el algoritmo de IMERG ni los pluviómetros
que alimentan a CHIRPS. ERA5 diario (models=era5, día UTC como IMERG) de la API de archivo de Open-Meteo, sin cuenta.

Las PREDICCIONES se escriben a disco ANTES de descargar nada. Si ERA5 también pierde días de lluvia en 2013, la
hipótesis «cambió el contador de IMERG» se debilita y se dice así.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.era5_testigo
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..hr.common import ROOT, write_json
from ..tendencias import datos
from .run import SEED, pettitt

OUT = ROOT / "results" / "tropical" / "era5"
CACHE = ROOT / "data" / "tropical" / "era5"
CORTE = "2013-10-01"
# centros de celda ERA5 (0,25°) sobre tierra: las 4 estaciones GHCN-D y 2 puntos de montaña del interior
PUNTOS = {
    "Santo Domingo": (18.50, -69.75), "Punta Cana": (18.50, -68.50), "Puerto Plata": (19.75, -70.50),
    "Barahona": (18.25, -71.00), "Santiago": (19.50, -70.75), "Constanza": (19.00, -70.75),
}
PREDICCIONES = {
    "E1": "La serie mensual desestacionalizada de frecuencia de días húmedos IMERG − ERA5 tiene un punto de cambio "
          "entre 2012-10 y 2014-12 con p < 0,05 (permutación de bloques de 12 meses).",
    "E2": "En ERA5 la frecuencia de días húmedos después − antes de 2013-10 cambia menos de 2 pp (media de puntos), "
          "mientras IMERG baja al menos 4 pp en los mismos puntos.",
    "E3": "CHIRPS − ERA5 no tiene un punto de cambio significativo (p ≥ 0,05) entre 2012-10 y 2014-12.",
    "E4": "En la CANTIDAD de lluvia (log IMERG/ERA5) no hay un salto significativo en esa ventana.",
    "refutacion": "Si ERA5 baja tanto como IMERG (E2 falla) o CHIRPS − ERA5 salta igual (E3 falla), el escalón no es "
                  "solo de IMERG.",
}


def registrar():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "predicciones_registradas.json"
    if not p.exists():
        write_json(p, {"registradas_utc": datetime.now(timezone.utc).isoformat(), **PREDICCIONES})


def bajar(nombre, lat, lon):
    """Un año por petición (la API cuenta como varias llamadas los periodos de más de 2 semanas)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    partes = []
    for y in range(2001, 2025):
        f = CACHE / f"{nombre.replace(' ', '_')}_{y}.json"
        if not f.exists():
            url = ("https://archive-api.open-meteo.com/v1/archive?"
                   f"latitude={lat}&longitude={lon}&start_date={y}-01-01&end_date={y}-12-31"
                   "&daily=precipitation_sum&models=era5&timezone=GMT")
            for intento in range(30):
                try:
                    with urllib.request.urlopen(url, timeout=120) as r:
                        f.write_bytes(r.read())
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        print(f"  límite de la API; espero 60 s ({nombre} {y})", flush=True)
                        time.sleep(60)
                        continue
                    raise
                except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                    print(f"  fallo de red ({e}); reintento en 10 s ({nombre} {y})", flush=True)
                    time.sleep(10)
            time.sleep(1.5)
        J = json.loads(f.read_text())
        d = J["daily"]
        partes.append(pd.Series(d["precipitation_sum"], index=pd.to_datetime(d["time"]), dtype=float))
    print(f"ERA5 listo: {nombre}", flush=True)
    # la API puede devolver otra celda (elige una adecuada a tierra): se usa la coordenada DEVUELTA
    return pd.concat(partes), float(J["latitude"]), float(J["longitude"]), J.get("elevation")


def caja(P, lat, lon, half=0.125):
    """Media de las celdas de 0,1° ponderada por el área que comparten con la celda ERA5 de 0,25°."""
    g = datos.GRID01
    e_la = g.lat0 + g.res * np.arange(g.ny + 1)
    e_lo = g.lon0 + g.res * np.arange(g.nx + 1)
    w_la = np.clip(np.minimum(e_la[1:], lat + half) - np.maximum(e_la[:-1], lat - half), 0, None)
    w_lo = np.clip(np.minimum(e_lo[1:], lon + half) - np.maximum(e_lo[:-1], lon - half), 0, None)
    W = np.outer(w_la, w_lo)
    X = P * W[None]
    ok = np.isfinite(P)
    return np.nansum(X, (1, 2)) / np.where(ok, W[None], 0).sum((1, 2))


def prueba(s, rng):
    s = s - s.groupby(s.index.month).transform("mean")
    x = s.to_numpy()
    k, K = pettitt(x)
    blocks = x[: (x.size // 12) * 12].reshape(-1, 12)
    null = [pettitt(blocks[rng.permutation(blocks.shape[0])].ravel())[1] for _ in range(2999)]
    return {"punto_de_cambio": str(s.index[k]), "p_bloques_12m": float((1 + np.sum(np.asarray(null) >= K)) / 3000),
            "media_antes": float(x[:k].mean()), "media_despues": float(x[k:].mean())}, s


def main():
    registrar()
    Pi = np.load(datos.DER / "imerg_diario_01.npz")["P"].astype(float)
    Pc = np.load(datos.DER / "chirps_diario_01.npz")["P"].astype(float)
    days = pd.DatetimeIndex(datos.DAYS.astype("datetime64[D]"))
    rows, wet, coords = [], {}, {}
    for n, (la0, lo0) in PUNTOS.items():
        e, la, lo, elev = bajar(n, la0, lo0)
        e = e.reindex(days)
        coords[n] = {"pedida": [la0, lo0], "devuelta": [la, lo], "elevacion_m": elev}
        df = pd.DataFrame({"IMERG": caja(Pi, la, lo), "CHIRPS": caja(Pc, la, lo), "ERA5": e.to_numpy()}, index=days)
        df = df.dropna()
        wet[n] = (df >= 1).astype(float)
        wet[n]["amt_I"], wet[n]["amt_E"] = df["IMERG"], df["ERA5"]
        for prod in ("IMERG", "CHIRPS", "ERA5"):
            a = (df.loc[df.index < CORTE, prod] >= 1).mean()
            b = (df.loc[df.index >= CORTE, prod] >= 1).mean()
            rows.append({"punto": n, "producto": prod, "frec_antes": a, "frec_despues": b,
                         "cambio_pp": 100 * (b - a)})
    T = pd.DataFrame(rows)
    T.to_csv(OUT / "cambio_frecuencia_por_punto.csv", index=False, float_format="%.4f")
    W = pd.concat(wet).groupby(level=1).mean()                       # media de los puntos, por día
    m = W.groupby(W.index.to_period("M")).mean()
    rng = np.random.default_rng(SEED)
    res, series = {}, {}
    for name, s in (("IMERG_menos_ERA5", m["IMERG"] - m["ERA5"]), ("CHIRPS_menos_ERA5", m["CHIRPS"] - m["ERA5"]),
                    ("ERA5_solo", m["ERA5"]), ("IMERG_solo", m["IMERG"]),
                    ("log_cantidad_IMERG_sobre_ERA5", np.log(m["amt_I"] / m["amt_E"]))):
        res[name], series[name] = prueba(s, rng)
    pd.DataFrame(series).to_csv(OUT / "series_mensuales_desestacionalizadas.csv", float_format="%.5f")
    med = T.groupby("producto")["cambio_pp"].mean().to_dict()

    def en_ventana(r):
        return "2012-10" <= r["punto_de_cambio"] <= "2014-12"

    veredicto = {
        "E1": bool(res["IMERG_menos_ERA5"]["p_bloques_12m"] < 0.05 and en_ventana(res["IMERG_menos_ERA5"])),
        "E2": bool(abs(med["ERA5"]) < 2 and med["IMERG"] <= -4),
        "E3": bool(not (res["CHIRPS_menos_ERA5"]["p_bloques_12m"] < 0.05 and en_ventana(res["CHIRPS_menos_ERA5"]))),
        "E4": bool(not (res["log_cantidad_IMERG_sobre_ERA5"]["p_bloques_12m"] < 0.05
                        and en_ventana(res["log_cantidad_IMERG_sobre_ERA5"]))),
    }
    mediana = T.groupby("producto")["cambio_pp"].median().to_dict()
    write_json(OUT / "resumen.json", {"puntos": coords, "corte": CORTE, "pettitt": res,
                                      "cambio_medio_pp": med, "cambio_mediano_pp": mediana, "veredicto": veredicto})
    print(T.round(3).to_string())
    print(json.dumps({"pettitt": res, "cambio_medio_pp": med, "veredicto": veredicto}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
