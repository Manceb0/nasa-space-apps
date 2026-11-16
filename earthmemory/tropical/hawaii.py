"""Experimento natural para la causa: Hawái, bajo GOES-West.

En la RD y en Puerto Rico, IMERG pierde días de lluvia ligera desde ~2018-02 frente a pluviómetros que no cambian.
Dos sospechosos entraron con 19 días de diferencia y no se pueden separar allí:
  - el ATMS de NOAA-20 (microondas, órbita polar: llega a TODO el planeta) desde 2017-11-29;
  - el GOES-16 como GOES-East (infrarrojo geoestacionario: solo el lado este) desde 2017-12-18.
Hawái tiene muchos pluviómetros en GHCN-D y está bajo GOES-West (GOES-15 hasta 2019-02-12, luego GOES-17).
Si IMERG pierde días también en Hawái con el mismo corte, la causa es global; si no, apunta al GOES-East.

Mismo método que puerto_rico.py (celda IMERG que contiene la estación, umbrales 0,1 / 1 / 5 mm, al menos 70 % de
días en cada tramo). Además, el momento del cambio: punto de cambio de Pettitt sobre la serie mensual de la mediana
entre estaciones de (frecuencia IMERG − frecuencia pluviómetro), en Hawái y en Puerto Rico.
Las PREDICCIONES se escriben antes de descargar.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.hawaii
Prueba de humo (un solo archivo): ... python -m earthmemory.tropical.hawaii --prueba
"""

from __future__ import annotations

import gzip
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .. import earthdata as ed
from ..hr.common import ROOT, write_json
from ..power import Manifest

OUT = ROOT / "results" / "tropical" / "hawaii"
DDIR = ROOT / "data" / "tropical" / "hawaii"
DDIR_PR = ROOT / "data" / "tropical" / "puerto_rico"
INV = DDIR_PR / "ghcnd-inventory.txt"
BBOX = (-160.30, 18.85, -154.75, 22.30)    # lon0, lat0, lon1, lat1 (convención de earthdata.bbox_to_edges)
BBOX_PR = (-67.30, 17.85, -65.55, 18.55)
CORTE = "2018-02-01"
PREDICCIONES = {
    "HI_global": "Si la causa es global (ATMS de NOAA-20 u otro cambio de la constelación de microondas), en Hawái "
                 "IMERG también pierde días frente a los pluviómetros con el corte 2018-02: mediana de (cambio IMERG - "
                 "cambio pluviómetro) a 1 mm <= -3 pp, y IMERG cae más en al menos 2 de cada 3 estaciones.",
    "HI_goes_east": "Si la causa es el GOES-16 (solo GOES-East), en Hawái esa mediana queda entre -1,5 y +1,5 pp.",
    "HI_zona_gris": "Entre -3 y -1,5 pp, o fuera de +1,5: no concluyente; se dice así.",
    "HI_momento": "Punto de cambio (Pettitt) de la serie mensual de la mediana (IMERG - pluviómetro) a 1 mm en Hawái: "
                  "con causa global, entre 2017-06 y 2018-12; si cae entre 2019-01 y 2019-12, apunta al GOES-17.",
    "PR_momento": "Control: en Puerto Rico ese punto de cambio cae entre 2017-06 y 2018-12 (ambas causas lo predicen).",
    "pluviometros_hawaii": "Los pluviómetros de Hawái cambian poco: mediana de su cambio a 1 mm entre -2 y +2 pp. Si "
                           "no, el corte no aísla al instrumento y se dice.",
}


def registrar():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "predicciones_registradas.json"
    if not p.exists():
        write_json(p, {"registradas_utc": datetime.now(timezone.utc).isoformat(), "corte": CORTE, **PREDICCIONES})


