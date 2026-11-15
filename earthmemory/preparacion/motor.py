"""Motor científico puro, sin interfaz, red, credenciales ni dependencias externas.

Reglas v1: acumulados completos; comparación simultánea; disponibilidad conservadora;
percentiles descriptivos y sensibilidad al retirar un año, sin convertirlos en riesgo.
"""
from __future__ import annotations

import math
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from hashlib import sha256

RULE_VERSION = "municipal-evidence-1.0"
ENGINE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()


def instant(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp_required")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("explicit_timezone_required")
    return stamp.astimezone(timezone.utc)


def iso(stamp: datetime) -> str:
    return stamp.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def valid_mm(value) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def accumulations(samples: list[dict], hours: int, decision: str) -> list[dict]:
    if not isinstance(hours, int) or hours < 1:
        raise ValueError("positive_window_required")
    cutoff = instant(decision)
    rows = []
    for sample in samples:
        try:
            rows.append((instant(sample["time"]), sample.get("mm")))
        except (ValueError, TypeError, KeyError):
            # Un tiempo ilegible no se reemplaza ni se desplaza: no puede aportar lluvia.
            continue
    rows.sort(key=lambda r: r[0])
    out = []
    for index in range(hours - 1, len(rows)):
        part = rows[index - hours + 1:index + 1]
        end = part[-1][0]
        start = end - timedelta(hours=hours)
        if start < cutoff or end > cutoff + timedelta(days=7) or any(not valid_mm(v) for _, v in part):
            continue
        if any(part[k][0] - part[k - 1][0] != timedelta(hours=1) for k in range(1, len(part))):
            continue
        out.append({"start": iso(start), "end": iso(end), "mm": sum(v for _, v in part)})
    return out


def exclusion(record: dict, decision: str) -> str | None:
    cutoff = instant(decision)
    try:
        captured = instant(record["first_seen_at"])
        retrieved = instant(record["retrieved_at"])
        start, end = instant(record["valid_start"]), instant(record["valid_end"])
        lat, lon = record["returned"]
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (lat, lon)):
            return "invalid_coordinates"
        if abs(lat) > 90 or abs(lon) > 180 or start > end or retrieved < captured:
            return "invalid_metadata"
        issued = instant(record["issued_at"]) if record.get("issued_at") else None
        kind = record["kind"]
        if kind not in ("forecast", "observation", "reanalysis"):
            return "invalid_kind"
    except (KeyError, TypeError, ValueError):
        return "invalid_metadata"
    if captured > cutoff or retrieved > cutoff:
        return "not_available_at_decision"
    if issued and issued > cutoff:
        return "future_issue"
    if kind != "forecast" and end > cutoff:
        return "future_observation"
    if kind == "forecast" and record.get("quality") != "provider":
        return "unverified_forecast"
    if kind == "forecast" and record.get("source_id") not in ("ECMWF", "GFS"):
        return "unsupported_forecast_source"
    if kind == "forecast" and (cutoff - retrieved > timedelta(hours=12) or end <= cutoff):
        return "expired_forecast"
    if kind == "reanalysis" and cutoff - end > timedelta(days=8):
        return "old_reanalysis"
    return None


def percentile(total: float, reference: list[float]) -> float:
    if not valid_mm(total) or not reference or not all(valid_mm(v) for v in reference):
        raise ValueError("invalid_percentile_inputs")
    return 100 * (sum(v < total for v in reference) + .5 * sum(v == total for v in reference)) / len(reference)


def reference_metric(metric: dict) -> dict:
    """Recalcula desde los totales: no confía en percentiles aportados en el JSON."""
    ref = metric.get("reference_totals_mm", [])
    total = metric.get("total_mm")
    if not isinstance(ref, list) or len(ref) < 20 or len(ref) != metric.get("reference_n"):
        raise ValueError("insufficient_reference")
    if not valid_mm(total) or not all(valid_mm(v) for v in ref):
        raise ValueError("invalid_reference")
    if metric.get("days") not in (30, 90):
        raise ValueError("unsupported_deficit_window")
    current_end = datetime.fromisoformat(metric["end"]).date()
    current_start = datetime.fromisoformat(metric["start"]).date()
    if (current_end - current_start).days + 1 != metric["days"]:
        raise ValueError("invalid_deficit_interval")
    detail = metric.get("reference_windows")
    if detail is not None:
        if len(detail) != len(ref) or len({r["year"] for r in detail}) != len(ref):
            raise ValueError("duplicate_reference_year")
        for row, expected in zip(detail, ref):
            end = datetime.fromisoformat(row["end"]).date()
            start = datetime.fromisoformat(row["start"]).date()
            day = 28 if (current_end.month, current_end.day) == (2, 29) and end.month == 2 and end.day == 28 else current_end.day
            if row["year"] not in range(2001, 2025) or end.year != row["year"] or (end.month, end.day) != (current_end.month, day) or (end - start).days + 1 != metric["days"] or row["total_mm"] != expected:
                raise ValueError("reference_calendar_mismatch")
    score = percentile(total, ref)
    leave_one_out = [percentile(total, ref[:i] + ref[i + 1:]) for i in range(len(ref))] if len(ref) >= 21 else []
    return {**metric, "percentile": score, "rank_resolution_pct": 100 / len(ref),
            "calendar_reference_verified": detail is not None,
            "leave_one_year_out_range": [min(leave_one_out), max(leave_one_out)] if leave_one_out else None,
            "deficit_class_stable_to_one_year": all((p <= 20) == (score <= 20) for p in leave_one_out) if leave_one_out else None,
            "sensitivity_is_confidence_interval": False}


