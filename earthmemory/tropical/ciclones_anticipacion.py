"""¿Cuántas inundaciones del Yuna vinieron de un ciclón, y con cuánta antelación las anunció el pronóstico OFICIAL del
NHC tal como se emitió? Archivo ATCF a-deck (ftp.nhc.noaa.gov/atcf/archive), registros TECH = OFCL: la trayectoria
pronosticada en cada aviso, con su hora de emisión. Es el pronóstico que existía en ese momento, no una reconstrucción.

Regla fija antes de mirar (pre-alerta de ciclón): se dispara en el primer aviso OFCL cuya trayectoria, entre 12 y
120 h, pase a menos de R = 200 km del centro de la cuenca del Yuna. Sensibilidad a 100 y 300 km.
Inicio de la inundación: 04 UTC del día de inicio del catálogo (medianoche local), lo más temprano posible: la
antelación medida es la mínima. Catálogo de prensa: las falsas alarmas son una cota superior.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.ciclones_anticipacion
"""

from __future__ import annotations

import gzip
import json
import time
import urllib.request
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..hr.common import ROOT, write_json

OUT = ROOT / "results" / "tropical" / "ciclones"
CACHE = ROOT / "data" / "tropical" / "nhc_adeck"
IBT = ROOT / "data" / "tropical" / "ibtracs" / "ibtracs.NA.list.v04r01.csv"
CAT = ROOT / "results" / "yuna" / "catalogo_eventos.csv"
YUNA = (19.10, -70.10)
R = 200.0
PREDICCIONES = {
    "C1": "Al menos la mitad de las 14 inundaciones del catálogo 2001-2024 coinciden con un ciclón tropical a menos de "
          "500 km de la cuenca (IBTrACS) entre 3 días antes y 1 día después del inicio.",
    "C2": "En al menos 2 de cada 3 inundaciones con ciclón, el primer aviso oficial del NHC que pone el centro a menos "
          "de 200 km de la cuenca se emitió 48 h o más antes del inicio.",
    "C3": "Más de la mitad de las tormentas cuyo pronóstico oficial pasó a menos de 200 km no tienen inundación del "
          "Yuna en el catálogo (la pre-alerta de ciclón tiene muchas falsas alarmas).",
}


def registrar():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "predicciones_registradas.json"
    if not p.exists():
        write_json(p, {"registradas_utc": datetime.now(timezone.utc).isoformat(), "R_km": R, **PREDICCIONES})


