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

    def test_settings_reject_invalid_json(self):
        self.window.config_editor.setPlainText("{")
        self.window.save_settings()
        self.assertIn("not saved", self.errors[0])


if __name__ == "__main__":
    unittest.main()