def bajar(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        with urllib.request.urlopen(url, timeout=300) as r:
            dest.write_bytes(r.read())
    return dest


def estaciones(bbox):
    bajar("https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt", INV)
    lon0, lat0, lon1, lat1 = bbox
    rows = []
    for line in INV.read_text().splitlines():
        if line[31:35] != "PRCP":
            continue
        lat, lon = float(line[12:20]), float(line[21:30])
        if lat0 <= lat <= lat1 and lon0 <= lon <= lon1:
            rows.append({"id": line[:11], "lat": lat, "lon": lon, "y0": int(line[36:40]), "y1": int(line[41:45])})
    st = pd.DataFrame(rows)
    return st[(st.y0 <= 2005) & (st.y1 >= 2024)]


def serie_estacion(sid, ddir):
    f = bajar(f"https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/{sid}.csv.gz", ddir / "ghcnd" / f"{sid}.csv.gz")
    df = pd.read_csv(io.BytesIO(gzip.decompress(f.read_bytes())), header=None,
                     names=["id", "fecha", "elem", "val", "m", "q", "s", "t"], dtype={"fecha": str, "q": str})
    df = df[(df.elem == "PRCP") & (df.q.isna())]
    return pd.Series(df.val.to_numpy() / 10.0, index=pd.to_datetime(df.fecha, format="%Y%m%d"))


def imerg(ddir, bbox, prueba=False):
    jobs = ed.imerg_daily_jobs(ddir, bbox, 2001, 2024)
    if prueba:
        jobs = jobs[:1]

    def respaldo(u, d):
        return next((x["url_respaldo"] for uu, dd, x in jobs if dd == d), None)
    res = ed.fetch_many(jobs, Manifest(ddir / "MANIFEST.json"), workers=8, log_every=500, fallback=respaldo)
    print({k: (v if k != "errores" else len(v)) for k, v in res.items()}, flush=True)
    cubo, dias, lat, lon = [], [], None, None
    for _, d, x in jobs:
        if not d.exists():
            continue
        a, lat, lon, _ = ed.read_subset(d, "precipitation")
        cubo.append(a)
        dias.append(pd.Timestamp(x["granulo"].split(".")[4][:8]))
    return np.stack(cubo), pd.DatetimeIndex(dias), lat, lon


def pettitt(x):
    """Punto de cambio de Pettitt: índice del último valor del primer tramo, estadístico K y p aproximado."""
    x = np.asarray(x, float)
    n = len(x)
    s = np.sign(x[:, None] - x[None, :])
    u = np.array([s[: t + 1, t + 1:].sum() for t in range(n - 1)])
    t = int(np.abs(u).argmax())
    k = float(np.abs(u[t]))
    p = float(min(1.0, 2 * np.exp(-6 * k ** 2 / (n ** 3 + n ** 2))))
    return t, k, p


def analizar(region, ddir, bbox, prueba=False):
    st = estaciones(bbox)
    print(region, "estaciones candidatas:", len(st), flush=True)
    P, dias, lat, lon = imerg(ddir, bbox, prueba)
    if prueba:
        print("prueba OK:", P.shape, dias[0].date(), float(np.nanmax(P)))
        return None
    filas, mensual = [], {}
    for s in st.itertuples():
        try:
            g = serie_estacion(s.id, ddir)
        except Exception as e:  # noqa: BLE001
            print("sin serie", s.id, e)
            continue
        i, j = int(np.abs(lat - s.lat).argmin()), int(np.abs(lon - s.lon).argmin())
        if abs(lat[i] - s.lat) > 0.06 or abs(lon[j] - s.lon) > 0.06:
            continue
        df = pd.DataFrame({"g": g, "i": pd.Series(P[:, i, j], index=dias)}).dropna()
        df = df[(df.index >= "2001-01-01") & (df.index <= "2024-12-31")]
        a, b = df[df.index < CORTE], df[df.index >= CORTE]
        if len(a) < 0.7 * 6240 or len(b) < 0.7 * 2525:     # al menos 70 % de los días en cada tramo
            continue
        fila = {"estacion": s.id, "lat": s.lat, "lon": s.lon, "dias_antes": len(a), "dias_despues": len(b)}
        for th in (0.1, 1.0, 5.0):
            fila[f"cambio_pluvio_pp_{th}"] = 100 * ((b.g >= th).mean() - (a.g >= th).mean())
            fila[f"cambio_imerg_pp_{th}"] = 100 * ((b.i >= th).mean() - (a.i >= th).mean())
        filas.append(fila)
        m = df.assign(dg=(df.g >= 1.0), di=(df.i >= 1.0)).resample("MS").agg({"dg": ["mean", "count"], "di": "mean"})
        m.columns = ["fg", "n", "fi"]
        m = m[m.n >= 20]
        mensual[s.id] = 100 * (m.fi - m.fg)
    T = pd.DataFrame(filas)
    M = pd.DataFrame(mensual)
    serie = M.median(axis=1).dropna()
    t, k, p = pettitt(serie.to_numpy())
    d1 = T["cambio_imerg_pp_1.0"] - T["cambio_pluvio_pp_1.0"]
    return T, serie, {"estaciones": int(len(T)), "corte": CORTE,
                      "imerg_cae_mas": int((d1 < 0).sum()),
                      "mediana_cambio_pp": {c: float(T[c].median()) for c in T.columns if c.startswith("cambio")},
                      "mediana_diferencia_1mm_pp": float(d1.median()),
                      "punto_cambio": {"ultimo_mes_antes": str(serie.index[t].date())[:7],
                                       "primer_mes_despues": str(serie.index[t + 1].date())[:7],
                                       "K": k, "p_aprox": p, "meses": int(len(serie)),
                                       "media_antes_pp": float(serie.iloc[: t + 1].mean()),
                                       "media_despues_pp": float(serie.iloc[t + 1:].mean())}}


def en(fecha, a, b):
    return a <= fecha <= b


def main():
    prueba = "--prueba" in sys.argv
    registrar()
    r = analizar("hawaii", DDIR, BBOX, prueba)
    if r is None:
        return
    T, serie, res = r
    T.to_csv(OUT / "cambio_por_estacion.csv", index=False, float_format="%.3f")
    serie.rename("mediana_imerg_menos_pluvio_pp").to_csv(OUT / "serie_mensual.csv", float_format="%.3f")
    _, serie_pr, res_pr = analizar("puerto_rico", DDIR_PR, BBOX_PR)
    serie_pr.rename("mediana_imerg_menos_pluvio_pp").to_csv(OUT / "serie_mensual_puerto_rico.csv", float_format="%.3f")
    d, n = res["mediana_diferencia_1mm_pp"], res["estaciones"]
    pc, pc_pr = res["punto_cambio"]["primer_mes_despues"], res_pr["punto_cambio"]["primer_mes_despues"]
    res["veredicto"] = {
        "HI_global": bool(n and d <= -3 and res["imerg_cae_mas"] >= np.ceil(2 * n / 3)),
        "HI_goes_east": bool(n and -1.5 <= d <= 1.5),
        "HI_zona_gris": bool(n and (-3 < d < -1.5 or d > 1.5)),
        "HI_momento": ("no significativo" if res["punto_cambio"]["p_aprox"] >= 0.05 else
                       f"{pc}: apunta a causa global" if en(pc, "2017-06", "2018-12") else
                       f"{pc}: apunta al GOES-17" if en(pc, "2019-01", "2019-12") else f"{pc}: fuera de ambas ventanas"),
        "PR_momento": bool(res_pr["punto_cambio"]["p_aprox"] < 0.05 and en(pc_pr, "2017-06", "2018-12")),
        "pluviometros_hawaii": bool(n and abs(res["mediana_cambio_pp"]["cambio_pluvio_pp_1.0"]) <= 2),
    }
    res["puerto_rico_punto_cambio"] = res_pr["punto_cambio"]
    write_json(OUT / "resumen.json", res)
    print(T.round(2).to_string())
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
