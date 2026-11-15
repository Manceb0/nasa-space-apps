"""Réplica independiente en Puerto Rico: la isla vecina, bajo el mismo GOES-East, con muchos pluviómetros en GHCN-D
(COOP y CoCoRaHS). Si IMERG pierde días de lluvia frente a pluviómetros densos también allí, la conclusión deja de
depender de 4 estaciones dominicanas y deja de ser una rareza de la RD.

IMERG V07 Final diario (OPeNDAP, recorte de la caja de PR) y GHCN-D (NOAA NCEI, por estación).
Corte prefijado: 2018-02 (el de la RD). Día IMERG en UTC; el día del pluviómetro termina a su hora de lectura: sobre
años, el desfase no cambia la frecuencia de días húmedos.
Las PREDICCIONES se escriben antes de descargar.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.puerto_rico
"""

from __future__ import annotations

import gzip
import io
import json
import urllib.request
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .. import earthdata as ed
from ..hr.common import ROOT, write_json
from ..power import Manifest

OUT = ROOT / "results" / "tropical" / "puerto_rico"
DDIR = ROOT / "data" / "tropical" / "puerto_rico"
BBOX = (-67.30, 17.85, -65.55, 18.55)      # lon0, lat0, lon1, lat1 (convención de earthdata.bbox_to_edges)
CORTE = "2018-02-01"
PREDICCIONES = {
    "PR1": "En al menos 2 de cada 3 pluviómetros de PR con registro completo, la frecuencia de días >= 1 mm de IMERG "
           "(celda que contiene la estación) cae más que la del pluviómetro (después - antes de 2018-02).",
    "PR2": "Mediana de (cambio IMERG - cambio pluviómetro) <= -3 pp.",
    "PR3": "Los pluviómetros cambian poco: mediana de su cambio entre -2 y +2 pp.",
    "refutacion": "Si los pluviómetros de PR caen tanto como IMERG, la pérdida de días no es del instrumento sino de la "
                  "lluvia (o común a la región), y la conclusión de la RD se debilita.",
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


def estaciones():
    inv = bajar("https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt", DDIR / "ghcnd-inventory.txt")
    rows = []
    for line in inv.read_text().splitlines():
        if line.startswith("RQ") and line[31:35] == "PRCP":
            rows.append({"id": line[:11], "lat": float(line[12:20]), "lon": float(line[21:30]),
                         "y0": int(line[36:40]), "y1": int(line[41:45])})
    st = pd.DataFrame(rows)
    return st[(st.y0 <= 2005) & (st.y1 >= 2024)]


def serie_estacion(sid):
    f = bajar(f"https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/{sid}.csv.gz", DDIR / "ghcnd" / f"{sid}.csv.gz")
    df = pd.read_csv(io.BytesIO(gzip.decompress(f.read_bytes())), header=None,
                     names=["id", "fecha", "elem", "val", "m", "q", "s", "t"], dtype={"fecha": str, "q": str})
    df = df[(df.elem == "PRCP") & (df.q.isna())]
    return pd.Series(df.val.to_numpy() / 10.0, index=pd.to_datetime(df.fecha, format="%Y%m%d"))


def imerg():
    jobs = ed.imerg_daily_jobs(DDIR, BBOX, 2001, 2024)

    def respaldo(u, d):
        return next((x["url_respaldo"] for uu, dd, x in jobs if dd == d), None)
    res = ed.fetch_many(jobs, Manifest(DDIR / "MANIFEST.json"), workers=8, log_every=500, fallback=respaldo)
    print({k: (v if k != "errores" else len(v)) for k, v in res.items()}, flush=True)
    cubo, dias, lat, lon = [], [], None, None
    for _, d, x in jobs:
        if not d.exists():
            continue
        a, lat, lon, _ = ed.read_subset(d, "precipitation")
        cubo.append(a)
        dias.append(pd.Timestamp(x["granulo"].split(".")[4][:8]))
    return np.stack(cubo), pd.DatetimeIndex(dias), lat, lon


def main():
    registrar()
    st = estaciones()
    P, dias, lat, lon = imerg()
    filas = []
    for s in st.itertuples():
        try:
            g = serie_estacion(s.id)
        except Exception as e:  # noqa: BLE001
            print("sin serie", s.id, e)
            continue
        i, j = int(np.abs(lat - s.lat).argmin()), int(np.abs(lon - s.lon).argmin())
        if abs(lat[i] - s.lat) > 0.06 or abs(lon[j] - s.lon) > 0.06:
            continue
        im = pd.Series(P[:, i, j], index=dias)
        df = pd.DataFrame({"g": g, "i": im}).dropna()
        df = df[(df.index >= "2001-01-01") & (df.index <= "2024-12-31")]
        a, b = df[df.index < CORTE], df[df.index >= CORTE]
        if len(a) < 0.7 * 6240 or len(b) < 0.7 * 2525:     # al menos 70 % de los días en cada tramo
            continue
        fila = {"estacion": s.id, "lat": s.lat, "lon": s.lon, "dias_antes": len(a), "dias_despues": len(b)}
        for th in (0.1, 1.0, 5.0):
            fila[f"cambio_pluvio_pp_{th}"] = 100 * ((b.g >= th).mean() - (a.g >= th).mean())
            fila[f"cambio_imerg_pp_{th}"] = 100 * ((b.i >= th).mean() - (a.i >= th).mean())
        filas.append(fila)
    T = pd.DataFrame(filas)
    T.to_csv(OUT / "cambio_por_estacion.csv", index=False, float_format="%.3f")
    d1 = T["cambio_imerg_pp_1.0"] - T["cambio_pluvio_pp_1.0"]
    res = {"estaciones": int(len(T)), "corte": CORTE,
           "imerg_cae_mas": int((d1 < 0).sum()),
           "mediana_cambio_pp": {c: float(T[c].median()) for c in T.columns if c.startswith("cambio")},
           "mediana_diferencia_1mm_pp": float(d1.median()),
           "veredicto": {"PR1": bool(len(T) and (d1 < 0).sum() >= np.ceil(2 * len(T) / 3)),
                         "PR2": bool(len(T) and d1.median() <= -3),
                         "PR3": bool(len(T) and abs(T["cambio_pluvio_pp_1.0"].median()) <= 2)}}
    write_json(OUT / "resumen.json", res)
    print(T.round(2).to_string())
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
