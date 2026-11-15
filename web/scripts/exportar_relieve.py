"""Perfiles de relieve para la vista «Crestas» de la pantalla Tendencias.

Muestrea el mismo DEM que la pieza 3 de la galería (Copernicus GLO-90 a 1/300°, data/nacional_hr/derivados/nativas.npz):
una fila cada 0.03° de latitud (la fila del DEM más cercana) y una muestra cada 2 columnas (1/150°), recortado a la
rejilla de tendencias. No calcula ninguna estadística: el color lo pone la web con las clases de rejilla.json.

    docker compose run --rm -v "$PWD/web:/app/web" --entrypoint "uv run --frozen --no-sync python web/scripts/exportar_relieve.py" galeria
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEM = ROOT / "data/nacional_hr/derivados/nativas.npz"
REJ = ROOT / "web/public/data/tendencias/rejilla.json"
CUENCA = ROOT / "results/yuna/cuencas_yuna.geojson"
HATILLO = ROOT / "results/yuna/hatillo_ficha.json"
OUT = ROOT / "web/public/data/tendencias/relieve.json"
PASO = 0.03


def anillo_yuna() -> list[list[float]]:
    doc = json.loads(CUENCA.read_text(encoding="utf-8"))
    f = next((f for f in doc["features"] if f["properties"].get("zona") == "yuna"), doc["features"][0])
    g = f["geometry"]
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    ring = max((p[0] for p in polys), key=len)
    step = max(1, len(ring) // 500)
    out = ring[::step]
    if out[-1] != ring[-1]:
        out.append(ring[-1])
    return out


def main() -> None:
    z = np.load(DEM)
    Z, lat, lon = z["dem_Z"].astype(float), z["dem_lat"].astype(float), z["dem_lon"].astype(float)
    if lat[0] > lat[-1]:
        Z, lat = Z[::-1], lat[::-1]
    rej = json.loads(REJ.read_text(encoding="utf-8"))
    x0, x1 = rej["lon_bordes"][0], rej["lon_bordes"][-1]
    cols = np.flatnonzero((lon >= x0) & (lon <= x1))[::2]
    lon_s = lon[cols]
    filas = []
    for la in np.arange(19.95, 17.50 - 1e-9, -PASO):
        i = int(np.argmin(np.abs(lat - la)))
        r = Z[i, cols]
        r = np.where(np.isfinite(r) & (r > 0), np.round(r), 0).astype(int)
        filas.append({"lat": round(float(la), 3), "z": r.tolist()})

    def elev(y: float, x: float) -> int:
        v = Z[int(np.argmin(np.abs(lat - y))), int(np.argmin(np.abs(lon - x)))]
        return int(round(v)) if np.isfinite(v) and v > 0 else 0

    ring = [[round(x, 4), round(y, 4), elev(y, x)] for x, y in anillo_yuna()]
    txt = json.loads(HATILLO.read_text(encoding="utf-8"))["coordenadas_cortina"]
    hy, hx = (float(v) for v in txt.split("(")[1].split(")")[0].split(","))
    sub = Z[:, (lon >= x0) & (lon <= x1)]
    lon_sub = lon[(lon >= x0) & (lon <= x1)]
    im = np.unravel_index(np.nanargmax(sub), sub.shape)
    doc = {
        "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fuente": "Copernicus GLO-90 DEM (ESA/Airbus, AWS open data), mosaico 1/300° del motor de alta resolución",
        "dem_sha256": hashlib.sha256(DEM.read_bytes()).hexdigest(),
        "metodo": f"Fila del DEM más cercana cada {PASO}° de latitud; una muestra cada 2 columnas (1/150°). 0 = mar o sin dato.",
        "lon0": round(float(lon_s[0]), 6), "dlon": round(float(np.median(np.diff(lon_s))), 8), "nlon": int(lon_s.size),
        "paso_lat": PASO, "filas": filas,
        "yuna": ring,
        "hatillo": {"lat": hy, "lon": hx, "z": elev(hy, hx)},
        "pico": {"lat": round(float(lat[im[0]]), 4), "lon": round(float(lon_sub[im[1]]), 4), "z": int(round(sub[im]))},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(OUT, f"{OUT.stat().st_size / 1024:.0f} KB", len(filas), "filas ×", lon_s.size, "· pico", doc["pico"])


if __name__ == "__main__":
    main()
