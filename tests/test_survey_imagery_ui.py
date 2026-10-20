import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from veilbreaker.core import AppConfig
from veilbreaker.survey_imagery_ui import SurveyImageryDialog
from test_survey_imagery import image_bytes, metadata


class DialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_preview_save_and_cancel_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            config = AppConfig(data_dir=folder)
            path = config.root/'surveys'/'survey-ui.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(dict(schema_version=1,survey_id='survey-ui',name='UI',status='planned',steps=[])))
            with patch('veilbreaker.survey_imagery_ui.survey_points',return_value=[]):
                dialog = SurveyImageryDialog(None,config,path)
            self.assertEqual(dialog.default_bounds(),[0,0,0,0])
            dialog.set_preview(image_bytes(),metadata())
            self.assertTrue(dialog.save.isEnabled())
            with patch('veilbreaker.survey_imagery.survey_points',return_value=[]):
                dialog.save_map()
            previous = path.read_bytes()
            with patch('veilbreaker.survey_imagery_ui.survey_points',return_value=[]):
                dialog = SurveyImageryDialog(None,config,path)
            for field, value in zip(dialog.bounds,[-97,32,-96,33]):
                field.setValue(value)
            def fetch(bounds,cancelled):
                while not cancelled():
                    time.sleep(.005)
                raise ValueError('cancelled')
            with patch('veilbreaker.imagery_provider.fetch_naip',side_effect=fetch):
                dialog.show()
                dialog.download()
                dialog.reject()
                self.assertIsNotNone(dialog.worker)
                deadline = time.monotonic()+3
                while dialog.worker is not None and time.monotonic()<deadline:
                    self.app.processEvents()
                    time.sleep(.005)
                self.assertIsNone(dialog.worker)
                self.assertFalse(dialog.isVisible())
            self.assertEqual(path.read_bytes(),previous)
