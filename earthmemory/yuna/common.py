"""Rutas, constantes y manifiesto del caso Yuna (Bajo Yuna / presa de Hatillo).

Cada motor de Evidence Intelligence escribe SOLO en su carpeta: data/yuna, results/yuna, figures/yuna.
Lee en solo lectura data/nacional (IMERG, GLDAS), data/nacional_hr (SMAP L4, CHIRPS, DEM, WorldCover, límites)
y, si existe, data/tendencias/chirps_diario (CHIRPS diario que baja otro motor).
"""

from __future__ import annotations

from pathlib import Path

from ..hr.common import Manifest, http_get, http_head, sha256, earthdata_token, FetchError  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "yuna"
RES = ROOT / "results" / "yuna"
FIG = ROOT / "figures" / "yuna"
WEB = RES / "web"
REPORT = ROOT / "reports_nacional" / "CASO_YUNA.md"
NB_DIR = ROOT / "notebooks"
NB_HTML = ROOT / "reports_nacional" / "notebooks_html"

NAC = ROOT / "data" / "nacional"
HR = ROOT / "data" / "nacional_hr"
TEND = ROOT / "data" / "tendencias"

USER_AGENT = "earthmemory-yuna/0.1 (NASA Space Apps 2026; reproducible research)"
SEED = 2026
YEARS = (2001, 2024)
# Caja del caso: cuenca del Yuna + Yaque del Norte (para responder qué drena dónde) + margen
BBOX = (-71.40, 18.55, -69.00, 19.95)

# Puntos que hay que asignar a una cuenca (lat, lon). Fuentes: EARTH_MEMORY.md / ALTA_RESOLUCION.md
# (celdas del análisis previo) y coordenadas de cabeceras municipales (aprox., Wikipedia/OSM; ver informe).
PUNTOS = {
    "celda_GLDAS_MonsenorNouel_18.875_-70.375": (18.875, -70.375),
    "celda_GLDAS_Santiago_LaVega_19.375_-70.625": (19.375, -70.625),
    "celda_HR_cordillera_19.025_-70.975": (19.025, -70.975),
    "celda_HR_LaVega_19.175_-70.475": (19.175, -70.475),
    "Bonao": (18.937, -70.409),
    "La Vega (ciudad)": (19.222, -70.529),
    "Santiago (ciudad)": (19.451, -70.697),
    "Cotuí": (19.053, -70.149),
    "San Francisco de Macorís": (19.300, -70.252),
    "Villa Riva": (19.176, -69.908),
    "Arenoso": (19.188, -69.857),
    "Pimentel": (19.183, -70.100),
    "Jarabacoa": (19.118, -70.637),
    "Constanza": (18.909, -70.745),
    "Moca": (19.394, -70.525),
}

# Presa de Hatillo (coordenada de la cortina; se verifica contra el embalse visible en JRC GSW y el DEM)
HATILLO = {"lat": 19.0336, "lon": -70.2004}  # Wikipedia «Hatillo Dam» (19°02′00.91″N 70°12′01.49″O)

CLASES = {
    "OBS": "OBSERVACIÓN",
    "RET": "RECUPERACIÓN SATELITAL",
    "ASIM": "MODELO CON ASIMILACIÓN",
    "FORZ": "MODELO FORZADO",
    "HIDRO": "SIMULACIÓN HIDROLÓGICA",
    "REG": "REGISTRO DOCUMENTAL",
}


def manifest() -> Manifest:
    return Manifest(DATA / "MANIFEST.json")


def ensure_dirs() -> None:
    for d in (DATA, RES, FIG, WEB):
        d.mkdir(parents=True, exist_ok=True)