def dist(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(np.radians, (la1, lo1, la2, lo2))
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def ibtracs():
    df = pd.read_csv(IBT, skiprows=[1], usecols=["SID", "SEASON", "NAME", "ISO_TIME", "LAT", "LON", "USA_ATCF_ID"],
                     low_memory=False, keep_default_na=False)
    df = df[(df.SEASON.astype(int) >= 2001) & (df.SEASON.astype(int) <= 2024)].copy()
    df["t"] = pd.to_datetime(df.ISO_TIME)
    df["LAT"], df["LON"] = df.LAT.astype(float), df.LON.astype(float)
    df["d"] = dist(df.LAT, df.LON, *YUNA)
    return df


def adeck(atcf):
    """atcf = 'AL072022' -> registros OFCL: emisión, tau, lat, lon."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"a{atcf.lower()}.dat.gz"
    if not f.exists():
        url = f"https://ftp.nhc.noaa.gov/atcf/archive/{atcf[4:]}/a{atcf.lower()}.dat.gz"
        for intento in range(5):
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    f.write_bytes(r.read())
                break
            except Exception as e:  # noqa: BLE001
                print(f"  reintento {atcf}: {e}", flush=True)
                time.sleep(5)
        else:
            return pd.DataFrame()
        time.sleep(0.5)
    rows = []
    for line in gzip.open(f, "rt", errors="replace"):
        p = [x.strip() for x in line.split(",")]
        if len(p) < 8 or p[4] != "OFCL":
            continue
        try:
            tau = int(p[5])
            la = int(p[6][:-1]) / 10 * (1 if p[6][-1] == "N" else -1)
            lo = int(p[7][:-1]) / 10 * (-1 if p[7][-1] == "W" else 1)
        except ValueError:
            continue
        rows.append((pd.to_datetime(p[2], format="%Y%m%d%H"), tau, la, lo))
    d = pd.DataFrame(rows, columns=["emision", "tau", "lat", "lon"]).drop_duplicates()
    d["d"] = dist(d.lat, d.lon, *YUNA)
    return d


def primer_aviso(ad, radio):
    x = ad[(ad.tau >= 12) & (ad.tau <= 120) & (ad.d < radio)]
    return (x.emision.min(), x.loc[x.emision == x.emision.min(), "d"].min()) if len(x) else (pd.NaT, np.nan)


def main():
    registrar()
    ib = ibtracs()
    cat = pd.read_csv(CAT)
    cat = cat[cat.usable_backtest.astype(str) == "True"].copy()
    cat["inicio_utc"] = pd.to_datetime(cat.inicio) + pd.Timedelta(hours=4)
    # tormentas cuyo centro real pasó a < 800 km: candidatas a que su PRONÓSTICO pasara a < 300 km
    cerca = ib[ib.d < 800].groupby("SID").agg(nombre=("NAME", "first"), atcf=("USA_ATCF_ID", "first"),
                                              dmin=("d", "min"), t0=("t", "min"), t1=("t", "max"))
    cerca = cerca[cerca.atcf.str.len() == 8]
    ads = {r.atcf: adeck(r.atcf) for r in cerca.itertuples()}
    # 1) cada inundación: ¿ciclón cerca? ¿con cuánta antelación lo anunció el NHC?
    filas = []
    for e in cat.itertuples():
        w = ib[(ib.t >= e.inicio_utc - pd.Timedelta(days=3)) & (ib.t <= e.inicio_utc + pd.Timedelta(days=1))
               & (ib.d < 500)]
        fila = {"id": e.id, "inicio": e.inicio, "nombre_catalogo": e.nombre, "ciclon": None, "dist_min_real_km": None}
        if len(w):
            sid = w.sort_values("d").SID.iloc[0]
            c = cerca.loc[sid] if sid in cerca.index else None
            fila["ciclon"] = w.loc[w.SID == sid, "NAME"].iloc[0]
            fila["dist_min_real_km"] = round(float(w.loc[w.SID == sid, "d"].min()))
            if c is not None and c.atcf in ads and len(ads[c.atcf]):
                for radio in (100, 200, 300):
                    t, dm = primer_aviso(ads[c.atcf], radio)
                    fila[f"antelacion_h_R{radio}"] = (None if pd.isna(t)
                                                     else round((e.inicio_utc - t).total_seconds() / 3600))
                    if radio == 200:
                        fila["primer_aviso_R200_utc"] = None if pd.isna(t) else str(t)
        filas.append(fila)
    E = pd.DataFrame(filas)
    E.to_csv(OUT / "inundaciones_y_ciclones.csv", index=False)
    # 2) cada tormenta cuyo pronóstico pasó a < R: ¿hubo inundación catalogada?
    tor = []
    for r in cerca.itertuples():
        ad = ads.get(r.atcf)
        if ad is None or not len(ad):
            continue
        for radio in (100, 200, 300):
            t, dm = primer_aviso(ad, radio)
            if pd.isna(t):
                continue
            fin = ad.emision.max() + pd.Timedelta(days=5)
            hit = cat[(cat.inicio_utc >= t - pd.Timedelta(days=1)) & (cat.inicio_utc <= fin)]
            tor.append({"R_km": radio, "tormenta": r.nombre, "atcf": r.atcf, "primer_aviso_utc": str(t),
                        "dist_real_min_km": round(r.dmin), "inundacion": ";".join(hit.id) or None})
    T = pd.DataFrame(tor)
    T.to_csv(OUT / "tormentas_pronosticadas_cerca.csv", index=False)
    cic = E[E.ciclon.notna()]
    ant = cic["antelacion_h_R200"].dropna()
    t200 = T[T.R_km == 200]
    sens = {int(k): {"tormentas": int(len(g)), "con_inundacion": int(g.inundacion.notna().sum())}
            for k, g in T.groupby("R_km")}
    res = {
        "inundaciones": int(len(E)), "con_ciclon_500km": int(len(cic)),
        "antelacion_h_R200": cic.set_index("id")["antelacion_h_R200"].to_dict(),
        "con_aviso_48h_o_mas": int((ant >= 48).sum()), "con_aviso_cualquiera": int(ant.notna().sum()),
        "tormentas_por_radio": sens,
        "veredicto": {
            "C1": bool(len(cic) >= len(E) / 2),
            "C2": bool(len(cic) > 0 and (ant >= 48).sum() >= np.ceil(2 * len(cic) / 3)),
            "C3": bool(len(t200) > 0 and t200.inundacion.isna().sum() > len(t200) / 2),
        },
    }
    write_json(OUT / "resumen.json", res)
    print(E.to_string())
    print(t200.to_string())
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
