"""Ríos principales de República Dominicana para el mapa de crestas: OpenStreetMap (© colaboradores de OSM, ODbL),
vía Overpass. Se piden los cauces con nombre de los ríos grandes, se unen los tramos de cada río y se simplifican
(Douglas-Peucker, 0,004°). Solo biblioteca estándar.
Ejecutar: MSYS_NO_PATHCONV=1 docker compose run --rm -v "$(pwd -W)/web:/app/web" \
  --entrypoint "uv run --frozen --no-sync python web/scripts/exportar_rios.py" galeria
"""
from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web" / "public" / "data" / "tendencias" / "rios.json"
NOMBRES = ["Yaque del Norte", "Yaque del Sur", "Yuna", "Camú", "Ozama", "Isabela", "Nizao", "Haina", "Higuamo",
           "Chavón", "Soco", "Bajabonico", "Mao", "Guayubín", "Jima", "Ocoa", "Nigua", "Boba", "Nagua", "Bao", "Amina",
           "Maimón", "Licey", "Jaya", "Dajabón", "Masacre", "Macasía", "Artibonito", "Bajo Yuna", "Payabo", "Cuaba"]
BBOX = (17.4, -72.05, 20.05, -68.3)


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy) or 1e-12
    d = [abs(dy * (x - x0) - dx * (y - y0)) / n for x, y in pts[1:-1]]
    i = max(range(len(d)), key=d.__getitem__)
    if d[i] > eps:
        return rdp(pts[: i + 2], eps)[:-1] + rdp(pts[i + 1:], eps)
    return [pts[0], pts[-1]]


def main():
    rx = "|".join(NOMBRES)
    q = f'[out:json][timeout:120];way["waterway"="river"]["name"~"(R[ií]o )?({rx})$",i]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});out geom;'
    data = None
    for intento in range(4):
        try:
            req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(),
                                         headers={"User-Agent": "earth-trend-detective/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read())
            break
        except Exception as e:  # noqa: BLE001
            print("reintento", e, flush=True)
            time.sleep(15 * (intento + 1))
    if data is None:
        raise SystemExit("Overpass no respondió")
    by = {}
    for w in data["elements"]:
        if w.get("type") != "way" or "geometry" not in w:
            continue
        name = w["tags"]["name"]
        pts = [(round(p["lon"], 4), round(p["lat"], 4)) for p in w["geometry"]]
        by.setdefault(name, []).append(rdp(pts, 0.004))
    rios = []
    for name, parts in by.items():
        total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for p in parts for a, b in zip(p, p[1:]))
        if total < 0.12:  # tramos sueltos muy cortos
            continue
        rios.append({"name": name, "len_deg": round(total, 3), "parts": parts})
    rios.sort(key=lambda r: -r["len_deg"])
    OUT.write_text(json.dumps({"fuente": "OpenStreetMap (© colaboradores de OSM, ODbL) vía Overpass", "rios": rios},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(len(rios), "ríos;", sum(len(p) for r in rios for p in r["parts"]), "puntos;", [r["name"] for r in rios[:12]])


if __name__ == "__main__":
    main()
