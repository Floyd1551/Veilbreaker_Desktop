import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from veilbreaker import core
from veilbreaker.evidence import verify_bundle
from veilbreaker.survey import execute_survey, read_session, validate_steps, export_session, resume_survey, update_point_notes, session_lock


class SurveyTests(unittest.TestCase):
    def test_plan_limit_and_flags(self):
        for steps in ([], [{}]*21, [{"options": {"sdr": "false"}}], [{"options": {"run_id": "outside"}}]):
            with self.assertRaises(ValueError):
                validate_steps(steps)
        self.assertEqual(len(validate_steps([{}]*20)), 20)
        self.assertTrue(validate_steps([{"options": {"guided": True}}])[0]["options"]["active"])

    def test_twenty_runs_have_independent_evidence_and_numeric_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder, site_id="Survey 東京")
            with patch.object(core.VeilbreakerApplication, "collect_passive", side_effect=[({"latency_ms": i}, []) for i in range(20)]):
                result = execute_survey(cfg, "Twenty tests", [{"label": f"Point {i}"} for i in range(20)])
            session = result["survey"]
            self.assertEqual(session["status"], "complete")
            self.assertEqual(len({s["run_id"] for s in session["steps"]}), 20)
            self.assertEqual(session["numeric_summary"]["latency_ms"]["minimum"], 0)
            self.assertEqual(session["numeric_summary"]["latency_ms"]["median"], 9.5)
            self.assertEqual(verify_bundle(result["evidence_zip"])["status"], "verified")
            with zipfile.ZipFile(result["evidence_zip"]) as bundle:
                self.assertEqual(sum(n.endswith("_evidence.zip") for n in bundle.namelist()), 20)
                self.assertIn("comparison.csv", bundle.namelist())
                self.assertIn("survey_report.html", bundle.namelist())
                self.assertIn("Point 19", bundle.read("survey_report.html").decode("utf-8"))
            reopened = read_session(cfg, result["survey_path"])
            self.assertEqual(reopened["steps"][0]["metrics"]["latency_ms"], 0)

    def test_mixed_measurements_do_not_fill_missing_with_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            with patch.object(core.VeilbreakerApplication, "collect_passive", side_effect=[({"latency_ms": 0}, []), ({"rssi": -60}, [])]):
                result = execute_survey(cfg, "Mixed", [{}, {}])
            self.assertNotIn("latency_ms", result["survey"]["steps"][1]["metrics"])
            self.assertEqual(result["survey"]["numeric_summary"]["latency_ms"]["observed"], 1)

    def test_failed_step_keeps_completed_runs_and_continues(self):
        original = core.VeilbreakerApplication.run
        def failing(app, **kwargs):
            if kwargs["run_id"].endswith("-02"):
                raise OSError("Device unavailable")
            return original(app, **kwargs)
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            with patch.object(core.VeilbreakerApplication, "collect_passive", return_value=({"latency_ms": 1}, [])), patch.object(core.VeilbreakerApplication, "run", failing):
                result = execute_survey(cfg, "Mixed failures", [{}, {}, {}])
            self.assertEqual(result["survey"]["status"], "partial")
            self.assertEqual([s["status"] for s in result["survey"]["steps"]], ["complete", "failed", "complete"])

    def test_interruption_keeps_finished_steps_and_does_not_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            def interrupt(event):
                if event["source"].startswith("Test 2/"):
                    raise KeyboardInterrupt()
            with patch.object(core.VeilbreakerApplication, "collect_passive", return_value=({"latency_ms": 1}, [])) as collect:
                with self.assertRaises(KeyboardInterrupt):
                    execute_survey(cfg, "Interrupted", [{}, {}, {}], interrupt)
                self.assertEqual(collect.call_count, 1)
            path = next((cfg.root / "surveys").glob("*.json"))
            with patch("veilbreaker.survey.process_alive", return_value=False):
                session = read_session(cfg, path)
                pack = export_session(cfg, path)
            self.assertEqual(session["status"], "interrupted")
            self.assertEqual([s["status"] for s in session["steps"]], ["complete", "interrupted", "not_run"])
            self.assertEqual(verify_bundle(pack)["status"], "verified")

    def test_existing_run_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            app = core.VeilbreakerApplication(core.AppConfig(data_dir=folder))
            try:
                with patch.object(app, "collect_passive", return_value=({}, [])):
                    app.run(run_id="fixed")
                    with self.assertRaisesRegex(ValueError, "already exists"):
                        app.run(run_id="fixed")
                    with self.assertRaisesRegex(ValueError, "Invalid"):
                        app.run(run_id="../outside")
            finally:
                app.close()

    def test_manual_resume_preserves_settings_and_run_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder, site_id="Original site")
            with patch.object(core.VeilbreakerApplication, "collect_passive", return_value=({"latency_ms": 0}, [])) as collect:
                first = execute_survey(cfg, "Walk", [{}, {}, {}], manual=True)
                self.assertEqual(first["survey"]["status"], "paused")
                ids = [s["run_id"] for s in first["survey"]["steps"]]
                cfg.site_id = "Changed site"
                second = resume_survey(cfg, first["survey_path"])
                self.assertEqual(second["survey"]["status"], "paused")
                final = resume_survey(cfg, first["survey_path"])
                self.assertEqual(collect.call_count, 3)
                with self.assertRaisesRegex(ValueError, "No unrun"):
                    resume_survey(cfg, first["survey_path"])
            self.assertEqual(final["survey"]["status"], "complete")
            self.assertEqual([s["run_id"] for s in final["survey"]["steps"]], ids)
            store = core.VeilbreakerStore(cfg.db_path)
            try:
                self.assertTrue(all(store.get_run(i)["site_id"] == "Original site" for i in ids))
            finally:
                store.close()

    def test_notes_are_audited_and_original_evidence_is_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            with patch.object(core.VeilbreakerApplication, "collect_passive", return_value=({}, [])):
                result = execute_survey(cfg, "Walk", [{"notes": "Entrance"}, {}], manual=True)
            evidence = Path(result["survey"]["steps"][0]["evidence_zip"])
            original = evidence.read_bytes()
            session = update_point_notes(cfg, result["survey_path"], 0, "Entrance, door closed")
            self.assertEqual(session["steps"][0]["note_history"][0]["previous"], "Entrance")
            self.assertEqual(evidence.read_bytes(), original)
            pack = export_session(cfg, result["survey_path"])
            self.assertEqual(verify_bundle(pack)["status"], "verified")
            with zipfile.ZipFile(pack) as archive:
                self.assertFalse(any("settings" in name for name in archive.namelist()))
                self.assertIn("Entrance, door closed", archive.read("comparison.csv").decode("utf-8-sig"))
            with self.assertRaises(ValueError):
                update_point_notes(cfg, result["survey_path"], 0, "x" * 2001)
            with session_lock(result["survey_path"]):
                with self.assertRaisesRegex(ValueError, "another worker"):
                    resume_survey(cfg, result["survey_path"])
            update_point_notes(cfg, result["survey_path"], 1, "Roof")

    def test_interrupted_resume_skips_attempted_step(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            def interrupt(event):
                if event["source"].startswith("Test 2/"):
                    raise KeyboardInterrupt()
            with patch.object(core.VeilbreakerApplication, "collect_passive", return_value=({}, [])) as collect:
                with self.assertRaises(KeyboardInterrupt):
                    execute_survey(cfg, "Interrupted", [{}, {}, {}], interrupt)
                path = next((cfg.root / "surveys").glob("*.json"))
                with patch("veilbreaker.survey.process_alive", return_value=False):
                    final = resume_survey(cfg, path)
                self.assertEqual(collect.call_count, 2)
            self.assertEqual([s["status"] for s in final["survey"]["steps"]], ["complete", "interrupted", "complete"])
            self.assertEqual(final["survey"]["status"], "partial")
