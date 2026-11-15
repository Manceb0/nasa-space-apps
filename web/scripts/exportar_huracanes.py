"""Huracanes del Yuna para la web: trayectoria observada (IBTrACS v04r01), el primer pronóstico oficial del NHC que
puso el centro a menos de 200 km de la cuenca (a-deck OFCL tal como se emitió) y el viento a 10 m de ERA5 cada 6 h
en una rejilla de 0,5° alrededor de La Española (Open-Meteo, archivo histórico de ERA5).

Solo biblioteca estándar. Los ciclones y sus fechas salen de results/tropical/ciclones/inundaciones_y_ciclones.csv.
Ejecutar (Docker, desde la raíz del repo):
  MSYS_NO_PATHCONV=1 docker compose run --rm -v "$(pwd -W)/web:/app/web" \
    -v "$(pwd -W)/data/tropical/era5_viento:/app/cache" --entrypoint "uv run --frozen --no-sync python web/scripts/exportar_huracanes.py" galeria
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IBT = ROOT / "data" / "tropical" / "ibtracs" / "ibtracs.NA.list.v04r01.csv"
ADECK = ROOT / "data" / "tropical" / "nhc_adeck"
FLOODS = ROOT / "results" / "tropical" / "ciclones" / "inundaciones_y_ciclones.csv"
OUT = ROOT / "web" / "public" / "data" / "huracanes"
CACHE = Path("/app/cache") if Path("/app/cache").exists() else ROOT / "data" / "tropical" / "era5_viento"
YUNA = (19.10, -70.10)
R_KM = 200.0
LON0, LON1, LAT0, LAT1, STEP = -80.0, -60.0, 13.0, 27.0, 0.5
BOX = (-86.0, -54.0, 9.0, 31.0)  # recorte de la trayectoria


def dist(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(math.radians, (la1, lo1, la2, lo2))
    a = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def floods():
    out = []
    for r in csv.DictReader(open(FLOODS, encoding="utf-8")):
        if r["ciclon"]:
            out.append({"id": r["id"], "name": r["ciclon"], "onset": r["inicio"],
                        "lead_h": float(r["antelacion_h_R200"]) if r["antelacion_h_R200"] else None,
                        "alert_utc": r["primer_aviso_R200_utc"] or None, "dmin_km": float(r["dist_min_real_km"])})
    return out


def track(name, season):
    pts, atcf = [], None
    with open(IBT, encoding="utf-8") as f:
        rd = csv.DictReader(f)
        next(rd)  # fila de unidades
        for r in rd:
            if r["SEASON"] != season or r["NAME"] != name:
                continue
            la, lo = float(r["LAT"]), float(r["LON"])
            atcf = atcf or r["USA_ATCF_ID"]
            if not (BOX[0] <= lo <= BOX[1] and BOX[2] <= la <= BOX[3]):
                continue
            w, pr = r["USA_WIND"].strip(), (r["USA_PRES"].strip() or r["WMO_PRES"].strip())
            pts.append({"t": r["ISO_TIME"].replace(" ", "T") + "Z", "lat": la, "lon": lo,
                        "kt": int(w) if w.lstrip("-").isdigit() else None,
                        "hpa": int(pr) if pr.isdigit() else None})
    return pts, atcf


def forecast(atcf):
    f = ADECK / f"a{atcf.lower()}.dat.gz"
    if not f.exists():
        return None
    by = {}
    for line in gzip.open(f, "rt", errors="replace"):
        p = [x.strip() for x in line.split(",")]
        if len(p) < 8 or p[4] != "OFCL":
            continue
        try:
            tau = int(p[5])
            la = int(p[6][:-1]) / 10 * (1 if p[6][-1] == "N" else -1)
            lo = int(p[7][:-1]) / 10 * (-1 if p[7][-1] == "W" else 1)
            vmax = int(p[8]) if len(p) > 8 and p[8].isdigit() else None
            mslp = int(p[9]) if len(p) > 9 and p[9].isdigit() and int(p[9]) > 0 else None
        except ValueError:
            continue
        by.setdefault(p[2], {}).setdefault(tau, (la, lo, vmax, mslp))
    for em in sorted(by):
        taus = by[em]
        if any(12 <= t <= 120 and dist(la, lo, *YUNA) < R_KM for t, (la, lo, _, _) in taus.items()):
            return {"issued": datetime.strptime(em, "%Y%m%d%H").strftime("%Y-%m-%dT%H:00Z"),
                    "pts": [{"tau": t, "lat": la, "lon": lo, "kt": vm, "hpa": pr} for t, (la, lo, vm, pr) in sorted(taus.items())]}
    return None


def wind(storm_id, start, end):
    """ERA5 10 m, cada 6 h, rejilla de 0,5°. Devuelve u y v (m/s) por fotograma, fila por latitud."""
    CACHE.mkdir(parents=True, exist_ok=True)
    lats = [LAT0 + i * STEP for i in range(int((LAT1 - LAT0) / STEP) + 1)]
    lons = [LON0 + j * STEP for j in range(int((LON1 - LON0) / STEP) + 1)]
    grid = [(la, lo) for la in lats for lo in lons]
    raw = []
    for k in range(0, len(grid), 100):
        part = grid[k:k + 100]
        cf = CACHE / f"{storm_id}_{start}_{end}_{k}.json"
        if not cf.exists():
            url = ("https://archive-api.open-meteo.com/v1/archive?latitude=" + ",".join(f"{a:.2f}" for a, _ in part)
                   + "&longitude=" + ",".join(f"{b:.2f}" for _, b in part)
                   + f"&start_date={start}&end_date={end}&hourly=wind_speed_10m,wind_direction_10m"
                   + "&wind_speed_unit=ms&timezone=GMT&models=era5")
            for intento in range(6):
                try:
                    with urllib.request.urlopen(url, timeout=180) as r:
                        cf.write_bytes(r.read())
                    break
                except Exception as e:  # noqa: BLE001
                    print("  reintento", storm_id, k, e, flush=True)
                    time.sleep(10 * (intento + 1))
            else:
                raise RuntimeError(f"sin viento para {storm_id} lote {k}")
            time.sleep(1.5)
        d = json.loads(cf.read_text())
        raw.extend(d if isinstance(d, list) else [d])
    assert len(raw) == len(grid), (len(raw), len(grid))
    times = raw[0]["hourly"]["time"]
    idx = [i for i, t in enumerate(times) if int(t[11:13]) % 6 == 0]
    frames = []
    for i in idx:
        u, v = [], []
        for loc in raw:
            s, dr = loc["hourly"]["wind_speed_10m"][i], loc["hourly"]["wind_direction_10m"][i]
            if s is None or dr is None:
                u.append(None); v.append(None); continue
            a = math.radians(dr)
            u.append(round(-s * math.sin(a), 1)); v.append(round(-s * math.cos(a), 1))
        frames.append({"t": times[i] + "Z", "u": u, "v": v})
    return {"lon0": LON0, "lat0": LAT0, "step": STEP, "nx": len(lons), "ny": len(lats), "frames": frames}


def rain(storm_id, start, end, frames):
    """Lluvia ERA5 acumulada en las 6 h que terminan en cada fotograma (mm), misma rejilla."""
    lats = [LAT0 + i * STEP for i in range(int((LAT1 - LAT0) / STEP) + 1)]
    lons = [LON0 + j * STEP for j in range(int((LON1 - LON0) / STEP) + 1)]
    grid = [(la, lo) for la in lats for lo in lons]
    raw = []
    for k in range(0, len(grid), 100):
        part = grid[k:k + 100]
        cf = CACHE / f"lluvia_{storm_id}_{start}_{end}_{k}.json"
        if not cf.exists():
            url = ("https://archive-api.open-meteo.com/v1/archive?latitude=" + ",".join(f"{a:.2f}" for a, _ in part)
                   + "&longitude=" + ",".join(f"{b:.2f}" for _, b in part)
                   + f"&start_date={start}&end_date={end}&hourly=precipitation&timezone=GMT&models=era5")
            for intento in range(6):
                try:
                    with urllib.request.urlopen(url, timeout=180) as r:
                        cf.write_bytes(r.read())
                    break
                except Exception as e:  # noqa: BLE001
                    print("  reintento lluvia", storm_id, k, e, flush=True)
                    time.sleep(10 * (intento + 1))
            else:
                raise RuntimeError(f"sin lluvia para {storm_id} lote {k}")
            time.sleep(1.5)
        d = json.loads(cf.read_text())
        raw.extend(d if isinstance(d, list) else [d])
    assert len(raw) == len(grid)
    times = raw[0]["hourly"]["time"]
    pos = {t + "Z": i for i, t in enumerate(times)}
    for fr in frames:
        i = pos[fr["t"]]
        fr["p"] = [round(sum(x for x in loc["hourly"]["precipitation"][max(0, i - 5):i + 1] if x is not None), 1) for loc in raw]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for fl in floods():
        season = fl["onset"][:4]
        pts, atcf = track(fl["name"], season)
        fc = forecast(atcf) if atcf else None
        onset = datetime.strptime(fl["onset"], "%Y-%m-%d")
        t0 = onset - timedelta(days=3)
        if fc:
            t0 = min(t0, datetime.strptime(fc["issued"], "%Y-%m-%dT%H:00Z"))
        t1 = onset + timedelta(days=1)
        w = wind(fl["id"], t0.strftime("%Y-%m-%d"), t1.strftime("%Y-%m-%d"))
        # la lluvia se sirve en la web desde NASA GIBS (IMERG); rain() queda para quien tenga cupo de Open-Meteo
        peak = max((p["kt"] for p in pts if p["kt"] is not None), default=None)
        rec = {"id": fl["id"], "name": fl["name"].title(), "year": int(season), "onset": fl["onset"], "lead_h": fl["lead_h"],
               "dmin_km": fl["dmin_km"], "atcf": atcf, "peak_kt": peak, "track": pts, "forecast": fc, "wind": w}
        (OUT / f"{fl['id']}.json").write_text(json.dumps(rec, separators=(",", ":")), encoding="utf-8")
        index.append({k: rec[k] for k in ("id", "name", "year", "onset", "lead_h", "dmin_km", "peak_kt")})
        print(fl["id"], fl["name"], len(pts), "puntos", "pronóstico" if fc else "sin pronóstico", len(w["frames"]), "fotogramas", flush=True)
    meta = {"yuna": {"lat": YUNA[0], "lon": YUNA[1]}, "r_km": R_KM, "storms": index,
            "sources": {"track": "IBTrACS v04r01 (NOAA NCEI), North Atlantic",
                        "forecast": "NHC ATCF a-deck, OFCL, as issued (ftp.nhc.noaa.gov/atcf/archive)",
                        "wind": "ERA5 10 m wind via Open-Meteo historical archive, 6-hourly, 0.5° grid",
                        "rain": "NASA GPM IMERG precipitation rate via NASA GIBS (served live in the web)",
                        "satellite": "NASA GIBS MODIS Terra corrected reflectance, true colour, daily",
                        "floods": "results/tropical/ciclones/inundaciones_y_ciclones.csv"}}
    (OUT / "index.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
