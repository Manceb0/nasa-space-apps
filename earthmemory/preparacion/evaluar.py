"""CLI científico: evalúa paquetes y retiradas sin tocar una interfaz.

python -m earthmemory.preparacion.evaluar --en 2026-11-15T17:00:00Z --sin-fuente GFS
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .motor import ENGINE_SHA256, investigate, instant, iso, local_evidence
from .paquete import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paquete", type=Path, default=ROOT / "results/preparacion/paquete.json")
    parser.add_argument("--en", help="ISO con zona; omitido = captura de esta solicitud")
    parser.add_argument("--sitio", choices=["bonao", "cotui", "villa-riva", "monte-cristi"])
    parser.add_argument("--sin-fuente", action="append", default=[])
    parser.add_argument("--mediciones", type=Path, help="Objeto o lista LocalInput; se captura al ejecutar, no se retrofecha")
    parser.add_argument("--salida", type=Path, default=ROOT / "results/preparacion/evaluacion.json")
    args = parser.parse_args()
    if args.en is not None:
        instant(args.en)
    source = args.paquete.read_bytes()
    package = json.loads(source)
    capture = iso(datetime.now(timezone.utc))
    at = args.en or capture
    sites = [s for s in package["sites"] if args.sitio is None or s["id"] == args.sitio]
    local = []
    if args.mediciones:
        if args.mediciones.stat().st_size > 1_000_000:
            raise ValueError("measurement_file_too_large")
        values = json.loads(args.mediciones.read_text(encoding="utf-8"))
        values = values if isinstance(values, list) else [values]
        if not 1 <= len(values) <= 100:
            raise ValueError("invalid_measurement_count")
        by_id = {s["id"]: s for s in package["sites"]}
        local = [dict(local_evidence(v, by_id[v["site_id"]], capture), id=f"local:{capture}:{i}") for i, v in enumerate(values)]
    result = {"package_sha256": hashlib.sha256(source).hexdigest(), "decision_at": at,
              "engine_sha256": ENGINE_SHA256,
              "disabled_sources": args.sin_fuente,
              "derived_context_available": instant(package["generated_at"]) <= instant(at),
              "cases": [investigate(s, at, set(args.sin_fuente), local, package.get("graph")) for s in sites]}
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(args.salida), "cases": [{"site": c["site_id"], "rain": c["rain"]["state"],
        "drought": c["drought"]["state"], "excluded": len(c["excluded"])} for c in result["cases"]]}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, FileNotFoundError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from exc
