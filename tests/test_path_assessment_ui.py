import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import time
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from veilbreaker.core import AppConfig
from veilbreaker.path_assessment_ui import PathAssessmentDialog
from test_terrain_raster import make_dem

class PathUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_calculate_and_changed_input_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'dem.tif';make_dem(path)
            context=dict(run_id='synthetic',observation=dict(location=dict(longitude_deg=-96.999,latitude_deg=32.995)),candidate=dict(lon=-96.991,lat=32.995,verification='operator-entered'))
            dialog=PathAssessmentDialog(None,AppConfig(data_dir=tmp),context)
            dialog.file.setText(str(path));dialog.source.setText('Synthetic');dialog.datum.setText('NAVD88');dialog.units.setCurrentText('m')
            dialog.receiver.setValue(10);dialog.site.setValue(10);dialog.confirm.setChecked(True)
            dialog.run_assessment()
            deadline=time.monotonic()+10
            while dialog.worker is not None and time.monotonic()<deadline:
                self.app.processEvents();time.sleep(.01)
            self.assertIsNone(dialog.worker)
            self.assertIsNotNone(dialog.assessment,dialog.status.text())
            self.assertTrue(dialog.keep.isEnabled())
            dialog.site.setValue(20)
            self.assertIsNone(dialog.assessment)
            self.assertFalse(dialog.keep.isEnabled())
            dialog.close()
