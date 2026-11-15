"""Todas las tormentas tropicales que pasaron cerca de República Dominicana (2001-2024) y, para cada provincia,
cuáles la rozaron y con cuánta antelación lo anunció el pronóstico oficial del NHC.

- Trayectorias: IBTrACS v04r01 (Atlántico Norte), cada 6 h (00, 06, 12, 18 UTC).
- Llegada a un lugar: primera hora en que el centro observado queda a menos de 200 km del centroide de la provincia.
- Antelación: llegada menos la emisión del primer aviso OFCL (a-deck tal como se emitió) cuya trayectoria, entre 12 y
  120 h, pone el centro a menos de 200 km del mismo centroide. Si el aviso llega después, la antelación es negativa.
Solo biblioteca estándar. Ejecutar en Docker (galeria) con web/ montado, como exportar_huracanes.py.
"""
from __future__ import annotations

import csv
import gzip
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IBT = ROOT / "data" / "tropical" / "ibtracs" / "ibtracs.NA.list.v04r01.csv"
ADECK = ROOT / "data" / "tropical" / "nhc_adeck"
GEO = ROOT / "web" / "public" / "data" / "limites" / "provincias.geojson"
OUT = ROOT / "web" / "public" / "data" / "huracanes" / "rd.json"
WIND = ROOT / "web" / "public" / "data" / "huracanes"
R_KM = 200.0
NEAR_KM = 400.0  # tormentas cuyo centro pasó a menos de esto de alguna provincia


def dist(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(math.radians, (la1, lo1, la2, lo2))
    a = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def centroid(geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    ring = max((p[0] for p in polys), key=len)
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        f = x0 * y1 - x1 * y0
        a += f; cx += (x0 + x1) * f; cy += (y0 + y1) * f
    return cy / (3 * a), cx / (3 * a)


def provinces():
    g = json.loads(GEO.read_text(encoding="utf-8"))
    out = []
    for f in g["features"]:
        la, lo = centroid(f["geometry"])
        out.append({"id": f["properties"]["shapeISO"], "name": f["properties"]["shapeName"], "lat": round(la, 3), "lon": round(lo, 3)})
    return sorted(out, key=lambda p: p["name"])


def storms():
    by = {}
    with open(IBT, encoding="utf-8") as f:
        rd = csv.DictReader(f)
        next(rd)
        for r in rd:
            if not (2001 <= int(r["SEASON"]) <= 2024) or r["ISO_TIME"][11:13] not in ("00", "06", "12", "18"):
                continue
            la, lo = float(r["LAT"]), float(r["LON"])
            if not (-90 <= lo <= -50 and 5 <= la <= 35):
                continue
            w, pr = r["USA_WIND"].strip(), (r["USA_PRES"].strip() or r["WMO_PRES"].strip())
            s = by.setdefault(r["SID"], {"sid": r["SID"], "name": r["NAME"].title(), "year": int(r["SEASON"]), "atcf": r["USA_ATCF_ID"], "track": []})
            s["track"].append([r["ISO_TIME"].replace(" ", "T") + "Z", la, lo, int(w) if w.isdigit() else None, int(pr) if pr.isdigit() else None])
    return list(by.values())


def advisories(atcf):
    f = ADECK / f"a{atcf.lower()}.dat.gz"
    if not atcf or not f.exists():
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
        except ValueError:
            continue
        by.setdefault(p[2], {}).setdefault(tau, (la, lo, vmax))
    return by


def main():
    provs = provinces()
    winds = {p.stem for p in WIND.glob("20*.json")}
    floods = {}
    for fn in WIND.glob("20*.json"):
        d = json.loads(fn.read_text(encoding="utf-8"))
        floods[(d["name"].upper(), d["year"])] = fn.stem
    out_storms, hits = [], {p["id"]: [] for p in provs}
    hits["DO"] = []
    for s in storms():
        dmin = min(min(dist(la, lo, p["lat"], p["lon"]) for p in provs) for _, la, lo, _, _ in s["track"])
        if dmin > NEAR_KM:
            continue
        adv = advisories(s["atcf"])
        kts = [k for *_, k, _ in s["track"] if k is not None]
        rec = {"sid": s["sid"], "name": s["name"], "year": s["year"], "peak_kt": max(kts) if kts else None,
               "dmin_km": round(dmin), "has_adv": adv is not None,
               "wind": floods.get((s["name"].upper(), s["year"])) if (s["name"].upper(), s["year"]) in floods else None,
               "track": s["track"]}
        out_storms.append(rec)
        best_do = None
        for p in provs:
            ds = [(dist(la, lo, p["lat"], p["lon"]), t, k) for t, la, lo, k, _ in s["track"]]
            near = [x for x in ds if x[0] < R_KM]
            if not near:
                continue
            arrive = min(near, key=lambda x: x[1])[1]
            closest = min(ds)
            lead, issued, fc = None, None, None
            if adv:
                for em in sorted(adv):
                    if any(12 <= tau <= 120 and dist(la, lo, p["lat"], p["lon"]) < R_KM for tau, (la, lo, _) in adv[em].items()):
                        issued = datetime.strptime(em, "%Y%m%d%H")
                        lead = round((datetime.strptime(arrive, "%Y-%m-%dT%H:%M:%SZ") - issued).total_seconds() / 3600)
                        fc = [[tau, la, lo, vm] for tau, (la, lo, vm) in sorted(adv[em].items())]
                        break
            h = {"sid": s["sid"], "dmin_km": round(closest[0]), "arrive": arrive, "kt_closest": closest[2], "lead_h": lead,
                 "issued": issued.strftime("%Y-%m-%dT%H:00Z") if issued else None, "fc": fc}
            hits[p["id"]].append(h)
            if best_do is None or (lead or -1e9) > (best_do["lead_h"] or -1e9):
                best_do = h
        if best_do:
            hits["DO"].append(best_do)
    for k in hits:
        hits[k].sort(key=lambda h: h["arrive"], reverse=True)
    meta = {"r_km": R_KM, "near_km": NEAR_KM, "provinces": provs, "storms": out_storms, "hits": hits,
            "sources": {"track": "IBTrACS v04r01 (NOAA NCEI)", "forecast": "NHC ATCF a-deck OFCL as issued",
                        "rule": "arrival = first 6-hourly fix within 200 km of the province centroid; lead = arrival - first OFCL advisory forecasting the centre within 200 km at 12-120 h"}}
    OUT.write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")
    n = sum(1 for k in hits if k != "DO" for _ in hits[k])
    print(len(out_storms), "tormentas a <", NEAR_KM, "km;", len(hits["DO"]), "pasaron a <200 km de alguna provincia;", n, "pares provincia-tormenta")
    leads = [h["lead_h"] for h in hits["DO"] if h["lead_h"] is not None]
    print("antelación (mejor provincia) mediana:", sorted(leads)[len(leads) // 2] if leads else None, "h; sin aviso:", sum(1 for h in hits["DO"] if h["lead_h"] is None))


if __name__ == "__main__":
    main()
