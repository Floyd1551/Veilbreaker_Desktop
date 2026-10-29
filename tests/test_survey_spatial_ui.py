import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import copy
from pathlib import Path
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QImage, QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QGraphicsEllipseItem, QGraphicsRectItem, QPushButton
from veilbreaker.core import AppConfig
from veilbreaker.survey import create_survey
from veilbreaker.survey_spatial import import_floor, load_spatial, save_placement
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

    def test_floor_marker_colors_keep_manual_outline_and_missing_values_gray(self):
        image = QImage(200, 100, QImage.Format.Format_RGB32)
        image.fill(QColor('white'))
        canvas = FloorCanvas()
        canvas.set_floor(image, [
            {'x': .2, 'y': .3, 'number': 1, 'scan_label': 'Lobby', 'metric': {'value': -91, 'unit': 'dBm', 'label': 'RSRP', 'color': '#4877ca'}},
            {'x': .8, 'y': .7, 'number': 2, 'scan_label': 'Hall', 'metric': None},
        ], metric_mode=True)
        dots = sorted((item for item in canvas.scene().items() if isinstance(item, QGraphicsEllipseItem)),
                      key=lambda item: item.rect().x())
        self.assertEqual([item.brush().color().name() for item in dots], ['#4877ca', '#65748b'])
        self.assertEqual([item.pen().color().name() for item in dots], ['#ba95f5', '#ba95f5'])
        self.assertIn('saved run metric', dots[0].toolTip().lower())
        self.assertIn('unavailable', dots[1].toolTip().lower())
        self.assertEqual(len([item for item in canvas.scene().items() if isinstance(item, QGraphicsRectItem)]), 2)
        canvas.close()

    def test_clicking_existing_floor_marker_selects_scan_without_moving_it(self):
        image = QImage(200, 100, QImage.Format.Format_RGB32)
        image.fill(QColor('white'))
        canvas = FloorCanvas()
        canvas.resize(600, 400)
        canvas.set_floor(image, [{'run_id': 'saved-run', 'x': .5, 'y': .5,
                                  'number': 1, 'scan_label': 'Room', 'metric': None}])
        canvas.show()
        self.app.processEvents()
        canvas.fit_floor()
        selected, picked = [], []
        canvas.marker_selected.connect(selected.append)
        canvas.picked.connect(lambda x, y: picked.append((x, y)))
        QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton,
                         pos=canvas.mapFromScene(QPointF(100, 50)))
        self.assertEqual(selected, ['saved-run'])
        self.assertEqual(picked, [])
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

    def test_floor_metric_selector_legend_and_selected_scan_details(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = AppConfig(data_dir=folder)
            made = create_survey(cfg, 'Indoor', [{'label': 'Lobby'}, {'label': 'Hall'}, {'label': 'Roof'}])
            path = made['survey_path']
            image = QImage(200, 100, QImage.Format.Format_RGB32)
            image.fill(QColor('white'))
            source = Path(folder) / 'floor.png'
            image.save(str(source))
            f1 = import_floor(cfg, path, source, 'Floor 1')
            f2 = import_floor(cfg, path, source, 'Roof')
            runs = [step['run_id'] for step in made['survey']['steps']]
            for run_id, floor in zip(runs, (f1, f1, f2)):
                save_placement(cfg, path, run_id, {'kind': 'floor', 'floor_id': floor, 'x': .25, 'y': .5})
            session = copy.deepcopy(made['survey'])
            for step, value in zip(session['steps'], (-110, -80, -30)):
                step['metrics'] = {'rsrp': value}
            context = {
                runs[0]: {'rsrp': {'sources': ['cellular_modem'], 'started_utc': '2026-10-28T09:00:00Z', 'duration_s': 1}},
                runs[1]: {'rsrp': {'sources': ['android_import'], 'received_utc': '2026-10-28T09:01:00Z', 'age_ms': 50}},
                runs[2]: {'rsrp': {'sources': ['cellular_modem']}},
            }
            map_model = {'rows': [], 'representatives': [], 'run_context': context}
            with patch('veilbreaker.survey_spatial_ui.read_session', return_value=session), \
                 patch('veilbreaker.map_sources.load_survey_map_data', return_value=map_model):
                dialog = SpatialDialog(None, cfg, path)
            try:
                dialog.metric_selector.setCurrentIndex(dialog.metric_selector.findData('rsrp'))
                dialog.surface.setCurrentIndex(dialog.surface.findData(f1))
                self.assertIn('-110 to -80 dBm', dialog.metric_legend.text())
                self.assertIn('RSRP -110 dBm', dialog.measurement_detail.text())
                self.assertIn(runs[0], dialog.measurement_detail.text())
                self.assertIn('Operator placed', dialog.measurement_detail.text())
                dialog.source_filter.setCurrentIndex(dialog.source_filter.findData('android_import'))
                self.assertIn('single value -80 dBm', dialog.metric_legend.text())
                dialog.point.setCurrentIndex(1)
                self.assertIn('Phone observation received 2026-10-28T09:01:00Z', dialog.measurement_detail.text())
                dialog.source_filter.setCurrentIndex(0)
                dialog.point.setCurrentIndex(0)
                dialog.canvas.scale(1.5, 1.5)
                zoom = dialog.canvas.transform().m11()
                dialog.floor_picked(.4, .6)
                dialog.metric_selector.setCurrentIndex(0)
                self.assertAlmostEqual(dialog.canvas.transform().m11(), zoom)
                self.assertEqual(dialog.pending['x'], .4)
                self.assertIsNotNone(dialog.canvas.preview)
                dialog.metric_selector.setCurrentIndex(dialog.metric_selector.findData('rsrp'))
                dialog.surface.setCurrentIndex(dialog.surface.findData(f2))
                self.assertIn('single value -30 dBm', dialog.metric_legend.text())
                self.assertNotIn('-110', dialog.metric_legend.text())
                dialog.resize(900, 680)
                dialog.show()
                QTest.qWait(30)
                self.assertLessEqual(dialog.height(), 720)
                QTest.mouseClick(dialog.canvas.viewport(), Qt.MouseButton.LeftButton,
                                 pos=dialog.canvas.mapFromScene(QPointF(50, 50)))
                self.assertEqual(dialog.point.currentData(), runs[2])
                self.assertIn('RSRP -30 dBm', dialog.measurement_detail.text())
                close = next(button for button in dialog.findChildren(QPushButton) if button.text() == 'Close')
                self.assertLessEqual(close.mapTo(dialog, close.rect().bottomRight()).y(), dialog.height())
            finally:
                dialog.close()
