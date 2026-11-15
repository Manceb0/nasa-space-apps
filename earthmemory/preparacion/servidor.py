"""API local del motor científico. Sin interfaz, archivos arbitrarios ni secretos.

python -m earthmemory.preparacion.servidor --port 4178
GET /health, GET /api/preparacion, POST /api/investigacion
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from uuid import uuid4

from .motor import ENGINE_SHA256, RULE_VERSION, instant, investigate, iso, local_evidence
from .paquete import ROOT

MAX_BODY = 1_000_000
SOURCES = {"ECMWF", "GFS", "ERA5", "IMERG", "CHIRPS", "LOCAL"}


class UnknownSiteError(ValueError):
    pass


def evaluate_request(package: dict, payload: dict, capture_time: str, previous_measurements=()) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("object_required")
    site = next((s for s in package["sites"] if s["id"] == payload.get("site_id")), None)
    if site is None:
        raise UnknownSiteError("unknown_site")
    at = payload.get("decision_at", capture_time)
    instant(at)
    disabled = payload.get("disabled_sources", [])
    measurements = payload.get("measurements", [])
    if not isinstance(disabled, list) or any(not isinstance(s, str) or s not in SOURCES for s in disabled):
        raise ValueError("invalid_disabled_sources")
    if not isinstance(measurements, list) or len(measurements) > 100:
        raise ValueError("invalid_measurements")
    local = [*previous_measurements, *[dict(local_evidence(v, site, capture_time), id=f"local:{site['id']}:{capture_time}:{i}:{uuid4().hex}")
             for i, v in enumerate(measurements)]]
    result = investigate(site, at, set(disabled), local, package.get("graph"))
    return {"rule_version": RULE_VERSION, "server_capture_at": capture_time,
            "engine_sha256": ENGINE_SHA256,
            "disabled_sources": disabled, "measurement_ids": [r["id"] for r in local],
            "case": result, "source_records": [*site["evidence"], *local],
            "package_generated_at": package["generated_at"],
            "derived_context_available": instant(package["generated_at"]) <= instant(at),
            "source_graph": package["graph"]}


def make_handler(package_path: Path, allowed_origins=()):
    measurements = {}
    ledger_lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body):
            content = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            origin = self.headers.get("Origin")
            if origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(content)

        def package(self):
            raw = package_path.read_bytes()
            package = json.loads(raw)
            if package.get("version") != 1:
                raise ValueError("unsupported_package_version")
            return package, hashlib.sha256(raw).hexdigest()

        def do_OPTIONS(self):
            origin = self.headers.get("Origin")
            if origin not in allowed_origins:
                self.reply(403, {"error": "origin_not_allowed"})
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Vary", "Origin")
            self.end_headers()

        def do_GET(self):
            if self.path == "/health":
                self.reply(200, {"status": "ok", "rule_version": RULE_VERSION})
                return
            if self.path != "/api/preparacion":
                self.reply(404, {"error": "not_found"})
                return
            try:
                package, digest = self.package()
                self.reply(200, {"package": package, "sha256": digest})
            except (OSError, ValueError, KeyError, TypeError):
                self.reply(503, {"error": "package_unavailable_or_invalid"})

        def do_POST(self):
            if self.path != "/api/investigacion":
                self.reply(404, {"error": "not_found"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.reply(400, {"error": "invalid_content_length"})
                return
            if not 0 < size <= MAX_BODY:
                self.reply(413, {"error": "body_size_outside_limits"})
                return
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                self.reply(415, {"error": "application_json_required"})
                return
            try:
                package, digest = self.package()
            except (OSError, ValueError, KeyError, TypeError):
                self.reply(503, {"error": "package_unavailable_or_invalid"})
                return
            try:
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("object_required")
                ids = payload.get("measurement_ids", [])
                if not isinstance(ids, list) or len(ids) > 100 or any(not isinstance(i, str) for i in ids):
                    raise ValueError("invalid_measurement_ids")
                with ledger_lock:
                    if any(i not in measurements for i in ids):
                        raise ValueError("unknown_measurement_id")
                    previous = [measurements[i] for i in dict.fromkeys(ids)]
                    if any(r["site_id"] != payload.get("site_id") for r in previous):
                        raise ValueError("measurement_site_mismatch")
                response = evaluate_request(package, payload, iso(datetime.now(timezone.utc)), previous)
            except UnknownSiteError as exc:
                self.reply(404, {"error": str(exc)})
                return
            except (ValueError, KeyError, TypeError) as exc:
                self.reply(400, {"error": str(exc)})
                return
            response["package_sha256"] = digest
            with ledger_lock:
                measurements.update({r["id"]: r for r in response["source_records"] if r["source_id"] == "LOCAL"})
            self.reply(200, response)

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4178)
    parser.add_argument("--paquete", type=Path, default=ROOT / "results/preparacion/paquete.json")
    parser.add_argument("--allow-origin", action="append", default=[])
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.paquete, args.allow_origin))
    print(f"Scientific API http://127.0.0.1:{server.server_port} · {RULE_VERSION}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
