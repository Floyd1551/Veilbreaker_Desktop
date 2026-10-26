import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QImage, QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
from veilbreaker.core import AppConfig
from veilbreaker.survey import create_survey
from veilbreaker.survey_spatial import import_floor, load_spatial
from veilbreaker.survey_spatial_ui import SpatialDialog, FloorCanvas


class SpatialUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_floor_click_conversion_after_zoom(self):
        image = QImage(200, 100, QImage.Format.Format_RGB32)
        image.fill(QColor('white'))
        canvas = FloorCanvas()
        canvas.resize(600, 400)
        canvas.set_floor(image, [])
        canvas.show()
        self.app.processEvents()
        canvas.fit_floor()
        points = []
        canvas.picked.connect(lambda x, y: points.append((x, y)))
        for scale in (1, 1.5):
            canvas.scale(scale, scale)
            pos = canvas.mapFromScene(QPointF(100, 50))
            QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=pos)
            self.assertAlmostEqual(points[-1][0], .5, delta=.01)
            self.assertAlmostEqual(points[-1][1], .5, delta=.01)
        canvas.close()

    def test_save_and_clear_floor_placement(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = AppConfig(data_dir=folder)
            made = create_survey(cfg, 'Test', [{'label': 'Room'}])
            path = made['survey_path']
            image = QImage(200, 100, QImage.Format.Format_RGB32)
            image.fill(QColor('white'))
            source = Path(folder) / 'floor.png'
            image.save(str(source))
            floor = import_floor(cfg, path, source, 'Level 1')
            dialog = SpatialDialog(None, cfg, path)
            with patch('veilbreaker.map_sources.load_survey_map_data', return_value={
                    'representatives': ['p0'], 'rows': [{'id': 'p0', 'run_id': 'gps-run', 'renderable': True}]}):
                dialog.refresh()
            self.assertIn('Unplaced measurements: 0', dialog.placement_summary.text())
            dialog.surface.setCurrentIndex(dialog.surface.findData(floor))
            dialog.floor_picked(.2, .8)
            dialog.save()
            run = made['survey']['steps'][0]['run_id']
            self.assertEqual(load_spatial(cfg, path)['placements'][run]['x'], .2)
            with patch('veilbreaker.survey_spatial_ui.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
                dialog.clear()
            self.assertNotIn(run, load_spatial(cfg, path)['placements'])
            dialog.close()
