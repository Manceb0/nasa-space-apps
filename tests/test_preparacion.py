"""Pruebas del emparejamiento estacional: no necesita descargas ni pandas."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import date, timedelta
from earthmemory.preparacion import paquete
from earthmemory.preparacion.paquete import deficit_metrics, normalized_time, window


class PreparationTests(unittest.TestCase):
    def test_provider_outage_preserves_cached_capture_and_values(self):
        cached = {"first_seen_at": "2026-11-15T12:00:00Z", "retrieved_at": "2026-11-15T12:00:00Z",
                  "url": "https://example.invalid", "response": {"value": 0}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.json"
            path.write_text(json.dumps(cached), encoding="utf-8")
            with patch.object(paquete, "RAW", Path(tmp)), patch.object(paquete.urllib.request, "urlopen", side_effect=OSError("offline")), patch.object(paquete.time, "sleep"):
                result, mode = paquete.fetch("test", "https://example.invalid", {})
            self.assertEqual(result, cached)
            self.assertEqual(mode, "cache_after_error")
            self.assertEqual(json.loads(path.read_text()), cached)

    def setUp(self):
        start = date(2000, 10, 1)
        self.values = {start + timedelta(days=i): 1.0 for i in range((date(2026, 11, 10)-start).days+1)}

    def test_zero_is_data_missing_is_not(self):
        end = date(2026, 11, 10)
        self.values[end] = 0
        self.assertEqual(window(self.values, end, 2), 1)
        self.values[end] = None
        self.assertIsNone(window(self.values, end, 2))

    def test_reference_is_24_calendar_matched_windows(self):
        rows = deficit_metrics(self.values, date(2026, 11, 10))
        for row in rows:
            self.assertEqual(row["reference_n"], 24)
            self.assertEqual(row["total_mm"], row["days"])
            self.assertEqual(row["percentile"], 50)

    def test_missing_reference_prevents_percentile(self):
        for year in range(2001, 2007):
            self.values[date(year, 11, 10)] = None
        for row in deficit_metrics(self.values, date(2026, 11, 10)):
            self.assertEqual(row["reference_n"], 18)
            self.assertIsNone(row["percentile"])

    def test_leap_day_and_utc(self):
        self.assertEqual(normalized_time("2026-11-15T12:00"), "2026-11-15T12:00:00Z")
        self.assertEqual(normalized_time("2026-11-15"), "2026-11-15T00:00:00Z")
        rows = deficit_metrics(self.values, date(2024, 2, 29))
        self.assertEqual(rows[0]["reference_n"], 24)


if __name__ == "__main__":
    unittest.main()
