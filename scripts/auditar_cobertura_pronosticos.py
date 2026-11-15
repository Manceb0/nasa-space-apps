"""Cruza fechas del catálogo con el inicio documentado de archivos de pronóstico.

No descarga corridas ni confunde cobertura nominal con anticipación validada.
"""
import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "results/tropical/cierre_alertas/eventos.csv"
SOURCES = [
    {"id": "NCAR_GFS_025", "documented_start": "2015-01-15",
     "url": "https://gdex.ucar.edu/datasets/d084001/", "kind": "archived_operational_forecasts"},
    {"id": "ECMWF_TIGGE", "documented_start": "2006-10-01",
     "url": "https://www.ecmwf.int/en/forecasts/datasets/tigge-global-medium-range-ensemble-forecasts-multiple-nwp-centres-2006",
     "kind": "archived_multi_centre_ensemble_forecasts"},
]


def main():
    with CATALOG.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    events = {r["evento"]: r for r in rows if r["periodo"] == "2016-2024" and r["regla"] == "IMERG"}
    candidates = []
    for source in SOURCES:
        candidates.append({**source, "coverage_status": "documented_start_only_not_file_availability",
            "events": [{"event": key, "catalog_start_date": r["inicio_catalogo"],
                        "after_documented_archive_start": date.fromisoformat(r["inicio_catalogo"]) >= date.fromisoformat(source["documented_start"]),
                        "forecast_files_retrieved": False, "precipitation_variable_verified": False,
                        "publication_time_verified": False, "local_operational_access_verified": False,
                        "onset_hour_and_timezone_verified": False, "validated_lead_time": None}
                       for key, r in sorted(events.items())]})
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "catalog_sha256": hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
        "test_events": len(events), "sources": candidates, "new_forecast_backtest_executed": False,
        "limits": ["Archive start is not proof of continuous coverage, download access or an event-specific forecast file",
                   "Forecast initialization is not publication time or availability to a Dominican municipality",
                   "Catalogue dates lack onset hours/timezone verification; no operational lead time is established",
                   "Reforecasts or later analyses cannot substitute for originally issued forecast runs",
                   "Non-event intervals must be included to evaluate unmatched signal episodes"]}
    dest = ROOT / "results/preparacion/COBERTURA_ARCHIVOS_PRONOSTICO.json"
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"test_events": len(events), "sources": [{"id": s["id"], "nominal_date_candidates": sum(e["after_documented_archive_start"] for e in s["events"]),
          "retrieved_runs": 0, "validated_lead_times": 0} for s in candidates]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
