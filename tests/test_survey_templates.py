import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from veilbreaker import core
from veilbreaker.survey import execute_survey
from veilbreaker.survey_templates import save_template, load_template


class TemplateTests(unittest.TestCase):
    def test_roundtrip_strips_visit_data_and_creates_fresh_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "template.json"
            save_template(path, "Repeat visit 東京", [{"label": "Roof", "options": {}, "notes": "Old observation", "run_id": "old", "metrics": {"rssi": -50}}], True)
            plan = load_template(path)
            self.assertEqual(plan["steps"][0]["label"], "Roof")
            self.assertNotIn("notes", plan["steps"][0])
            self.assertNotIn("run_id", plan["steps"][0])
            cfg = core.AppConfig(data_dir=folder)
            with patch.object(core.VeilbreakerApplication, "collect_passive", return_value=({}, [])):
                visits = [execute_survey(cfg, plan["name"], plan["steps"], manual=plan["manual"]) for _ in range(2)]
            self.assertNotEqual(visits[0]["survey"]["survey_id"], visits[1]["survey"]["survey_id"])
            self.assertNotEqual(visits[0]["evidence_zip"], visits[1]["evidence_zip"])

    def test_invalid_template_does_not_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "template.json"
            path.write_text("original", encoding="utf-8")
            for steps, manual in [([], True), ([{}]*21, True), ([{"options": {"sdr": "false"}}], True), ([{}], "false")]:
                with self.assertRaises(ValueError):
                    save_template(path, "Test", steps, manual)
                self.assertEqual(path.read_text(encoding="utf-8"), "original")

    def test_rejects_session_unknown_version_and_oversized_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "template.json"
            for value in [{"schema_version": 1, "steps": [{}]}, {"format": "veilbreaker-survey-template", "version": 2}]:
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_template(path)
            path.write_bytes(b" " * (128*1024+1))
            with self.assertRaisesRegex(ValueError, "128 KiB"):
                load_template(path)