def local_evidence(value: dict, site: dict, captured: str) -> dict:
    start, end, at = instant(value["start"]), instant(value["end"]), instant(captured)
    if value.get("site_id") != site["id"] or start >= end or end > at:
        raise ValueError("invalid_local_interval_or_site")
    if not valid_mm(value.get("mm")) or not isinstance(value.get("source"), str) or len(value["source"].strip()) < 3:
        raise ValueError("invalid_local_value_or_provenance")
    if "synthetic" in value and not isinstance(value["synthetic"], bool):
        raise ValueError("invalid_synthetic_flag")
    has_coords = "lat" in value or "lon" in value
    lat, lon = (value.get("lat"), value.get("lon")) if has_coords else (site["lat"], site["lon"])
    if not all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v) for v in (lat, lon)) or abs(lat) > 90 or abs(lon) > 180:
        raise ValueError("invalid_local_coordinates")
    return {"id": f"local:{site['id']}:{captured}", "source_id": "LOCAL", "kind": "observation",
            "site_id": site["id"], "requested": [site["lat"], site["lon"]], "returned": [lat, lon],
            "spatial_scope": "instrument_coordinates_user_reported" if has_coords else "municipality_report_location_unspecified",
            "valid_start": iso(start), "valid_end": iso(end), "issued_at": None,
            "first_seen_at": captured, "retrieved_at": captured, "availability_basis": "user_entry",
            "quality": "synthetic" if value.get("synthetic") else "unverified", "provenance": value["source"].strip(),
            "precipitation_mm": value["mm"]}


def dependencies(graph: dict | None, sources: list[str]) -> dict:
    """Solapamiento cualitativo de familias de insumos; no estima correlaciones."""
    edges = (graph or {}).get("edges", [])
    def ancestors(source):
        pending, seen = [source], set()
        while pending:
            current = pending.pop()
            for child, parent, *_ in edges:
                if child == current and parent not in seen:
                    seen.add(parent)
                    pending.append(parent)
        seen.discard(source)
        return seen
    pairs = []
    for index, left in enumerate(sorted(set(sources))):
        for right in sorted(set(sources))[index + 1:]:
            a, b = ancestors(left), ancestors(right)
            shared = sorted(a & b)
            direct = right in a or left in b
            pairs.append({"sources": [left, right], "shared_input_families": shared,
                          "upstream_relationship": direct,
                          "corroboration": "partially_dependent" if shared or direct else "independence_not_established"})
    return {"pairs": pairs, "probability_estimated": False,
            "limit": "Non-exhaustive input-family graph; shared station identities and error correlations are not established"}


