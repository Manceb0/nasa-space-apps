"""Ingestión sin credenciales: pronósticos separados y referencia ERA5 coherente.

python -m earthmemory.preparacion.paquete [--sin-red]
Los datos sin procesar quedan en data/preparacion; results recibe un paquete fechado.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from .motor import valid_mm

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/preparacion"
OUT = ROOT / "results/preparacion/paquete.json"
SITES = [
    {"id": "bonao", "name": "Bonao", "lat": 18.937, "lon": -70.409, "province": "DO-28"},
    {"id": "cotui", "name": "Cotuí", "lat": 19.053, "lon": -70.149, "province": "DO-24"},
    {"id": "villa-riva", "name": "Villa Riva", "lat": 19.176, "lon": -69.908, "province": "DO-06"},
    {"id": "monte-cristi", "name": "Monte Cristi", "lat": 19.85, "lon": -71.65, "province": "DO-15"},
]
MODELS = {"ECMWF": "ecmwf_ifs025", "GFS": "gfs_global"}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalized_time(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # Las fechas sin zona vienen exclusivamente de consultas con timezone=GMT.
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def window(values: dict[date, float | None], end: date, days: int):
    part = [values.get(end - timedelta(days=i)) for i in range(days)]
    return sum(part) if all(valid_mm(v) for v in part) else None


def deficit_metrics(values: dict[date, float | None], end: date):
    out = []
    for days in (30, 90):
        total = window(values, end, days)
        ref, reference_windows = [], []
        for year in range(2001, 2025):
            # 29-feb se compara con 28-feb en años no bisiestos, explícito en método.
            try:
                ref_end = end.replace(year=year)
            except ValueError:
                ref_end = date(year, 2, 28)
            value = window(values, ref_end, days)
            if value is not None:
                ref.append(value)
                reference_windows.append({"year": year, "start": str(ref_end - timedelta(days=days - 1)),
                                          "end": str(ref_end), "total_mm": value})
        percentile = (100 * (sum(v < total for v in ref) + .5 * sum(v == total for v in ref)) / len(ref)
                      if total is not None and len(ref) >= 20 else None)
        out.append({"days": days, "total_mm": total, "percentile": percentile,
                    "reference_n": len(ref), "reference_totals_mm": ref,
                    "reference_windows": reference_windows,
                    "start": str(end - timedelta(days=days - 1)), "end": str(end)})
    return out


def fetch(key, base, params, offline=False):
    path = RAW / f"{key}.json"
    if offline:
        return json.loads(path.read_text(encoding="utf-8")), "cache"
    url = base + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "StellarHorizons/1.0 (Space Apps prototype)"})
            with urllib.request.urlopen(req, timeout=100) as response:
                data = json.load(response)
            if "error" in data:
                raise ValueError(data.get("reason"))
            first = now()
            if path.exists():
                old = json.loads(path.read_text(encoding="utf-8"))
                if old.get("response") == data:
                    first = old["first_seen_at"]
            envelope = {"url": url, "first_seen_at": first, "retrieved_at": now(), "response": data}
            RAW.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8", newline="\n")
            return envelope, "network"
        except Exception:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")), "cache_after_error"
    raise RuntimeError(f"Sin respuesta ni caché: {key}")


def record(site, source, envelope, mode, kind):
    d = envelope["response"]
    stamp = envelope["first_seen_at"]
    return {"id": f"{site['id']}:{source}:{stamp}", "source_id": source, "kind": kind,
            "site_id": site["id"], "requested": [site["lat"], site["lon"]],
            "returned": [d["latitude"], d["longitude"]], "issued_at": None,
            "first_seen_at": stamp, "retrieved_at": envelope.get("retrieved_at", stamp), "availability_basis": "first_capture_conservative",
            "quality": "provider", "delivery": mode, "provenance": envelope["url"],
            "sha256": hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()}


def collect(site, offline=False):
    evidence, errors = [], []
    for source, model in MODELS.items():
        try:
            env, mode = fetch(f"{site['id']}_{model}", "https://api.open-meteo.com/v1/forecast",
                              {"latitude": site["lat"], "longitude": site["lon"], "hourly": "precipitation",
                               "models": model, "forecast_days": 7, "timezone": "GMT"}, offline)
            d = env["response"]
            if d.get("hourly_units", {}).get("precipitation") != "mm":
                raise ValueError("Unidades de precipitación no reconocidas")
            r = record(site, source, env, mode, "forecast")
            r["model"] = model
            r["resolution"] = ("IFS 0.25°; native 3/6-hourly, provider hourly interpolation" if source == "ECMWF"
                               else "GFS surface ~0.11°; hourly, native 3-hourly after 120h")
            r["hourly"] = [{"time": normalized_time(t), "mm": v}
                           for t, v in zip(d["hourly"]["time"], d["hourly"]["precipitation"])]
            r["valid_start"], r["valid_end"] = r["hourly"][0]["time"], r["hourly"][-1]["time"]
            evidence.append(r)
        except Exception as exc:
            errors.append(f"{source}: {exc}")
    try:
        end = datetime.now(timezone.utc).date() - timedelta(days=5)
        env, mode = fetch(f"{site['id']}_era5", "https://archive-api.open-meteo.com/v1/archive",
                          {"latitude": site["lat"], "longitude": site["lon"], "daily": "precipitation_sum",
                           "models": "era5", "start_date": "2000-10-01", "end_date": str(end), "timezone": "GMT",
                           "cell_selection": "nearest"}, offline)
        d = env["response"]
        if d.get("daily_units", {}).get("precipitation_sum") != "mm":
            raise ValueError("Unidades ERA5 no reconocidas")
        values = {date.fromisoformat(t): v for t, v in zip(d["daily"]["time"], d["daily"]["precipitation_sum"])}
        valid = [t for t, v in values.items() if valid_mm(v)]
        if not valid:
            raise ValueError("ERA5 sin días válidos")
        end = max(valid)
        r = record(site, "ERA5", env, mode, "reanalysis")
        r["model"] = "era5"
        r["resolution"] = "ERA5 0.25°; daily aggregation"
        r["valid_start"] = normalized_time(str(end - timedelta(days=89)))
        r["valid_end"] = normalized_time(str(end + timedelta(days=1)))
        r["metrics"] = deficit_metrics(values, end)
        r["daily"] = [{"date": str(t), "mm": v} for t, v in values.items() if t >= end - timedelta(days=119)]
        evidence.append(r)
    except Exception as exc:
        errors.append(f"ERA5: {exc}")
    return {**site, "evidence": evidence, "errors": errors}


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--sin-red", action="store_true")
    args.add_argument("--exportar-web", action="store_true", help="Copia opcional del contrato JSON, sin modificar interfaz")
    opts = args.parse_args()
    with ThreadPoolExecutor(max_workers=2) as pool:
        sites = list(pool.map(lambda s: collect(s, opts.sin_red), SITES))
    trends = json.loads((ROOT / "web/public/data/tendencias/provincias.json").read_text(encoding="utf-8"))
    for site in sites:
        site["trends"] = {index: trends["tendencias"][index]["anual"].get(site["province"])
                          for index in ("SDII", "CDD", "PRCPTOT")}
        for source in ("IMERG", "CHIRPS"):
            stamp = now()
            site["evidence"].append({"id": f"{site['id']}:{source}:history", "source_id": source,
                "kind": "observation", "site_id": site["id"], "requested": [site["lat"], site["lon"]],
                "returned": [site["lat"], site["lon"]], "spatial_scope": "province_not_point",
                "valid_start": "2001-01-01T00:00:00Z", "valid_end": "2025-01-01T00:00:00Z",
                "issued_at": None, "first_seen_at": stamp, "retrieved_at": stamp,
                "availability_basis": "first_pack_capture_conservative", "quality": "provider",
                "delivery": "local_archive", "provenance": "data/tendencias/provincias.json",
                "sha256": hashlib.sha256(json.dumps(site["trends"], sort_keys=True).encode()).hexdigest()})
    priority_path = ROOT / "results/auditoria/donde_medir_prototipo.csv"
    import csv
    priorities = list(csv.DictReader(priority_path.open(encoding="utf-8"))) if priority_path.exists() else []
    backtest = json.loads((ROOT / "results/tropical/cierre_alertas/demo_yuna.json").read_text(encoding="utf-8"))
    graph = {
        "nodes": ["IMERG", "CHIRPS", "ERA5", "ECMWF", "GFS", "LOCAL", "GPCC", "GTS", "SATELLITES"],
        "edges": [
            ["IMERG", "ERA5", "dato auxiliar"], ["IMERG", "GPCC", "ajuste mensual"],
            ["GPCC", "GTS", "estaciones compartidas"], ["CHIRPS", "GTS", "estaciones compartidas"],
            ["ERA5", "SATELLITES", "asimilación"], ["ECMWF", "SATELLITES", "asimilación"],
            ["GFS", "SATELLITES", "asimilación"],
        ],
    }
    payload = {"version": 1, "generated_at": now(), "sites": sites, "graph": graph,
               "measurement_priority": priorities, "yuna_backtest": backtest,
               "methods": {"reference": "2001-2024", "minimum_reference_windows": 20,
                           "deficit_percentile": 20, "rain_exploratory_mm48": 100,
                           "percentile": "100*(count(reference<current)+0.5*count(reference=current))/n",
                           "leap_day": "29-feb compared to 28-feb in non-leap reference years",
                           "observations_are_not_forecasts": True}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        previous = OUT.read_bytes()
        archive = RAW / "packages"
        archive.mkdir(parents=True, exist_ok=True)
        (archive / f"{hashlib.sha256(previous).hexdigest()}.json").write_bytes(previous)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8", newline="\n")
    if opts.exportar_web:
        (ROOT / "web/public/data/preparacion.json").write_bytes(OUT.read_bytes())
    manifest = {"generated_at": payload["generated_at"], "sources": [
        {k: r[k] for k in ("id", "source_id", "first_seen_at", "requested", "returned", "provenance", "sha256", "delivery")}
        for site in sites for r in site["evidence"]], "errors": {s["id"]: s["errors"] for s in sites}}
    dest = ROOT / "results/preparacion"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"sites": [{"id": s["id"], "sources": len(s["evidence"]), "errors": s["errors"]} for s in sites]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
