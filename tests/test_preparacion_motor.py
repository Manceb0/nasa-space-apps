"""Invariantes científicas del motor Python; fixtures explícitamente sintéticos."""
import copy
import unittest
from datetime import datetime, timedelta, timezone

from earthmemory.preparacion import motor as m

AT = "2026-11-15T12:00:00Z"


def forecast(source="ECMWF", amount=3, length=168):
    start = m.instant(AT)
    return {"id": source, "source_id": source, "kind": "forecast", "site_id": "test",
            "requested": [19, -70], "returned": [19, -70], "valid_start": AT,
            "valid_end": m.iso(start + timedelta(hours=length)), "issued_at": None,
            "first_seen_at": AT, "retrieved_at": AT, "quality": "provider",
            "hourly": [{"time": m.iso(start + timedelta(hours=i + 1)), "mm": amount} for i in range(length)]}


def site(records):
    return {"id": "test", "lat": 19, "lon": -70, "evidence": records, "trends": {}}


class ScientificMotorTests(unittest.TestCase):
    def test_cyclone_calendar_does_not_gate_rain_attention_or_imply_active_storm(self):
        guide = m.decision_guidance("villa-riva", "2026-01-15T00:00:00Z", "watch", False)
        self.assertFalse(guide["atlantic_climatological_season"])
        self.assertEqual(guide["decisions_to_verify"][0]["id"], "verify_heavy_rain_preparedness")
        self.assertEqual(guide["current_cyclone_status"], "not_ingested_calendar_is_not_an_active_storm")

    def test_yuna_requires_camu_and_dam_inputs_instead_of_assuming_total_regulation(self):
        guide = m.decision_guidance("villa-riva", AT, "below_rule", False)
        self.assertIn("upstream_camu_rain_and_river_status", guide["domain_information_missing"])
        self.assertIn("Hatillo does not regulate the entire Yuna basin", guide["hydrological_connections"])
        self.assertTrue(guide["no_threshold_exceedance_is_not_flood_clearance"])

    def test_deficit_does_not_cancel_heavy_rain_attention(self):
        guide = m.decision_guidance("bonao", AT, "watch", True)
        self.assertEqual({d["id"] for d in guide["decisions_to_verify"]}, {"verify_heavy_rain_preparedness", "verify_water_availability"})
        self.assertFalse(guide["operational_benefit_validated"])

    def test_unknown_territory_does_not_inherit_yuna_hydrology(self):
        guide = m.decision_guidance("unknown", AT, "insufficient", False)
        self.assertEqual(guide["territorial_profile"], "not_characterized")
        self.assertEqual(guide["hydrological_connections"], [])

    def test_dependencies_follow_shared_upstream_inputs_without_independence_claims(self):
        graph = {"edges": [["IMERG", "ERA5", "auxiliary"], ["ERA5", "SATELLITES", "assimilation"],
                           ["GFS", "SATELLITES", "assimilation"]]}
        result = m.dependencies(graph, ["IMERG", "ERA5", "GFS", "LOCAL"])
        pairs = {tuple(p["sources"]): p for p in result["pairs"]}
        self.assertEqual(pairs[("GFS", "IMERG")]["shared_input_families"], ["SATELLITES"])
        self.assertTrue(pairs[("ERA5", "IMERG")]["upstream_relationship"])
        self.assertEqual(pairs[("IMERG", "LOCAL")]["corroboration"], "independence_not_established")
        self.assertFalse(result["probability_estimated"])

    def test_zero_missing_gap_and_same_series(self):
        self.assertEqual(m.accumulations(forecast(amount=0)["hourly"], 48, AT)[0]["mm"], 0)
        missing = forecast(length=48)["hourly"]
        missing[20]["mm"] = None
        self.assertEqual(m.accumulations(missing, 48, AT), [])
        gap = forecast(length=49)["hourly"]
        gap.pop(20)
        self.assertEqual(m.accumulations(gap, 48, AT), [])
        self.assertEqual(m.accumulations(forecast()["hourly"], 48, AT)[0]["mm"], 144)

    def test_two_peaks_at_different_times_are_not_confirmation(self):
        a, b = forecast(amount=0), forecast("GFS", amount=0)
        for row in a["hourly"][:24]:
            row["mm"] = 6
        for row in b["hourly"][-24:]:
            row["mm"] = 6
        result = m.investigate(site([a, b]), AT)
        self.assertEqual(result["rain"]["state"], "watch")
        self.assertEqual(result["rain"]["agreement"], "one_or_disagree")
        self.assertTrue(all(r["max48"]["mm"] > 100 for r in result["rain"]["models"]))

    def test_remove_source_changes_support_not_weather(self):
        s = site([forecast(), forecast("GFS")])
        self.assertEqual(m.investigate(s, AT)["rain"]["agreement"], "two_partially_dependent")
        result = m.investigate(s, AT, {"GFS"})
        self.assertEqual(result["rain"]["agreement"], "one_or_disagree")
        self.assertIn("GFS", result["missing"])
        self.assertEqual(result["rain"]["models"][0]["max48"]["mm"], 144)

    def test_window_is_not_chosen_to_maximize_agreement(self):
        a, b = forecast(amount=0), forecast("GFS", amount=0)
        for row in a["hourly"][:24]:
            row["mm"] = 20
        for row in a["hourly"][-24:]:
            row["mm"] = 5
        for row in b["hourly"][-24:]:
            row["mm"] = 5
        result = m.investigate(site([a, b]), AT)
        self.assertEqual(result["rain"]["agreement"], "one_or_disagree")
        self.assertEqual(result["rain"]["models"][0]["same_window_mm"], 480)
        self.assertEqual(result["rain"]["models"][1]["same_window_mm"], 0)

    def test_capture_retrieval_issue_and_observation_cannot_come_from_future(self):
        for field in ("first_seen_at", "retrieved_at", "issued_at"):
            f = forecast()
            f[field] = "2026-11-15T12:01:00Z"
            self.assertEqual(m.investigate(site([f]), AT)["rain"]["state"], "insufficient")
        f = forecast()
        f.update(kind="observation", source_id="LOCAL")
        self.assertEqual(m.investigate(site([f]), AT)["local"], [])

    def test_stale_unknown_coordinate_and_other_site_excluded(self):
        f = forecast()
        f["first_seen_at"] = f["retrieved_at"] = "2026-11-14T00:00:00Z"
        self.assertEqual(m.exclusion(f, AT), "expired_forecast")
        f = forecast()
        f["returned"] = [None, -70]
        self.assertEqual(m.exclusion(f, AT), "invalid_coordinates")
        f = forecast()
        f["site_id"] = "another"
        self.assertEqual(m.investigate(site([f]), AT)["excluded"][0]["reason"], "different_site")

    def test_duplicate_snapshots_do_not_vote_and_conflicts_are_not_hidden(self):
        f = forecast()
        duplicate = copy.deepcopy(f)
        duplicate["id"] = "copy"
        self.assertEqual(len(m.investigate(site([f, duplicate]), AT)["rain"]["models"]), 1)
        duplicate["hourly"][0]["mm"] = 500
        result = m.investigate(site([f, duplicate]), AT)
        self.assertEqual(result["rain"]["state"], "insufficient")
        self.assertTrue(all(r["reason"] == "conflicting_snapshots" for r in result["excluded"]))

    def test_percentile_recomputed_and_sensitivity_is_not_confidence(self):
        metric = {"days": 30, "start": "2026-10-12", "end": "2026-11-10", "total_mm": 1,
                  "reference_n": 24, "reference_totals_mm": [0] + [2] * 23, "percentile": 99}
        output = m.reference_metric(metric)
        self.assertAlmostEqual(output["percentile"], 100 / 24)
        self.assertTrue(output["deficit_class_stable_to_one_year"])
        self.assertFalse(output["sensitivity_is_confidence_interval"])
        metric["reference_n"] = 19
        metric["reference_totals_mm"] = [0] * 19
        with self.assertRaises(ValueError):
            m.reference_metric(metric)

    def test_local_zero_unverified_and_synthetic_not_independent_measurement(self):
        s = site([forecast()])
        value = {"site_id": "test", "start": "2026-11-14T00:00:00Z", "end": "2026-11-15T00:00:00Z",
                 "mm": 0, "source": "SYNTHETIC TEST FIXTURE"}
        r = m.local_evidence(value, s, AT)
        self.assertEqual(r["quality"], "unverified")
        self.assertEqual(m.investigate(s, AT, local=[r])["rain"]["agreement"], "one_or_disagree")
        r = m.local_evidence(dict(value, synthetic=True), s, AT)
        self.assertIn("local_measurement", m.investigate(s, AT, local=[r])["missing"])
        for patch in ({"mm": -1}, {"start": "2026-11-14T00:00"}, {"lat": 99, "lon": 0}):
            with self.assertRaises(ValueError):
                m.local_evidence(dict(value, **patch), s, AT)

    def test_reference_calendar_is_checked(self):
        metric = {"days": 30, "start": "2026-10-12", "end": "2026-11-10", "total_mm": 1,
                  "reference_n": 20, "reference_totals_mm": [1] * 20,
                  "reference_windows": [{"year": y, "start": f"{y}-10-12", "end": f"{y}-11-10", "total_mm": 1} for y in range(2001, 2021)]}
        self.assertEqual(m.reference_metric(metric)["percentile"], 50)
        metric["reference_windows"][0]["end"] = "2001-12-10"
        with self.assertRaises(ValueError):
            m.reference_metric(metric)

    def test_borderline_percentile_reports_reference_sensitivity(self):
        metric = {"days": 30, "start": "2026-10-12", "end": "2026-11-10", "total_mm": 1,
                  "reference_n": 24, "reference_totals_mm": [0] * 5 + [2] * 19}
        result = m.reference_metric(metric)
        self.assertGreater(result["percentile"], 20)
        self.assertLessEqual(result["leave_one_year_out_range"][0], 20)
        self.assertFalse(result["deficit_class_stable_to_one_year"])


if __name__ == "__main__":
    unittest.main()
