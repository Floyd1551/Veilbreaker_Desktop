import json
import os
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
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
                dialog.table.selectRow(0); self.app.processEvents()
                with patch('veilbreaker.mobile_survey_library_ui.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
                    dialog.manage_selected(); self.wait_idle(dialog)
                self.assertEqual(dialog.rows, [])
                dialog.trash_filter.setChecked(True); self.wait_idle(dialog)
                self.assertEqual(len(dialog.rows), 1)
                dialog.table.selectRow(0); self.app.processEvents()
                dialog.manage_selected(); self.wait_idle(dialog)
                self.assertEqual(dialog.rows, [])
                dialog.trash_filter.setChecked(False); self.wait_idle(dialog)
                self.assertEqual(len(dialog.rows), 1)
                source.unlink()
                dialog.table.selectRow(0); self.app.processEvents()
                with patch('veilbreaker.mobile_survey_library_ui.MobileSurveyReviewDialog') as review:
                    review.return_value.exec.return_value = QDialog.DialogCode.Rejected
                    dialog.open_selected(); self.wait_idle(dialog)
                    review.assert_called_once()
                    self.assertEqual(review.call_args.args[2]['survey'], survey)
                dialog.table.selectRow(0); self.app.processEvents()
                with patch('veilbreaker.mobile_survey_library_ui.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
                    dialog.manage_selected(); self.wait_idle(dialog)
                dialog.trash_filter.setChecked(True); self.wait_idle(dialog)
                dialog.table.selectRow(0); self.app.processEvents()
                with patch('veilbreaker.mobile_survey_library_ui.QMessageBox.question', return_value=QMessageBox.StandardButton.No):
                    dialog.delete_selected()
                self.assertEqual(len(dialog.rows), 1)
                with patch('veilbreaker.mobile_survey_library_ui.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
                    dialog.delete_selected(); self.wait_idle(dialog)
                self.assertEqual(dialog.rows, [])
            finally:
                dialog.close(); self.app.processEvents()

    def test_close_does_not_claim_to_cancel_an_active_permanent_delete(self):
        with tempfile.TemporaryDirectory() as folder:
            dialog = MobileSurveyLibraryDialog(None, AppConfig(data_dir=str(Path(folder) / 'workspace')))
            try:
                self.wait_idle(dialog)
                worker = Mock(); dialog.worker = worker; dialog.mode = 'delete'
                dialog.reject()
                self.assertIn('in progress', dialog.status.text())
                worker.cancelled.set.assert_not_called()
                dialog.worker = None
            finally:
                dialog.close(); self.app.processEvents()
