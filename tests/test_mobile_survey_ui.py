import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from veilbreaker.mobile_survey_import import load_mobile_survey
from veilbreaker.mobile_survey_ui import MobileSurveyReviewDialog


class MobileSurveyUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_selection_shows_note_without_modifying_source(self):
        capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        survey = {'format': 'veilbreaker.mobile.survey', 'schema_version': 1, 'survey_id': str(uuid.uuid4()),
                  'name': 'Field survey', 'created_utc': capture['created_utc'], 'lifecycle': 'open',
                  'points': [{'attached_utc': capture['created_utc'], 'capture': capture, 'operator_note': 'Metal enclosure'}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'survey.json'
            path.write_text(json.dumps(survey), encoding='utf-8')
            before = path.read_bytes()
            dialog = MobileSurveyReviewDialog(None, str(path), load_mobile_survey(path))
            self.assertFalse(dialog.save.isEnabled())
            dialog.points.selectRow(0)
            self.app.processEvents()
            self.assertTrue(dialog.save.isEnabled())
            self.assertIn('Metal enclosure', dialog.details.toPlainText())
            output = Path(folder) / 'extracted.json'
            with patch('veilbreaker.mobile_survey_ui.QFileDialog.getSaveFileName', return_value=(str(output), 'JSON')):
                dialog.save_capture()
            self.assertEqual(json.loads(output.read_text(encoding='utf-8')), capture)
            self.assertIn('not been imported', dialog.status.text())
            with patch('veilbreaker.mobile_survey_ui.QFileDialog.getExistingDirectory', return_value=folder):
                dialog.export_all()
            bundle = Path(folder) / ('mobile-survey-' + survey['survey_id'])
            self.assertEqual((bundle / 'source-mobile-survey.json').read_bytes(), before)
            self.assertTrue((bundle / 'manifest.json').exists())
            self.assertEqual(path.read_bytes(), before)
            dialog.close()

    def test_save_and_attach_uses_selected_saved_file_without_starting_test(self):
        capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        survey = {'format': 'veilbreaker.mobile.survey', 'schema_version': 1, 'survey_id': str(uuid.uuid4()),
                  'name': 'Field survey', 'created_utc': capture['created_utc'], 'lifecycle': 'open',
                  'points': [{'attached_utc': capture['created_utc'], 'capture': capture}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'survey.json'; path.write_text(json.dumps(survey), encoding='utf-8')
            calls = []
            dialog = MobileSurveyReviewDialog(None, str(path), load_mobile_survey(path), attach_input=lambda name: calls.append(name) or True)
            self.assertFalse(dialog.attach.isEnabled())
            dialog.points.selectRow(0); self.app.processEvents()
            target = Path(folder) / 'input.json'
            with patch('veilbreaker.mobile_survey_ui.QFileDialog.getSaveFileName', return_value=(str(target), 'JSON')):
                dialog.attach_capture()
            self.assertEqual(calls, [str(target)])
            self.assertEqual(json.loads(target.read_text(encoding='utf-8')), capture)
            dialog.close()

    def test_changed_survey_does_not_attach_or_create_capture(self):
        capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        survey = {'format': 'veilbreaker.mobile.survey', 'schema_version': 1, 'survey_id': str(uuid.uuid4()),
                  'name': 'Field survey', 'created_utc': capture['created_utc'], 'lifecycle': 'open',
                  'points': [{'attached_utc': capture['created_utc'], 'capture': capture}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'survey.json'; path.write_text(json.dumps(survey), encoding='utf-8')
            calls = []
            dialog = MobileSurveyReviewDialog(None, str(path), load_mobile_survey(path), attach_input=lambda name: calls.append(name))
            dialog.points.selectRow(0); self.app.processEvents()
            path.write_text(path.read_text() + ' ', encoding='utf-8')
            target = Path(folder) / 'input.json'
            with patch('veilbreaker.mobile_survey_ui.QFileDialog.getSaveFileName', return_value=(str(target), 'JSON')), \
                 patch('veilbreaker.mobile_survey_ui.QMessageBox.warning'):
                dialog.attach_capture()
            self.assertFalse(target.exists()); self.assertEqual(calls, [])
            dialog.close()
