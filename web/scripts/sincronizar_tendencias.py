"""Copia a la web los JSON de tendencias que produce el chat de datos (results/tendencias/web/).

La web solo lee: no recalcula nada. Ejecutar de nuevo cada vez que cambie la corrida
(por ejemplo, cuando llegue CHIRPS):

    uv run python web/scripts/sincronizar_tendencias.py
"""
from pathlib import Path
import json
import shutil

RAIZ = Path(__file__).resolve().parents[2]
ORIGEN = RAIZ / "results" / "tendencias" / "web"
DESTINO = RAIZ / "web" / "public" / "data" / "tendencias"
ARCHIVOS = ["variables.json", "provincias.json", "rejilla.json", "resumen.json", "CONTRATO.md"]

DESTINO.mkdir(parents=True, exist_ok=True)
for nombre in ARCHIVOS:
    src = ORIGEN / nombre
    if not src.exists():
        raise SystemExit(f"Falta {src}")
    if src.suffix == ".json":
        json.loads(src.read_text(encoding="utf-8"))  # que no esté a medio escribir
    shutil.copy2(src, DESTINO / nombre)
    print(f"{nombre}: {src.stat().st_size / 1024:.0f} kB")
v = json.loads((DESTINO / "variables.json").read_text(encoding="utf-8"))
print("productos:", ", ".join(v["productos"]), "· generado", v["generado_utc"])
