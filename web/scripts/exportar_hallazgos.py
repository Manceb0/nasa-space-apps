"""Hallazgos para la web, leídos de results/ (sin recalcular nada):
- MERRA-2: cambio de frecuencia de días >= 1 mm por recuadro (IMERG, CHIRPS, MERRA-2), después - antes de 2018-02.
- Puerto Rico: cambio por estación (pluviómetro GHCN-D frente a la celda IMERG) a 0,1, 1 y 5 mm, y el resumen.
- Hawái (GOES-West): lo mismo que Puerto Rico; dos escalones (era_gpm) y alcance (OpenAlex).
- Predicciones: el registro de trazabilidad (results/tropical/trazabilidad/registro.json).
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
        "fuente": "results/tropical (merra2, puerto_rico, hawaii, era_gpm, alcance, trazabilidad, ciclones_sequia); ESTADO_CONCLUSIONES filas 4c, 4d, 7b, 8b, 8c, 8d y 26",
        "merra2": list(cells.values()),
        "pr": {"estaciones": pr, "resumen": json.loads((R / "puerto_rico" / "resumen.json").read_text(encoding="utf-8"))},
        "ciclones_sequia": json.loads((R / "ciclones_sequia" / "resumen.json").read_text(encoding="utf-8")),
    }
    # Hawái (GOES-West): mismo cálculo que Puerto Rico, 41 pluviómetros
    hi = []
    for r in csv.DictReader(open(R / "hawaii" / "cambio_por_estacion.csv", encoding="utf-8")):
        hi.append({"id": r["estacion"], "lat": float(r["lat"]), "lon": float(r["lon"]),
                   **{k: round(float(v), 2) for k, v in r.items() if k.startswith("cambio_")}})
    out["hi"] = {"estaciones": hi, "resumen": json.loads((R / "hawaii" / "resumen.json").read_text(encoding="utf-8"))}
    # dos escalones: medias anuales de (IMERG - testigo) en Hawái, Puerto Rico y la RD frente a CHIRPS
    out["era_gpm"] = json.loads((R / "era_gpm" / "resumen.json").read_text(encoding="utf-8"))
    out["alcance"] = {b["busqueda"]: b["trabajos"] for b in json.loads((R / "alcance" / "openalex.json").read_text(encoding="utf-8"))["busquedas"]}
    # predicciones escritas antes de calcular: el registro de trazabilidad (hora, script, huellas y commit)
    reg = json.loads((R / "trazabilidad" / "registro.json").read_text(encoding="utf-8"))
    preds = []
    for t in reg["pruebas"]:
        for q in t["predicciones"]:
            v = q["veredicto"].strip().lower()
            ok = True if v == "se cumple" else False if v == "no se cumple" else None
            preds.append({"id": q["id"], "texto": q["texto"], "estudio": t["prueba"], "cumplida": ok, "veredicto": q["veredicto"],
                          "registradas": t.get("registradas"), "commit": (t.get("commit_predicciones") or {}).get("commit")})
    assert len(preds) == reg["resumen"]["predicciones"], "faltan predicciones"
    assert sum(p["cumplida"] is True for p in preds) == reg["resumen"]["se_cumplen"]
    assert sum(p["cumplida"] is False for p in preds) == reg["resumen"]["no_se_cumplen"]
    out["predicciones"] = preds
    out["registro"] = reg["resumen"]
    # grados de certeza: la tabla de ESTADO_CONCLUSIONES.md
    import re
    conc, sec = [], ""
    for line in (ROOT / "reports_nacional" / "ESTADO_CONCLUSIONES.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            sec = line[3:].strip()
        m = re.match(r"^\| *([0-9]+[a-z]?) *\| *(.+?) *\| *(.+?) *\|", line)
        if m and sec and not sec.lower().startswith("correcciones"):
            grado = re.sub(r"\*\*", "", m.group(3)).strip()
            conc.append({"id": m.group(1), "texto": re.sub(r"\*\*", "", m.group(2)).strip(), "grado": grado, "seccion": sec})
    # la fila 8 conserva su redacción antigua en la tabla; en la web se lee con lo que ya sabemos (filas 8 y 8b)
    for c in conc:
        if c["id"] == "8":
            c["texto"] = "El GOES-16 no basta como causa del cambio de IMERG (Hawái, bajo GOES-West, también pierde días); queda como candidato del escalón caribeño de 2018"
    out["conclusiones"] = conc
    assert len(out["merra2"]) == 15 and all({"IMERG", "CHIRPS", "MERRA2"} <= set(c) for c in out["merra2"]), "faltan recuadros"
    assert len(pr) == out["pr"]["resumen"]["estaciones"]
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    assert len(hi) == out["hi"]["resumen"]["estaciones"]
    print(len(out["merra2"]), "recuadros;", len(pr), "estaciones de PR;", len(hi), "de Hawái;", len(preds), "predicciones;", len(conc), "conclusiones")


if __name__ == "__main__":
    main()
