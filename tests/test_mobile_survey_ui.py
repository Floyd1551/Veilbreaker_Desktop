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
            self.assertEqual(path.read_bytes(), before)
            dialog.close()
