"""Delimitación de la cuenca del Yuna y sus zonas con HydroSHEDS (HydroBASINS v1c niveles 6-10, HydroRIVERS v1.0).

Método (sin SIG externo):
- Se leen del zip solo los polígonos/tramos dentro de la caja de RD (pyshp + shapely).
- Topología: cada polígono HydroBASINS tiene NEXT_DOWN (polígono al que drena; 0 = mar o sumidero).
  «Aguas arriba de X» = todos los polígonos cuya cadena NEXT_DOWN pasa por X (X incluido).
- Salida del Yuna: el polígono de nivel 10 con mayor UP_AREA entre los que drenan al mar en la orilla oeste de
  la bahía de Samaná. Igual para Yaque del Norte (Montecristi), Yaque del Sur (bahía de Neiba) y Ozama.
- Presa de Hatillo: polígono de nivel 10 que contiene la cortina; además, el área drenada exacta en la cortina
  se lee de HydroRIVERS (UPLAND_SKM del tramo más cercano de mayor orden).
- Camú: se sigue HydroRIVERS desde La Vega aguas abajo hasta el tramo anterior a la unión con un río de mucha
  mayor área (el Yuna). La subcuenca es lo que drena al polígono de nivel 10 que contiene ese último tramo del Camú.
- Zonas finales (disjuntas): alto_hatillo (aguas arriba de la cortina), camu, bajo_yuna (el resto del Yuna:
  Cotuí → Pimentel → Villa Riva/Arenoso → bahía de Samaná, con sus afluentes no regulados).
Limitación declarada: el polígono de nivel 10 que contiene la cortina puede extenderse algo aguas abajo de ella;
el área se contrasta con la de HydroRIVERS en la cortina.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import shapefile
from shapely.geometry import Point, box, mapping, shape
from shapely.ops import unary_union

from .common import BBOX, DATA, HATILLO, PUNTOS, RES

HS = DATA / "hydrosheds"
DR_BOX = (-72.10, 17.40, -68.20, 20.10)


def _reader(zpath: Path) -> tuple[shapefile.Reader, zipfile.ZipFile]:
    z = zipfile.ZipFile(zpath)
    names = z.namelist()
    shp = next(n for n in names if n.endswith(".shp"))
    base = shp[:-4]
    r = shapefile.Reader(shp=z.open(shp), shx=z.open(base + ".shx"), dbf=z.open(base + ".dbf"))
    return r, z


def load_clip(zpath: Path, bbox=DR_BOX) -> list[dict]:
    """Registros (atributos + geometría shapely) cuyo rectángulo toca la caja."""
    r, z = _reader(zpath)
    fields = [f[0] for f in r.fields[1:]]
    out = []
    x0, y0, x1, y1 = bbox
    for i, s in enumerate(r.iterShapes()):
        b = s.bbox
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
            continue
        rec = dict(zip(fields, r.record(i)))
        rec["geom"] = shape(s.__geo_interface__)
        out.append(rec)
    z.close()
    return out


def _cache(name: str, loader):
    p = DATA / "derivados" / f"{name}.geojson"
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        return [{**f["properties"], "geom": shape(f["geometry"])} for f in d["features"]]
    recs = loader()
    p.parent.mkdir(parents=True, exist_ok=True)
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {k: v for k, v in r.items() if k != "geom"}, "geometry": mapping(r["geom"])}
        for r in recs]}
    p.write_text(json.dumps(fc), encoding="utf-8")
    return recs


def basins(level: int) -> list[dict]:
    return _cache(f"hybas_lev{level:02d}_RD", lambda: load_clip(HS / f"hybas_na_lev{level:02d}_v1c.zip"))


def rivers() -> list[dict]:
    return _cache("hydrorivers_RD", lambda: load_clip(HS / "HydroRIVERS_v10_na_shp.zip"))


# ------------------------------------------------------------------ topología

def upstream(recs: list[dict], target: int, key="HYBAS_ID") -> set[int]:
    down = {r[key]: r["NEXT_DOWN"] for r in recs}
    memo: dict[int, bool] = {}

    def reaches(i: int) -> bool:
        path = []
        while i and i not in memo:
            if i == target:
                memo[i] = True
                break
            path.append(i)
            i = down.get(i, 0)
        res = memo.get(i, False) if i else False
        for p in path:
            memo[p] = res
        return res

    return {r[key] for r in recs if r[key] == target or reaches(r[key])}


def containing(recs: list[dict], lat: float, lon: float) -> dict | None:
    p = Point(lon, lat)
    for r in recs:
        if r["geom"].contains(p):
            return r
    return None


def outlet(recs: list[dict], lon0, lat0, lon1, lat1) -> dict:
    """Polígono que drena al mar (NEXT_DOWN = 0) con mayor UP_AREA cuyo centroide cae en la caja."""
    cand = [r for r in recs if r["NEXT_DOWN"] == 0 and box(lon0, lat0, lon1, lat1).contains(r["geom"].centroid)]
    return max(cand, key=lambda r: r["UP_AREA"])


def outlet_of(recs: list[dict], hid: int) -> dict:
    by = {r["HYBAS_ID"]: r for r in recs}
    r = by[hid]
    while r["NEXT_DOWN"] and r["NEXT_DOWN"] in by:
        r = by[r["NEXT_DOWN"]]
    return r


def area_km2(geom) -> float:
    """Área geodésica aproximada (proyección equivalente local)."""
    from shapely.ops import transform
    lat0 = geom.centroid.y
    k = 111.32
    return transform(lambda x, y, z=None: (x * k * np.cos(np.radians(lat0)), y * 110.574), geom).area


# ------------------------------------------------------------------ cuencas del caso

SALIDAS = {  # caja de búsqueda de la desembocadura (lon0, lat0, lon1, lat1)
    "Yuna": (-69.95, 19.05, -69.40, 19.40),
    "Yaque del Norte": (-71.85, 19.60, -71.40, 20.00),
    "Yaque del Sur": (-71.30, 18.10, -70.90, 18.45),
    "Ozama": (-70.00, 18.40, -69.80, 18.55),
}


def _river_near(rivs: list[dict], lat: float, lon: float, min_up: float = 0, radio: float = 0.03) -> dict:
    p = Point(lon, lat)
    cand = [r for r in rivs if r["UPLAND_SKM"] >= min_up and r["geom"].distance(p) <= radio]
    if not cand:
        cand = [r for r in rivs if r["UPLAND_SKM"] >= min_up]
        return min(cand, key=lambda r: r["geom"].distance(p))
    return max(cand, key=lambda r: r["UPLAND_SKM"])


def camu_outlet_reach(rivs: list[dict]) -> tuple[dict, dict]:
    """Del Camú en La Vega, aguas abajo hasta justo antes de unirse a un río de área mucho mayor (el Yuna)."""
    by = {r["HYRIV_ID"]: r for r in rivs}
    lv = PUNTOS["La Vega (ciudad)"]
    r = _river_near(rivs, lv[0], lv[1], min_up=100, radio=0.04)
    while r["NEXT_DOWN"] in by:
        nxt = by[r["NEXT_DOWN"]]
        if nxt["UPLAND_SKM"] - r["UPLAND_SKM"] > 1000:  # se suma un río mayor que el propio Camú: confluencia
            return r, nxt
        r = nxt
    raise RuntimeError("no se encontró la confluencia del Camú")


def delinear() -> dict:
    out = {"niveles": {}}
    b10 = basins(10)
    rivs = rivers()
    by10 = {r["HYBAS_ID"]: r for r in b10}

    sal = {k: outlet(b10, *v) for k, v in SALIDAS.items()}
    sets = {k: upstream(b10, r["HYBAS_ID"]) for k, r in sal.items()}

    # Hatillo
    hp = containing(b10, HATILLO["lat"], HATILLO["lon"])
    set_hat = upstream(b10, hp["HYBAS_ID"])
    r_hat = _river_near(rivs, HATILLO["lat"], HATILLO["lon"], min_up=300, radio=0.03)

    # Camú
    r_camu, r_conf = camu_outlet_reach(rivs)
    g = r_camu["geom"]
    pt = g.interpolate(0.5, normalized=True)
    cp = containing(b10, pt.y, pt.x)
    set_camu = upstream(b10, cp["HYBAS_ID"])
    if cp["HYBAS_ID"] in set_hat or set_camu & set_hat:
        raise RuntimeError("Camú y Hatillo se solapan: revisar delimitación")

    yuna = sets["Yuna"]
    zonas = {
        "yuna": yuna,
        "alto_hatillo": set_hat & yuna,
        "camu": set_camu & yuna,
    }
    zonas["bajo_yuna"] = yuna - zonas["alto_hatillo"] - zonas["camu"]
    geoms = {k: unary_union([by10[i]["geom"] for i in v]).buffer(0) for k, v in zonas.items()}
    for k in ("Yaque del Norte", "Yaque del Sur", "Ozama"):
        geoms[k] = unary_union([by10[i]["geom"] for i in sets[k]]).buffer(0)

    out["salidas"] = {k: {"HYBAS_ID": int(r["HYBAS_ID"]), "UP_AREA_km2": float(r["UP_AREA"]),
                          "centroide": [round(r["geom"].centroid.y, 4), round(r["geom"].centroid.x, 4)]}
                      for k, r in sal.items()}
    out["hatillo"] = {"poligono_lev10": int(hp["HYBAS_ID"]), "UP_AREA_lev10_km2": float(hp["UP_AREA"]),
                      "hydrorivers_tramo": int(r_hat["HYRIV_ID"]), "hydrorivers_UPLAND_km2": float(r_hat["UPLAND_SKM"]),
                      "hydrorivers_caudal_medio_m3s": float(r_hat["DIS_AV_CMS"]),
                      "dist_tramo_cortina_km": round(r_hat["geom"].distance(Point(HATILLO["lon"], HATILLO["lat"])) * 105, 2)}
    out["camu"] = {"tramo_final": int(r_camu["HYRIV_ID"]), "UPLAND_km2": float(r_camu["UPLAND_SKM"]),
                   "caudal_medio_m3s_hydrorivers": float(r_camu["DIS_AV_CMS"]),
                   "confluencia_lonlat": [round(r_camu["geom"].coords[-1][0], 4), round(r_camu["geom"].coords[-1][1], 4)],
                   "tramo_receptor": int(r_conf["HYRIV_ID"]), "UPLAND_receptor_km2": float(r_conf["UPLAND_SKM"]),
                   "poligono_lev10": int(cp["HYBAS_ID"])}
    out["areas_km2"] = {k: round(area_km2(g), 1) for k, g in geoms.items()}
    out["n_poligonos_lev10"] = {k: len(v) for k, v in zonas.items()}

    # Niveles 6-9: qué polígonos componen la cuenca (código Pfafstetter) — para trazabilidad
    for lv in (6, 7, 8, 9):
        b = basins(lv)
        gy = geoms["yuna"]
        filas = []
        for r in b:
            if not r["geom"].intersects(gy):
                continue
            inter = r["geom"].intersection(gy).area
            if inter < 0.01 * gy.area:
                continue
            filas.append({"HYBAS_ID": int(r["HYBAS_ID"]), "PFAF_ID": int(r["PFAF_ID"]),
                          "SUB_AREA_km2": round(float(r["SUB_AREA"]), 1),
                          "frac_del_poligono_en_yuna": round(inter / r["geom"].area, 3),
                          "frac_del_yuna_cubierta": round(inter / gy.area, 3)})
        out["niveles"][f"lev{lv:02d}"] = sorted(filas, key=lambda t: t["PFAF_ID"])

    # ¿Qué drena dónde? Punto: zona que lo contiene. Celda: fracción del rectángulo en cada cuenca.
    cuencas_mayores = {"Yuna": geoms["yuna"], "Yaque del Norte": geoms["Yaque del Norte"],
                       "Yaque del Sur": geoms["Yaque del Sur"], "Ozama": geoms["Ozama"]}
    filas = []
    for nombre, (lat, lon) in PUNTOS.items():
        p = Point(lon, lat)
        res = 0.25 if "GLDAS" in nombre else 0.05 if "HR" in nombre else 0.0
        geom = box(lon - res / 2, lat - res / 2, lon + res / 2, lat + res / 2) if res else p
        f = {"punto": nombre, "lat": lat, "lon": lon, "celda_grados": res or None}
        for k, gg in {**cuencas_mayores, "alto_hatillo": geoms["alto_hatillo"], "camu": geoms["camu"],
                      "bajo_yuna": geoms["bajo_yuna"]}.items():
            f[f"frac_{k}"] = round(geom.intersection(gg).area / geom.area, 3) if res else float(gg.contains(p))
        pol = containing(b10, lat, lon)
        if pol is not None:
            o = outlet_of(b10, pol["HYBAS_ID"])
            f["salida_al_mar_HYBAS"] = int(o["HYBAS_ID"])
            f["salida_al_mar_lat"] = round(o["geom"].centroid.y, 3)
            f["salida_al_mar_lon"] = round(o["geom"].centroid.x, 3)
            f["salida_cuenca"] = next((k for k, s in sal.items() if s["HYBAS_ID"] == o["HYBAS_ID"]), "otra")
        filas.append(f)
    out["puntos"] = filas
    return out, geoms, rivs, b10


def guardar(out: dict, geoms: dict, rivs: list[dict]) -> None:
    RES.mkdir(parents=True, exist_ok=True)
    feats = []
    for k, g in geoms.items():
        feats.append({"type": "Feature", "properties": {"zona": k, "area_km2": out["areas_km2"].get(k)},
                      "geometry": mapping(g)})
    (RES / "cuencas_yuna.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}),
                                             encoding="utf-8")
    # ríos de la caja del caso con área drenada ≥ 50 km²
    x0, y0, x1, y1 = BBOX
    rf = [{"type": "Feature", "properties": {"HYRIV_ID": int(r["HYRIV_ID"]), "UPLAND_SKM": float(r["UPLAND_SKM"]),
                                             "ORD_STRA": int(r["ORD_STRA"]), "DIS_AV_CMS": float(r["DIS_AV_CMS"])},
           "geometry": mapping(r["geom"])}
          for r in rivs if r["UPLAND_SKM"] >= 50 and r["geom"].intersects(box(x0, y0, x1, y1))]
    (RES / "rios_hydrorivers.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": rf}),
                                                 encoding="utf-8")
    import pandas as pd
    pd.DataFrame(out["puntos"]).to_csv(RES / "que_drena_donde.csv", index=False)
    meta = {k: v for k, v in out.items() if k != "puntos"}
    (RES / "cuencas_resumen.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
