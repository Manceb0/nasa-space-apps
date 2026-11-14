"""País, rejilla MERRA-2 y máscara de tierra.

Límites: Natural Earth 1:10m admin-0 v5.1.2 (dominio público). Se descarga una vez, se guarda su
SHA-256 y solo se conserva un extracto con los países que tocan la caja de estudio.

Regla de inclusión de una celda (documentada en el informe):
- fracción de la celda dentro del país >= MIN_FRAC (0.25 por defecto; 0.50 en sensibilidad);
- la parte del país es mayor o igual que la de cualquier otro país (así se excluyen celdas
  dominadas por Haití);
- MERRA-2 trata la celda como tierra (EVLAND con datos y GWETTOP no fijo en 1.0, que es el valor
  que POWER devuelve sobre mar).
Las celdas costeras se conservan si cumplen lo anterior: su valor es el de la parte de tierra del
modelo, pero el clima de la celda incluye la influencia del mar. Se informa la fracción de tierra.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath

from . import power

NE_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/"
          "ne_10m_admin_0_countries.geojson")
DLAT, DLON = 0.5, 0.625  # rejilla nativa MERRA-2
MIN_FRAC = 0.25

# Lugares de referencia SOLO para nombrar celdas (coordenadas aproximadas, ±0.05°).
LUGARES_DOM = {
    "Santo Domingo": (18.47, -69.90), "Santiago": (19.45, -70.70), "Montecristi": (19.85, -71.65),
    "Dajabón": (19.55, -71.71), "Mao": (19.55, -71.08), "Puerto Plata": (19.79, -70.69),
    "La Vega": (19.22, -70.53), "Constanza": (18.91, -70.75), "Bonao": (18.94, -70.41),
    "San Francisco de Macorís": (19.30, -70.25), "Nagua": (19.38, -69.85), "Samaná": (19.21, -69.34),
    "Monte Plata": (18.81, -69.78), "Hato Mayor": (18.76, -69.26), "El Seibo": (18.77, -69.04),
    "Higüey": (18.62, -68.71), "La Romana": (18.43, -68.97), "San Pedro de Macorís": (18.46, -69.31),
    "Baní": (18.28, -70.33), "Azua": (18.45, -70.73), "San Juan de la Maguana": (18.81, -71.23),
    "Comendador (Elías Piña)": (18.88, -71.70), "Neiba": (18.48, -71.42), "Jimaní": (18.49, -71.85),
    "Barahona": (18.21, -71.10), "Pedernales": (18.04, -71.74), "Punta Cana": (18.58, -68.40),
    "Cotuí": (19.05, -70.15),
}


@dataclass
class Country:
    iso3: str
    name: str
    polygons: list          # [(exterior Nx2, [holes])]
    others: dict            # iso3 -> polygons de países vecinos dentro de la caja
    bounds: tuple           # lon0, lat0, lon1, lat1


def _polys(geom: dict) -> list:
    if geom["type"] == "Polygon":
        rings = [geom["coordinates"]]
    elif geom["type"] == "MultiPolygon":
        rings = geom["coordinates"]
    else:
        return []
    return [(np.asarray(r[0], float), [np.asarray(h, float) for h in r[1:]]) for r in rings]


def _bounds(polys: list) -> tuple:
    allp = np.vstack([e for e, _ in polys])
    return (float(allp[:, 0].min()), float(allp[:, 1].min()), float(allp[:, 0].max()), float(allp[:, 1].max()))


def ensure_boundaries(cache_dir: Path, iso3: str, manifest: power.Manifest, margin: float = 1.0) -> Path:
    """Extracto de Natural Earth con el país y sus vecinos en la caja (+margin°)."""
    out = Path(cache_dir) / f"natural_earth_10m_{iso3}_extracto.geojson"
    if manifest.verify(out):
        return out
    raw = power.http_get(NE_URL, pause=0.5)
    import hashlib
    raw_sha = hashlib.sha256(raw).hexdigest()
    doc = json.loads(raw)
    feats = {f["properties"]["ADM0_A3"]: f for f in doc["features"]}
    if iso3 not in feats:
        raise ValueError(f"{iso3} no está en Natural Earth admin-0")
    b = _bounds(_polys(feats[iso3]["geometry"]))
    box = (b[0] - margin, b[1] - margin, b[2] + margin, b[3] + margin)
    keep = []
    for a3, f in sorted(feats.items()):
        ps = _polys(f["geometry"])
        if not ps:
            continue
        fb = _bounds(ps)
        if fb[0] <= box[2] and fb[2] >= box[0] and fb[1] <= box[3] and fb[3] >= box[1]:
            keep.append({"type": "Feature", "properties": {"ADM0_A3": a3, "NAME": f["properties"].get("NAME")},
                         "geometry": f["geometry"]})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"type": "FeatureCollection", "features": keep}, ensure_ascii=False), encoding="utf-8",
                   newline="\n")
    manifest.add(out, NE_URL, nota="extracto: solo países que tocan la caja del país ±1°",
                 sha256_archivo_original=raw_sha, bytes_archivo_original=len(raw), fuente="Natural Earth 10m admin-0 v5.1.2")
    return out


def load_country(path: Path, iso3: str) -> Country:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    polys, others, name = None, {}, iso3
    for f in doc["features"]:
        a3 = f["properties"]["ADM0_A3"]
        if a3 == iso3:
            polys, name = _polys(f["geometry"]), f["properties"].get("NAME") or iso3
        else:
            others[a3] = _polys(f["geometry"])
    if polys is None:
        raise ValueError(f"{iso3} no está en {path}")
    return Country(iso3, name, polys, others, _bounds(polys))


def inside(polys: list, pts: np.ndarray) -> np.ndarray:
    res = np.zeros(len(pts), bool)
    for ext, holes in polys:
        m = MplPath(ext).contains_points(pts)
        for h in holes:
            m &= ~MplPath(h).contains_points(pts)
        res |= m
    return res


def cell_fraction(polys: list, lat: float, lon: float, n: int = 40) -> float:
    """Fracción de la celda (centro lat, lon) dentro de los polígonos, con n×n puntos ponderados por cos(lat)."""
    la = lat - DLAT / 2 + (np.arange(n) + 0.5) * DLAT / n
    lo = lon - DLON / 2 + (np.arange(n) + 0.5) * DLON / n
    LO, LA = np.meshgrid(lo, la)
    pts = np.column_stack([LO.ravel(), LA.ravel()])
    w = np.cos(np.radians(LA.ravel()))
    return float((inside(polys, pts) * w).sum() / w.sum())


def fetch_bbox(c: Country) -> tuple:
    """Caja del país ampliada media celda: así POWER devuelve toda celda cuyo centro pueda tocar el país.
    POWER exige al menos 2° por lado; si el país es más chico, se amplía alrededor del centro."""
    lon0, lat0, lon1, lat1 = c.bounds
    lon0, lon1, lat0, lat1 = lon0 - DLON / 2, lon1 + DLON / 2, lat0 - DLAT / 2, lat1 + DLAT / 2
    if lon1 - lon0 < 2:
        m = (lon0 + lon1) / 2
        lon0, lon1 = m - 1.01, m + 1.01
    if lat1 - lat0 < 2:
        m = (lat0 + lat1) / 2
        lat0, lat1 = m - 1.01, m + 1.01
    return (round(lon0, 4), round(lat0, 4), round(lon1, 4), round(lat1, 4))


def nearest_places(lat: float, lon: float, places: dict, k: int = 2) -> str:
    """Lugares cuyo punto cae dentro de la celda; si no hay, el más cercano (con 'cerca de')."""
    within = [n for n, (a, b) in places.items() if abs(a - lat) <= DLAT / 2 and abs(b - lon) <= DLON / 2]
    if within:
        within.sort(key=lambda n: (places[n][0] - lat) ** 2 + (places[n][1] - lon) ** 2)
        return " / ".join(within[:k])
    n = min(places, key=lambda n: (places[n][0] - lat) ** 2 + (places[n][1] - lon) ** 2)
    return f"cerca de {n}"


def cell_table(c: Country, meta: dict, gwettop: pd.DataFrame, evland: pd.DataFrame,
               min_frac: float = MIN_FRAC, places: dict | None = None) -> pd.DataFrame:
    rows = []
    for cid, (lat, lon, elev) in sorted(meta.items()):
        fp = cell_fraction(c.polygons, lat, lon)
        fo = {a3: cell_fraction(p, lat, lon) for a3, p in c.others.items()}
        fo_max_a3 = max(fo, key=fo.get) if fo else None
        fo_max = fo[fo_max_a3] if fo_max_a3 else 0.0
        if fo_max <= 0:
            fo_max_a3 = None
        land_model = bool(evland[cid].notna().any()) and not bool((gwettop[cid].dropna() >= 0.999).all())
        reasons = []
        if not land_model:
            reasons.append("MERRA-2 la trata como mar")
        if fp < min_frac:
            reasons.append(f"fracción en {c.iso3} {fp:.2f} < {min_frac}")
        if fo_max > fp:
            reasons.append(f"dominada por {fo_max_a3} ({fo_max:.2f})")
        rows.append({"celda": cid, "lat": lat, "lon": lon, "elevacion_merra2_m": elev,
                     "frac_pais": round(fp, 4), "frac_otro_pais": round(fo_max, 4), "otro_pais": fo_max_a3,
                     "frac_mar": round(max(0.0, 1 - fp - sum(fo.values())), 4),
                     "tierra_en_merra2": land_model, "incluida": not reasons,
                     "motivo_exclusion": "; ".join(reasons),
                     "lugares": nearest_places(lat, lon, places or {})})
    return pd.DataFrame(rows)


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
