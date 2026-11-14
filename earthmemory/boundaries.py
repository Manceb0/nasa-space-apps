"""Límites administrativos de geoBoundaries (gbOpen) para cualquier país: ADM0 y ADM1.

La API https://www.geoboundaries.org/api/current/gbOpen/{ISO3}/{ADM}/ da la URL fija (commit de GitHub)
del GeoJSON y la licencia. Para DOM ADM1 (consultado 2026-11-14): fuente Natural Earth, licencia
"Public Domain", 32 unidades (31 provincias + Distrito Nacional), año representado 2022. Se guardan el
JSON de metadatos y el GeoJSON con su SHA-256 en el manifiesto.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import power, region

API = "https://www.geoboundaries.org/api/current/gbOpen/{iso}/{adm}/"


@dataclass
class Unit:
    name: str
    code: str
    polygons: list                      # [(exterior Nx2, [holes])]
    bounds: tuple = field(default=())


def ensure_adm(ddir: Path, iso3: str, adm: str, manifest: power.Manifest) -> tuple[Path, dict]:
    ddir = Path(ddir) / "limites"
    meta_p = ddir / f"geoBoundaries-{iso3}-{adm}.api.json"
    gj_p = ddir / f"geoBoundaries-{iso3}-{adm}.geojson"
    if manifest.verify(meta_p) and manifest.verify(gj_p):
        return gj_p, json.loads(meta_p.read_text(encoding="utf-8"))
    api = API.format(iso=iso3, adm=adm)
    body = power.http_get(api, pause=0.5)
    meta = json.loads(body)
    ddir.mkdir(parents=True, exist_ok=True)
    meta_p.write_bytes(body)
    manifest.add(meta_p, api, fuente="geoBoundaries API (metadatos)")
    gj = power.http_get(meta["gjDownloadURL"], pause=0.5)
    json.loads(gj)  # valida
    gj_p.write_bytes(gj)
    manifest.add(gj_p, meta["gjDownloadURL"], fuente=f"geoBoundaries gbOpen {iso3} {adm}",
                 licencia=meta.get("boundaryLicense"), fuente_original=meta.get("boundarySource"),
                 anio_representado=meta.get("boundaryYearRepresented"), boundaryID=meta.get("boundaryID"))
    return gj_p, meta


def load_units(path: Path) -> list[Unit]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for f in doc["features"]:
        p = f["properties"]
        polys = region._polys(f["geometry"])
        out.append(Unit(p.get("shapeName"), p.get("shapeISO") or p.get("shapeID"), polys, region._bounds(polys)))
    return sorted(out, key=lambda u: u.name)


def country_polys(units: list[Unit]) -> list:
    return [pg for u in units for pg in u.polygons]


def bounds(units: list[Unit], margin: float = 0.0) -> tuple:
    b = np.array([u.bounds for u in units])
    return (float(b[:, 0].min() - margin), float(b[:, 1].min() - margin),
            float(b[:, 2].max() + margin), float(b[:, 3].max() + margin))


def outline_segments(units: list[Unit]) -> list[np.ndarray]:
    """Anillos exteriores (para dibujar bordes de provincias)."""
    return [e for u in units for e, _ in u.polygons]
