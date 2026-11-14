"""Empaqueta para la web la lluvia mensual IMERG V07 (0,1°) que ya bajó el chat de datos.

No hace ningún análisis: solo convierte mm/h a mm/mes, conserva cada celda en su centro real
y marca qué celdas tienen el centro dentro de República Dominicana (geoBoundaries ADM1).
Las anomalías se calculan en el navegador, a la vista, contra la media de cada mes de 2001 a 2024.

Uso: uv run python web/scripts/empaquetar_rejilla.py
"""
import calendar
import glob
import json
import re
from pathlib import Path

import h5py
import numpy as np
from matplotlib.path import Path as MPath

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "nacional" / "gesdisc" / "GPM_3IMERGM.07"
LIM = ROOT / "data" / "nacional" / "limites" / "geoBoundaries-DOM-ADM1.geojson"
OUT = ROOT / "web" / "public" / "data" / "grid" / "precip_imerg.json"

files = sorted(glob.glob(str(SRC / "*.nc4")))
assert len(files) == 288, f"se esperaban 288 meses, hay {len(files)}"
with h5py.File(files[0], "r") as h:
    lats = h["lat"][:].astype(float)
    lons = h["lon"][:].astype(float)

# Máscara: centro de la celda dentro de algún polígono ADM1 de RD
polys = []
for feat in json.loads(LIM.read_text(encoding="utf-8"))["features"]:
    g = feat["geometry"]
    rings = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    for poly in rings:
        polys.append(MPath(np.array(poly[0])))
mask = np.zeros((len(lats), len(lons)), dtype=bool)
for i, la in enumerate(lats):
    for j, lo in enumerate(lons):
        mask[i, j] = any(p.contains_point((lo, la)) for p in polys)

meses, valores = [], []
for f in files:
    m = re.search(r"3IMERG\.(\d{4})(\d{2})01", f)
    y, mo = int(m.group(1)), int(m.group(2))
    with h5py.File(f, "r") as h:
        pr = h["precipitation"][0].astype(float).T  # (lat, lon)
    pr[pr < 0] = np.nan
    mm = pr * 24 * calendar.monthrange(y, mo)[1]  # mm/h -> mm/mes
    mm[~mask] = np.nan
    meses.append(f"{y}-{mo:02d}")
    valores.append([[None if np.isnan(v) else round(float(v), 1) for v in row] for row in mm[::-1]])  # norte arriba

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "variable": "precip",
    "nombre": "Lluvia mensual",
    "unidad": "mm/mes",
    "fuente": "NASA GPM IMERG Final Precipitation L3 1 month 0.1° V07 (GES DISC)",
    "cita": "Huffman et al. 2023, doi:10.5067/GPM/IMERG/3B-MONTH/07",
    "resolucion_grados": 0.1,
    "bbox": [float(lons.min()) - 0.05, float(lats.min()) - 0.05, float(lons.max()) + 0.05, float(lats.max()) + 0.05],
    "lats": [round(float(v), 3) for v in lats[::-1]],
    "lons": [round(float(v), 3) for v in lons],
    "meses": meses,
    "valores": valores,
    "metodo": "Sin análisis: mm/h × horas del mes. Solo celdas con el centro dentro de RD (geoBoundaries ADM1).",
}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(OUT, f"{OUT.stat().st_size / 1e6:.1f} MB", int(mask.sum()), "celdas en RD")