def investigate(site: dict, decision: str, disabled=(), local=(), graph=None) -> dict:
    instant(decision)  # Una fecha inválida detiene el análisis, no se sustituye por ahora.
    excluded, eligible = [], []
    for record in [*site.get("evidence", []), *[r for r in local if r.get("site_id") == site["id"]]]:
        if record.get("site_id") != site["id"]:
            reason = "different_site"
        elif record.get("source_id") in disabled:
            reason = "removed_by_user"
        else:
            reason = exclusion(record, decision)
        if reason:
            excluded.append({"id": record.get("id"), "source": record.get("source_id"), "reason": reason})
        else:
            eligible.append(record)
    latest, grouped = {}, {}
    for record in eligible:
        if record["kind"] == "observation":
            continue
        source = record["source_id"]
        grouped.setdefault(source, []).append(record)
    for source, records in grouped.items():
        newest = max(instant(r["first_seen_at"]) for r in records)
        tied = [r for r in records if instant(r["first_seen_at"]) == newest]
        fingerprints = {json.dumps({k: r.get(k) for k in ("model", "returned", "valid_start", "valid_end", "hourly", "metrics", "quality")}, sort_keys=True) for r in tied}
        if len(fingerprints) != 1:
            excluded.extend({"id": r["id"], "source": source, "reason": "conflicting_snapshots"} for r in records)
        else:
            latest[source] = max(tied, key=lambda r: instant(r["retrieved_at"]))
    models = []
    for record in latest.values():
        if record["kind"] != "forecast":
            continue
        w24 = accumulations(record.get("hourly", []), 24, decision)
        w48 = accumulations(record.get("hourly", []), 48, decision)
        models.append({"source": record["source_id"], "record_id": record["id"],
                       "coordinates": record["returned"], "requested_coordinates": record["requested"],
                       "spatial_scope": "representative_model_cell_not_municipal_coverage",
                       "max24": max(w24, key=lambda w: w["mm"]) if w24 else None,
                       "max48": max(w48, key=lambda w: w["mm"]) if w48 else None,
                       "complete_windows_24h": len(w24), "complete_windows_48h": len(w48),
                       "_windows": {w["end"]: w for w in w48}})
    candidates = []
    for end in sorted({end for m in models for end in m["_windows"]}):
        values = [m["_windows"].get(end, {}).get("mm") for m in models]
        candidates.append({"end": end, "values": values, "votes": sum(v is not None and v > 100 for v in values),
                           "peak": max(v for v in values if v is not None)})
    # Se fija el intervalo más extremo, no el que maximiza el acuerdo entre fuentes.
    chosen = min(candidates, key=lambda c: (-c["peak"], c["end"])) if candidates else None
    for i, model in enumerate(models):
        model["same_window_mm"] = chosen["values"][i] if chosen else None
        del model["_windows"]
    covered = [m for m in models if m["max48"] is not None]
    watch = any(m["max48"]["mm"] > 100 for m in covered)
    agreement = ("two_partially_dependent" if chosen and chosen["votes"] == 2 else
                 "one_or_disagree" if watch else "below_exploratory_rule" if covered else "no_complete_window")
    era = latest.get("ERA5")
    metrics, metric_errors = [], []
    for metric in (era or {}).get("metrics", []):
        try:
            metrics.append(reference_metric(metric))
        except (ValueError, TypeError, KeyError):
            metric_errors.append({"days": metric.get("days"), "reason": "invalid_or_insufficient_reference"})
    reports = [r for r in eligible if r["source_id"] == "LOCAL"]
    actual_reports = [r for r in reports if r["quality"] != "synthetic"]
    missing = [source for source in ("ECMWF", "GFS") if not any(m["source"] == source for m in covered)]
    if not metrics:
        missing.append("ERA5_reference")
    if not actual_reports:
        missing.append("local_measurement")
    context = [r["source_id"] for r in eligible if r["source_id"] in ("IMERG", "CHIRPS")]
    if "IMERG" not in context:
        missing.append("NASA_planning_context")
    tasks = [{"id": "official_bulletin", "reason": "decision_requires_official_context"}]
    if watch:
        tasks.append({"id": "rain_interval", "reason": "forecast_exceeds_exploratory_rule"})
    if watch and agreement != "two_partially_dependent":
        tasks.append({"id": "resolve_models", "reason": "no_joint_model_confirmation"})
    if any(m["percentile"] <= 20 for m in metrics):
        tasks.append({"id": "water_availability", "reason": "rainfall_deficit_is_not_measured_impact"})
    if any(m["deficit_class_stable_to_one_year"] is False for m in metrics):
        tasks.append({"id": "reference_sensitivity", "reason": "classification_changes_when_one_reference_year_is_removed"})
    if not context:
        tasks.append({"id": "historical_context", "reason": "no_eligible_historical_sources"})
    tasks.append({"id": "verify_local_provenance" if actual_reports else "obtain_local_measurement",
                  "reason": "unverified_report" if actual_reports else "missing_independent_measurement"})
    return {"rule_version": RULE_VERSION, "site_id": site["id"], "decision_at": decision,
            "rain": {"state": "insufficient" if not covered else "watch" if watch else "below_rule",
                     "agreement": agreement, "models": models,
                     "selection_rule": "largest_model_48h_total_then_earliest_end_not_maximum_agreement",
                     "window": {"start": iso(instant(chosen["end"]) - timedelta(hours=48)), "end": chosen["end"]} if chosen else None},
            "drought": {"state": "insufficient" if not metrics else "deficit" if any(m["percentile"] <= 20 for m in metrics) else "not_below_p20",
                        "metrics": metrics, "record_id": era["id"] if era else None, "metric_errors": metric_errors},
            "historical_context_sources": sorted(set(context)), "local": reports, "missing": missing,
            "dependencies": dependencies(graph, [*latest.keys(), *context]),
            "supporting": ([{"claim": "same_window_exceedance", "sources": [m["source"] for m in models if m["same_window_mm"] is not None and m["same_window_mm"] > 100],
                             "independence": "not_assumed"}] if watch else []) +
                          ([{"claim": "provincial_historical_context", "sources": sorted(set(context))}] if context else []),
            "contradictions": ([{"claim": "largest_rain_window_not_jointly_confirmed", "sources": [m["source"] for m in models]}]
                               if watch and agreement != "two_partially_dependent" else []),
            "excluded": excluded, "tasks": tasks,
            "limits": ["Prototype, not an official warning", "Agreement is not independent votes or probability",
                       "Reference percentiles are descriptive, not impact predictions", "No damage reduction validation"]}
