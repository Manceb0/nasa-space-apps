"""Validación reproducible del paquete real, sin llamadas a proveedores ni interfaz.

python scripts/validar_backend_preparacion.py
Escribe resultados de escenarios y verificación HTTP en results/preparacion.
"""
from __future__ import annotations

import hashlib
import json
import sys
import threading
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from earthmemory.preparacion.motor import ENGINE_SHA256, investigate, instant, iso
from earthmemory.preparacion.servidor import make_handler


def main():
    dest = ROOT / "results/preparacion"
    package_path = dest / "paquete.json"
    raw = package_path.read_bytes()
    package = json.loads(raw)
    at = iso(datetime.now(timezone.utc))
    earliest = min(instant(r["first_seen_at"]) for s in package["sites"] for r in s["evidence"])
    before = iso(earliest - timedelta(seconds=1))
    checks, scenarios = [], {}

    def check(name, passed):
        checks.append({"check": name, "passed": bool(passed)})

    for name, disabled, cutoff in [("baseline", [], at), ("sin_gfs", ["GFS"], at),
                                    ("sin_era5", ["ERA5"], at), ("antes_captura", [], before)]:
        cases = [investigate(s, cutoff, disabled, graph=package["graph"]) for s in package["sites"]]
        scenarios[name] = {"decision_at": cutoff, "disabled_sources": disabled, "cases": cases}
    baseline = scenarios["baseline"]["cases"]
    check("four_pilots", len(baseline) == 4)
    check("no_ingestion_errors", all(not s["errors"] for s in package["sites"]))
    check("two_separate_forecasts_each_pilot", all(len(c["rain"]["models"]) == 2 for c in baseline))
    check("all_30_90_day_calendar_references_verified", all(len(c["drought"]["metrics"]) == 2 and
          all(m["calendar_reference_verified"] and m["reference_n"] >= 20 for m in c["drought"]["metrics"]) for c in baseline))
    check("producer_percentiles_match_engine", all(abs(m["percentile"] - original["percentile"]) < 1e-10
          for s, c in zip(package["sites"], baseline)
          for m, original in zip(c["drought"]["metrics"], next(r for r in s["evidence"] if r["source_id"] == "ERA5")["metrics"])))
    check("withdrawing_gfs_marks_missing", all("GFS" in c["missing"] for c in scenarios["sin_gfs"]["cases"]))
    check("withdrawing_gfs_preserves_ecmwf_numbers", all(
          next(m for m in a["rain"]["models"] if m["source"] == "ECMWF")["max48"] == b["rain"]["models"][0]["max48"]
          for a, b in zip(baseline, scenarios["sin_gfs"]["cases"])))
    check("withdrawing_era5_suppresses_deficit_claim", all(c["drought"]["state"] == "insufficient" for c in scenarios["sin_era5"]["cases"]))
    check("earlier_than_first_capture_has_no_weather_or_historical_support", all(
          c["rain"]["state"] == "insufficient" and c["drought"]["state"] == "insufficient" and not c["historical_context_sources"]
          for c in scenarios["antes_captura"]["cases"]))
    check("shared_forecast_input_family_reported", all(any(p["sources"] == ["ECMWF", "GFS"] and
          p["corroboration"] == "partially_dependent" for p in c["dependencies"]["pairs"]) for c in baseline))
    check("no_independence_probability_invented", all(not c["dependencies"]["probability_estimated"] for c in baseline))

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(package_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(base + "/api/preparacion", timeout=10) as response:
            api_package = json.load(response)
        check("http_package_hash_matches_disk", api_package["sha256"] == hashlib.sha256(raw).hexdigest())
        request = urllib.request.Request(base + "/api/investigacion", data=json.dumps({
            "site_id": "villa-riva", "decision_at": at, "disabled_sources": ["GFS"]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=10) as response:
            api_result = json.load(response)
        expected = next(c for c in scenarios["sin_gfs"]["cases"] if c["site_id"] == "villa-riva")
        check("http_and_pure_engine_identical", api_result["case"] == expected)
        check("http_engine_hash_identifies_loaded_engine", api_result["engine_sha256"] == ENGINE_SHA256)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    result = {"validated_at": at, "package_sha256": hashlib.sha256(raw).hexdigest(),
              "engine_sha256": ENGINE_SHA256, "external_network_used": False,
              "checks": checks, "scenarios": scenarios,
              "summary": [{"site": c["site_id"], "rain": c["rain"]["state"], "drought": c["drought"]["state"],
                  "metrics": [{k: m[k] for k in ("days", "total_mm", "percentile", "reference_n", "leave_one_year_out_range",
                                                 "deficit_class_stable_to_one_year")} for m in c["drought"]["metrics"]]} for c in baseline]}
    (dest / "VALIDACION_CIENTIFICA.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8", newline="\n")
    print(json.dumps({"passed": sum(c["passed"] for c in checks), "checks": len(checks), "summary": result["summary"]}, ensure_ascii=False))
    return 0 if all(c["passed"] for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
