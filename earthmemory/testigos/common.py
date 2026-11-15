"""Rutas, manifiesto y utilidades del motor de testigos (pruebas de hipótesis con datos independientes).

Escribe SOLO en data/testigos, results/testigos, figures/testigos, reports_nacional y notebooks. Lee todo lo
demás (data/nacional, data/nacional_hr, results/nacional, results/nacional_hr, data/tendencias) en solo lectura.
"""

from __future__ import annotations

from pathlib import Path

from ..hr.common import Manifest, bh_fdr, earthdata_token, http_get, write_json  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "testigos"
RES = ROOT / "results" / "testigos"
FIG = ROOT / "figures" / "testigos"
REPORT = ROOT / "reports_nacional" / "TESTIGOS_E_HIPOTESIS.md"
NB_DIR = ROOT / "notebooks"
NB_HTML = ROOT / "reports_nacional" / "notebooks_html"
NAC = ROOT / "data" / "nacional"
NAC_HR = ROOT / "data" / "nacional_hr"
RES_NAC = ROOT / "results" / "nacional"
RES_HR = ROOT / "results" / "nacional_hr"
CHIRPS_D = ROOT / "data" / "tendencias" / "chirps_diario"

# Caja de la RD (lon0, lat0, lon1, lat1) pedida para los testigos
BBOX = (-72.10, 17.30, -68.20, 20.10)
SEED = 2026

# Celdas de las afirmaciones que se ponen a prueba
PAR_GLDAS = {"A": {"celda": "18.875_-70.375", "lat": 18.875, "lon": -70.375, "res": 0.25,
                   "nombre": "Monseñor Nouel (Bonao)"},
             "B": {"celda": "19.375_-70.625", "lat": 19.375, "lon": -70.625, "res": 0.25,
                   "nombre": "Santiago / La Vega"}}
PAR_HR = {"A": {"lat": 19.025, "lon": -70.975, "res": 0.05, "nombre": "Cordillera Central (bosque, ~2400 m)"},
          "B": {"lat": 19.175, "lon": -70.475, "res": 0.05, "nombre": "La Vega (valle del Cibao)"}}
# Yuna alto / Bonao: caja descriptiva (cuenca alta del Yuna aguas arriba de Bonao, aproximada)
YUNA_ALTO = {"lat0": 18.75, "lat1": 19.05, "lon0": -70.65, "lon1": -70.30, "nombre": "Yuna alto / Bonao (caja aprox.)"}

CITAS = {
    "SMAP_L3E": ("O'Neill, P.E., Chan, S., Njoku, E.G., Jackson, T., Bindlish, R., Chaubell, J., Colliander, A. (2023). "
                 "SMAP Enhanced L3 Radiometer Global and Polar Grid Daily 9 km EASE-Grid Soil Moisture, Version 6. "
                 "Boulder, Colorado USA. NASA National Snow and Ice Data Center Distributed Active Archive Center. "
                 "https://doi.org/10.5067/M20OXIZHY3RJ"),
    "HANSEN": ("Hansen, M.C., Potapov, P.V., Moore, R., Hancher, M., Turubanova, S.A., Tyukavina, A., Thau, D., "
               "Stehman, S.V., Goetz, S.J., Loveland, T.R., Kommareddy, A., Egorov, A., Chini, L., Justice, C.O., "
               "Townshend, J.R.G. (2013). High-Resolution Global Maps of 21st-Century Forest Cover Change. Science 342, "
               "850-853. https://doi.org/10.1126/science.1244693 · Datos: Global Forest Change 2000-2025 v1.13, "
               "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2025-v1.13/download.html (CC BY 4.0)"),
    "IMERG_D": ("Huffman, G.J., Stocker, E.F., Bolvin, D.T., Nelkin, E.J., Tan, J. (2023). GPM IMERG Final "
                "Precipitation L3 1 day 0.1 degree x 0.1 degree V07. GES DISC. https://doi.org/10.5067/GPM/IMERGDF/DAY/07"),
    "GLDAS": ("Beaudoing, H., Rodell, M. (2020). GLDAS Noah Land Surface Model L4 monthly 0.25 x 0.25 degree V2.1. "
              "GES DISC. https://doi.org/10.5067/SXAVCZFAQLNO"),
    "CHIRPS": ("Funk, C. et al. (2015). The climate hazards infrared precipitation with stations — a new environmental "
               "record for monitoring extremes. Scientific Data 2, 150066. https://doi.org/10.1038/sdata.2015.66"),
    "TERRACLIMATE": ("Abatzoglou, J.T., Dobrowski, S.Z., Parks, S.A., Hegewisch, K.C. (2018). TerraClimate. "
                     "Scientific Data 5, 170191. https://doi.org/10.1038/sdata.2017.191"),
    "COPDEM": "European Space Agency (2021). Copernicus DEM GLO-90. https://doi.org/10.5270/ESA-c5d3d65",
    "MOD13A3": ("Didan, K. (2021). MODIS/Terra Vegetation Indices Monthly L3 Global 1km SIN Grid V061. NASA LP DAAC. "
                "https://doi.org/10.5067/MODIS/MOD13A3.061"),
    "GEOBOUNDARIES": ("Runfola, D. et al. (2020). geoBoundaries. PLoS ONE 15(4): e0231866. "
                      "https://doi.org/10.1371/journal.pone.0231866"),
}


def manifest() -> Manifest:
    return Manifest(DATA / "MANIFEST.json")
