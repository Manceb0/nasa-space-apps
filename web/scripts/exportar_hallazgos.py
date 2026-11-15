"""Hallazgos para la web, leídos de results/ (sin recalcular nada):
- MERRA-2: cambio de frecuencia de días >= 1 mm por recuadro (IMERG, CHIRPS, MERRA-2), después - antes de 2018-02.
- Puerto Rico: cambio por estación (pluviómetro GHCN-D frente a la celda IMERG) a 0,1, 1 y 5 mm, y el resumen.
- Ciclones y sequía: resumen (resultado negativo).
Solo biblioteca estándar. Ejecutar en Docker (galeria) con web/ montado.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "results" / "tropical"
OUT = ROOT / "web" / "public" / "data" / "tendencias" / "hallazgos.json"


def main():
    cells = {}
    for r in csv.DictReader(open(R / "merra2" / "cambio_frecuencia_por_celda.csv", encoding="utf-8")):
        c = cells.setdefault(r["celda"], {"lat": float(r["lat"]), "lon": float(r["lon"])})
        c[r["producto"]] = round(float(r["cambio_pp"]), 2)
    pr = []
    for r in csv.DictReader(open(R / "puerto_rico" / "cambio_por_estacion.csv", encoding="utf-8")):
        pr.append({"id": r["estacion"], "lat": float(r["lat"]), "lon": float(r["lon"]),
                   **{k: round(float(v), 2) for k, v in r.items() if k.startswith("cambio_")}})
    out = {
        "fuente": "results/tropical (merra2, puerto_rico, ciclones_sequia); ESTADO_CONCLUSIONES filas 4c, 4d, 7b y 26",
        "merra2": list(cells.values()),
        "pr": {"estaciones": pr, "resumen": json.loads((R / "puerto_rico" / "resumen.json").read_text(encoding="utf-8"))},
        "ciclones_sequia": json.loads((R / "ciclones_sequia" / "resumen.json").read_text(encoding="utf-8")),
    }
    assert len(out["merra2"]) == 15 and all({"IMERG", "CHIRPS", "MERRA2"} <= set(c) for c in out["merra2"]), "faltan recuadros"
    assert len(pr) == out["pr"]["resumen"]["estaciones"]
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(len(out["merra2"]), "recuadros;", len(pr), "estaciones de PR")


if __name__ == "__main__":
    main()
