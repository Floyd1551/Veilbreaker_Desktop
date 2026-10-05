import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from veilbreaker import core
from veilbreaker.gui import MainWindow, STYLE
from veilbreaker.jobs import DEMO_METRICS


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = MainWindow(core.AppConfig(data_dir=self.temp.name))
        self.errors = []
        self.window.error = self.errors.append

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.temp.cleanup()

    def wait_job(self):
        deadline = time.monotonic() + 30
        while self.window.process is not None and time.monotonic() < deadline:
            QTest.qWait(30)
        self.assertIsNone(self.window.process, "Worker timed out")

    def test_demo_does_not_write_history(self):
        self.window.show_demo()
        self.assertEqual(self.window.payload["run_id"], "demo")
        self.assertFalse(self.window.export_button.isEnabled())
        self.assertFalse(self.window.config.db_path.exists())

    def test_worker_analysis_history_and_reopen(self):
        source = Path(self.temp.name) / "metrics.json"
        source.write_text(json.dumps(DEMO_METRICS), encoding="utf-8")
        self.window.start_job("analyze", input=str(source))
        self.assertFalse(self.window.run_button.isEnabled())
        self.wait_job()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.window.history.rowCount(), 1)
        self.assertTrue(self.window.export_button.isEnabled())
        self.window.history.selectRow(0)
        self.window.open_history()
        self.assertEqual(self.window.metrics.rowCount(), len(DEMO_METRICS))
        self.assertEqual(self.window.collection_table.rowCount(), 1)
        self.assertEqual(self.window.metrics.item(0, 2).text(), "imported_metrics")
        collection_file = Path(self.window.history_rows[0]["artifact_dir"]) / "collection.json"
        collection_file.unlink()
        self.window.open_history()
        self.assertEqual(self.window.collection_table.rowCount(), 0)
        self.assertIn("Collection details unavailable", self.window.summary.toPlainText())

    def test_worker_failure_is_displayed(self):
        source = Path(self.temp.name) / "metrics.json"
        source.write_text("[]", encoding="utf-8")
        self.window.start_job("analyze", input=str(source))
        self.wait_job()
        self.assertIn("JSON object", self.errors[0])
        self.assertTrue(self.window.run_button.isEnabled())

    def test_verify_dialog_dispatches_and_displays_result(self):
        source = Path(self.temp.name) / "metrics.json"
        source.write_text(json.dumps(DEMO_METRICS), encoding="utf-8")
        self.window.start_job("analyze", input=str(source))
        self.wait_job()
        with patch("veilbreaker.gui.QFileDialog.getOpenFileName", return_value=(self.window.payload["evidence_zip"], "")):
            self.window.verify_evidence()
        self.wait_job()
        self.assertEqual(self.errors, [])
        self.assertEqual(json.loads(self.window.tool_output.toPlainText())["status"], "verified")

    def test_cancel_resets_controls(self):
        self.window.start_job("selftest")
        self.window.process.waitForStarted(5000)
        self.window.cancel_task()
        self.wait_job()
        self.assertEqual(self.errors, [])
        self.assertTrue(self.window.run_button.isEnabled())

    def test_network_settings_save_and_conflict_protection(self):
        destination = Path(self.temp.name) / "settings.json"
        self.window.network_fields["public_ping_target"].setText("8.8.8.8")
        with patch("veilbreaker.core.default_config_path", return_value=destination), patch.object(self.window, "start_job") as start:
            self.window.save_network_settings()
        start.assert_not_called()
        self.assertEqual(self.window.config.public_ping_target, "8.8.8.8")
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))["public_ping_target"], "8.8.8.8")
        original = destination.read_bytes()
        self.window.network_fields["public_ping_target"].setText("https://bad.example")
        with patch("veilbreaker.core.default_config_path", return_value=destination):
            self.window.save_network_settings()
        self.assertEqual(destination.read_bytes(), original)
        raw = self.window.config.to_dict(); raw["dns_test_host"] = "edited.example"
        self.window.config_editor.setPlainText(json.dumps(raw))
        self.window.save_network_settings()
        self.assertIn("advanced JSON edits", self.errors[-1])
        self.assertEqual(destination.read_bytes(), original)

    def test_history_search_clears_selection_and_finds_old_run(self):
        store = core.VeilbreakerStore(self.window.config.db_path)
        try:
            for i in range(205):
                store.db.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (f"run-{i:04}", "2026-10-02", "Site", "field_validation", "{}", "{}", "", "needle" if i == 0 else "routine"))
            store.db.commit()
        finally:
            store.close()
        self.window.refresh_history()
        self.assertEqual(self.window.history.rowCount(), 200)
        self.assertTrue(self.window.history_next.isEnabled())
        self.window.page_history(200)
        self.assertEqual(self.window.history.rowCount(), 5)
        self.window.history.selectRow(0)
        self.window.history_search.setText("needle")
        self.window.search_history()
        self.assertEqual(self.window.history.rowCount(), 1)
        self.assertIsNone(self.window.selected_run())
        self.assertEqual(self.window.history_rows[0]["run_id"], "run-0000")
        self.assertFalse(self.window.history_next.isEnabled())

    def test_settings_reject_invalid_json(self):
        self.window.config_editor.setPlainText("{")
        self.window.save_settings()
        self.assertIn("not saved", self.errors[0])

    def test_survey_queue_limit_and_dispatch(self):
        page = self.window.survey_page
        self.window.flags["sdr"].setChecked(True)
        page.copies.setValue(20)
        page.add_steps()
        self.assertEqual(len(page.steps), 20)
        page.add_steps()
        self.assertIn("at most 20", self.errors[-1])
        with patch.object(self.window, "start_job") as start:
            page.start()
        self.assertEqual(start.call_args.args[0], "survey")
        self.assertEqual(len(start.call_args.kwargs["steps"]), 20)
        self.assertIn("capture_settings", start.call_args.kwargs)
        self.assertTrue(start.call_args.kwargs["manual"])

    def test_template_load_reviews_queue_without_starting_worker(self):
        from veilbreaker.survey_templates import save_template
        path = Path(self.temp.name) / "plan.json"
        save_template(path, "Return visit", [{"label": "Roof", "options": {"active": True}}], False)
        page = self.window.survey_page
        with patch("veilbreaker.survey_ui.QFileDialog.getOpenFileName", return_value=(str(path), "")), patch.object(self.window, "start_job") as start:
            page.load_queue_template()
        start.assert_not_called()
        self.assertEqual(page.name.text(), "Return visit")
        self.assertFalse(page.manual.isChecked())
        self.assertTrue(page.steps[0]["options"]["active"])
        self.assertIn("active", page.queue.item(0, 2).text())
        path.write_text("{}", encoding="utf-8")
        with patch("veilbreaker.survey_ui.QFileDialog.getOpenFileName", return_value=(str(path), "")):
            page.load_queue_template()
        self.assertEqual(page.steps[0]["label"], "Roof")

    def test_visit_comparison_dialog_and_export(self):
        from veilbreaker.survey import execute_survey
        from PySide6.QtWidgets import QTableWidget, QPushButton
        with patch.object(core.VeilbreakerApplication, "collect_passive", side_effect=[({"latency_ms": 0}, []), ({"latency_ms": 7}, [])]):
            execute_survey(self.window.config, "Baseline", [{"label": "Roof"}])
            current = execute_survey(self.window.config, "Current", [{"label": "Roof"}])
        self.window.survey_page.show_session(current["survey"], current["survey_path"])
        output = Path(self.temp.name) / "comparison.json"
        def inspect(dialog):
            rows = dialog.findChild(QTableWidget)
            self.assertEqual(rows.item(0, 2).text(), "0")
            self.assertEqual(rows.item(0, 4).text(), "7")
            next(b for b in dialog.findChildren(QPushButton) if b.text().startswith("Export comparison")).click()
            return 0
        with patch("veilbreaker.survey_ui.QDialog.exec", inspect), patch("veilbreaker.survey_ui.QFileDialog.getSaveFileName", return_value=(str(output), "")):
            self.window.survey_page.compare_visit()
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["rows"][0]["delta"], 7)
        self.assertEqual(self.errors, [])

    def test_survey_comparison_keeps_missing_distinct_from_zero(self):
        page = self.window.survey_page
        page.show_session({"name": "Test", "site_id": "A", "status": "partial", "steps": [
            {"label": "First", "run_id": "1", "status": "complete", "metrics": {"latency_ms": 0}},
            {"label": "Second", "run_id": "2", "status": "failed", "metrics": {}}]}, "unused.json")
        self.assertEqual(page.comparison.item(0, 1).text(), "0")
        self.assertEqual(page.comparison.item(0, 2).text(), "—")


if __name__ == "__main__":
    unittest.main()
