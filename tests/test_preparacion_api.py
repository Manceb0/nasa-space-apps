"""Contrato de API local, usando exclusivamente evidencia sintética en memoria."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

from earthmemory.preparacion.servidor import evaluate_request, make_handler
from test_preparacion_motor import AT, forecast, site


def package():
    return {"version": 1, "generated_at": AT, "sites": [site([forecast(), forecast("GFS")])], "graph": {"nodes": [], "edges": []}}


class ScientificAPITests(unittest.TestCase):
    def test_server_does_not_backdate_local_capture(self):
        p = package()
        local = {"site_id": "test", "start": "2026-11-14T00:00:00Z", "end": "2026-11-15T00:00:00Z",
                 "mm": 5, "source": "SYNTHETIC", "synthetic": True, "first_seen_at": "2001-01-01T00:00:00Z"}
        r = evaluate_request(p, {"site_id": "test", "decision_at": AT, "measurements": [local]}, "2026-11-15T12:01:00Z")
        self.assertEqual(r["case"]["local"], [])
        self.assertEqual(r["case"]["excluded"][0]["reason"], "not_available_at_decision")

    def test_invalid_batch_is_atomic(self):
        with self.assertRaises(ValueError):
            evaluate_request(package(), {"site_id": "test", "disabled_sources": ["unknown"]}, AT)
        with self.assertRaises(ValueError):
            evaluate_request(package(), {"site_id": "test", "measurements": [
                {"site_id": "test", "start": "2026-11-14T00:00:00Z", "end": "2026-11-15T00:00:00Z", "mm": -5, "source": "SYNTHETIC"}
            ]}, AT)

    def test_http_contract_and_errors(self):
        with tempfile.TemporaryDirectory(prefix="stellar-science-test-") as temp:
            path = Path(temp) / "package.json"
            path.write_text(json.dumps(package()), encoding="utf-8")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(path))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urllib.request.urlopen(base + "/health") as response:
                    self.assertEqual(json.load(response)["status"], "ok")
                request = urllib.request.Request(base + "/api/investigacion", data=json.dumps({"site_id": "test", "decision_at": AT, "disabled_sources": ["GFS"]}).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(request) as response:
                    r = json.load(response)
                    self.assertEqual(r["case"]["rain"]["agreement"], "one_or_disagree")
                    self.assertTrue(r["package_sha256"])
                measurement = {"site_id": "test", "start": "2026-11-14T00:00:00Z", "end": "2026-11-15T00:00:00Z", "mm": 0, "source": "SYNTHETIC API TEST", "synthetic": True}
                request = urllib.request.Request(base + "/api/investigacion", data=json.dumps({"site_id": "test", "measurements": [measurement]}).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(request) as response:
                    stored = json.load(response)
                self.assertEqual(len(stored["measurement_ids"]), 1)
                request = urllib.request.Request(base + "/api/investigacion", data=json.dumps({"site_id": "test", "decision_at": AT, "measurement_ids": stored["measurement_ids"]}).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(request) as response:
                    replay = json.load(response)
                self.assertEqual(replay["case"]["local"], [])
                self.assertEqual(replay["measurement_ids"], stored["measurement_ids"])
                request = urllib.request.Request(base + "/api/investigacion", data=b'{"site_id":"missing"}', headers={"Content-Type": "application/json"})
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(request)
                self.assertEqual(error.exception.code, 404)
                request = urllib.request.Request(base + "/api/investigacion", data=b'{}', headers={"Content-Type": "text/plain"})
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(request)
                self.assertEqual(error.exception.code, 415)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
