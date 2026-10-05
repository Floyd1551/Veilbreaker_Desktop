import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from veilbreaker import core
from veilbreaker.survey import execute_survey
from veilbreaker.survey_compare import compare_visits, compare_saved_visits


class VisitComparisonTests(unittest.TestCase):
    def setUp(self):
        self.a = {"survey_id": "a", "site_id": "Site", "scenario": "general", "steps": [
            {"label": "Roof", "run_id": "a-1", "status": "complete", "options": {}, "metrics": {"latency_ms": 0, "rssi": -60}}]}
        self.b = copy.deepcopy(self.a)
        self.b["survey_id"] = "b"
        self.b["steps"][0]["run_id"] = "b-1"
        self.b["steps"][0]["metrics"] = {"latency_ms": 10, "rssi": -55}

    def test_signed_deltas_keep_zero_and_inputs_unchanged(self):
        original = copy.deepcopy(self.a)
        rows = compare_visits(self.a, self.b, True)["rows"]
        self.assertEqual([r["delta"] for r in rows], [10, 5])
        self.assertEqual(rows[0]["baseline"], 0)
        self.assertEqual(self.a, original)

    def test_missing_points_metrics_and_reordered_points(self):
        self.b["steps"].insert(0, {"label": "Office", "run_id": "b-2", "status": "complete", "options": {}, "metrics": {"latency_ms": 9}})
        del self.b["steps"][1]["metrics"]["rssi"]
        rows = compare_visits(self.a, self.b, True)["rows"]
        self.assertEqual(rows[0]["delta"], 10)
        self.assertIsNone(rows[1]["current"])
        self.assertIsNone(rows[1]["delta"])
        self.assertIsNone(rows[2]["baseline"])

    def test_incompatible_or_partial_collections_withhold_deltas(self):
        for change in ({"status": "partial"}, {"options": {"sdr": True}}):
            b = copy.deepcopy(self.b)
            b["steps"][0].update(change)
            self.assertTrue(all(r["delta"] is None for r in compare_visits(self.a, b, True)["rows"]))
        self.assertTrue(all(r["delta"] is None for r in compare_visits(self.a, self.b)["rows"]))
        self.b["scenario"] = "other"
        self.assertTrue(all(r["delta"] is None for r in compare_visits(self.a, self.b, True)["rows"]))

    def test_rejects_ambiguous_matching_and_different_sites(self):
        with self.assertRaises(ValueError):
            compare_visits(self.a, self.a)
        self.b["site_id"] = "Elsewhere"
        with self.assertRaises(ValueError):
            compare_visits(self.a, self.b)
        self.b["site_id"] = "Site"
        self.b["steps"] *= 2
        with self.assertRaisesRegex(ValueError, "unique"):
            compare_visits(self.a, self.b)

    def test_non_numeric_and_nonfinite_values_do_not_get_deltas(self):
        for value in (False, "10", float("nan"), float("inf"), {"a": 1}):
            self.b["steps"][0]["metrics"]["latency_ms"] = value
            self.assertIsNone(compare_visits(self.a, self.b, True)["rows"][0]["delta"])

    def test_saved_snapshots_control_comparison_without_mutating_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            with patch.object(core.VeilbreakerApplication, "collect_passive", side_effect=[({"latency_ms": 1}, []), ({"latency_ms": 3}, [])]):
                a = execute_survey(cfg, "First", [{"label": "Roof"}])
                b = execute_survey(cfg, "Second", [{"label": "Roof"}])
            original = Path(a["evidence_zip"]).read_bytes()
            result = compare_saved_visits(cfg, a["survey_path"], b["survey_path"])
            self.assertTrue(result["settings_match"])
            self.assertEqual(result["rows"][0]["delta"], 2)
            snapshot = Path(b["survey_path"]).parent / "settings" / Path(b["survey_path"]).name
            value = json.loads(snapshot.read_text(encoding="utf-8")); value["scenario"] = "changed"
            snapshot.write_text(json.dumps(value), encoding="utf-8")
            self.assertFalse(compare_saved_visits(cfg, a["survey_path"], b["survey_path"])["settings_match"])
            snapshot.unlink()
            self.assertFalse(compare_saved_visits(cfg, a["survey_path"], b["survey_path"])["settings_match"])
            self.assertEqual(Path(a["evidence_zip"]).read_bytes(), original)
