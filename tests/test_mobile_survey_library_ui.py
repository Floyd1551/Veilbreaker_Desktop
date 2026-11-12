import json
import os
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog
from veilbreaker.core import AppConfig
from veilbreaker.mobile_survey_library_ui import MobileSurveyLibraryDialog


class MobileSurveyLibraryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def wait_idle(self, dialog):
        deadline = time.monotonic() + 10
        while dialog.worker is not None and time.monotonic() < deadline:
            QTest.qWait(20)
        self.assertIsNone(dialog.worker)

    def test_import_and_reopen_from_local_copy(self):
        capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        survey = {'format': 'veilbreaker.mobile.survey', 'schema_version': 1, 'survey_id': str(uuid.uuid4()),
                  'name': 'Site', 'created_utc': capture['created_utc'], 'lifecycle': 'open',
                  'points': [{'attached_utc': capture['created_utc'], 'capture': capture}]}
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'mobile.json'; source.write_text(json.dumps(survey), encoding='utf-8')
            dialog = MobileSurveyLibraryDialog(None, AppConfig(data_dir=str(Path(folder) / 'workspace')))
            try:
                self.wait_idle(dialog)
                with patch('veilbreaker.mobile_survey_library_ui.QFileDialog.getOpenFileName', return_value=(str(source), 'JSON')):
                    dialog.import_file(); self.wait_idle(dialog)
                self.assertEqual(len(dialog.rows), 1)
                with patch('veilbreaker.mobile_survey_library_ui.QFileDialog.getOpenFileName', return_value=(str(source), 'JSON')):
                    dialog.import_file(); self.wait_idle(dialog)
                self.assertEqual(len(dialog.rows), 1)
                self.assertIn('already saved', dialog.status.text())
                source.unlink()
                dialog.table.selectRow(0); self.app.processEvents()
                with patch('veilbreaker.mobile_survey_library_ui.MobileSurveyReviewDialog') as review:
                    review.return_value.exec.return_value = QDialog.DialogCode.Rejected
                    dialog.open_selected(); self.wait_idle(dialog)
                    review.assert_called_once()
                    self.assertEqual(review.call_args.args[2]['survey'], survey)
            finally:
                dialog.close(); self.app.processEvents()
