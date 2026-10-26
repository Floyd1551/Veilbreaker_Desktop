import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QColor
from veilbreaker.core import AppConfig
from veilbreaker.survey import create_survey, export_session
from veilbreaker.survey_spatial import load_spatial, import_floor, save_placement, clear_placement, calibrate_floor, read_floor, remove_floor


class SpatialTests(unittest.TestCase):
    def test_unplaced_counts_evidence_not_planned_points(self):
        from veilbreaker.survey_spatial import unplaced_measurements
        steps = [dict(run_id='planned'), *[dict(run_id=r, evidence_zip=r + '.zip') for r in ('gps', 'manual', 'missing')]]
        self.assertEqual(unplaced_measurements(steps, {'placements': {'manual': {}}}, {'gps'}), ['missing'])

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cfg = AppConfig(data_dir=self.temp.name)
        made = create_survey(self.cfg, 'Indoor survey', [{'label': 'Lobby'}])
        self.path = Path(made['survey_path'])
        self.run = made['survey']['steps'][0]['run_id']
        self.original = self.path.read_bytes()
        self.image = Path(self.temp.name) / 'plan.png'
        image = QImage(200, 100, QImage.Format.Format_RGB32)
        image.fill(QColor('white'))
        image.save(str(self.image))

    def tearDown(self):
        self.temp.cleanup()

    def test_persist_export_and_original_journal_unchanged(self):
        floor = import_floor(self.cfg, self.path, self.image, 'Ground floor')
        save_placement(self.cfg, self.path, self.run, dict(kind='floor', floor_id=floor, x=.25, y=.5))
        calibrate_floor(self.cfg, self.path, floor, [0, 0], [1, 0], 20)
        data = load_spatial(self.cfg, self.path)
        self.assertEqual(data['placements'][self.run]['source'], 'operator')
        self.assertEqual(data['floors'][floor]['calibration']['meters_per_pixel'], .1)
        self.assertEqual(self.path.read_bytes(), self.original)
        self.image.unlink()
        self.assertEqual(read_floor(self.cfg, self.path, floor).width(), 200)
        bundle = export_session(self.cfg, self.path)
        with zipfile.ZipFile(bundle) as archive:
            exported = json.loads(archive.read('spatial.json'))
            self.assertEqual(exported['placements'][self.run]['x'], .25)
            self.assertIn(floor + '.png', archive.namelist())
            self.assertNotIn(self.temp.name, archive.read('spatial.json').decode())
        clear_placement(self.cfg, self.path, self.run)
        self.assertNotIn(self.run, load_spatial(self.cfg, self.path)['placements'])

    def test_invalid_placements_and_closed_survey(self):
        floor = import_floor(self.cfg, self.path, self.image, 'Floor')
        for x in (-.01, 1.01, True, float('inf')):
            with self.assertRaises(ValueError):
                save_placement(self.cfg, self.path, self.run, dict(kind='floor', floor_id=floor, x=x, y=.5))
        for first, second, meters in [([0,0], [0,0], 1), ([0,0], [1,0], 0), ([0,0], [2,0], 1)]:
            with self.assertRaises(ValueError):
                calibrate_floor(self.cfg, self.path, floor, first, second, meters)
        for value in [dict(kind='geographic', latitude=91, longitude=0),
                      dict(kind='geographic', latitude=float('nan'), longitude=0),
                      dict(kind='floor', floor_id='../bad', x=0, y=0)]:
            with self.assertRaises(ValueError):
                save_placement(self.cfg, self.path, self.run, value)
        with self.assertRaises(ValueError):
            save_placement(self.cfg, self.path, 'missing', dict(kind='geographic', latitude=1, longitude=2))
        raw = json.loads(self.path.read_text())
        raw['lifecycle'] = 'completed'
        self.path.write_text(json.dumps(raw))
        with self.assertRaises(ValueError):
            save_placement(self.cfg, self.path, self.run, dict(kind='geographic', latitude=1, longitude=2))

    def test_manual_map_pin_does_not_become_qualified_gps(self):
        from veilbreaker.map_sources import load_survey_map_data
        save_placement(self.cfg, self.path, self.run, dict(kind='geographic', latitude=40, longitude=-90))
        model = load_survey_map_data(self.cfg, self.path)
        manual = [f for f in model['features']['features'] if f['properties'].get('manual')]
        self.assertEqual(len(manual), 1)
        self.assertFalse(manual[0]['properties']['quality']['qualified'])
        self.assertEqual(model['representatives'], [])
        from veilbreaker.map_ui import MapWindow
        window = MapWindow(None, model, lambda _: None, enable_web=False, restore_pack=False)
        self.assertEqual(len(window.visible_features()), 1)
        self.assertTrue(window.visible_features()[0]['properties']['manual'])
        window.close()

    def test_floor_removal_integrity_and_trash_protection(self):
        from veilbreaker.library import trash_survey, restore_entry
        floor = import_floor(self.cfg, self.path, self.image, 'Upper')
        save_placement(self.cfg, self.path, self.run, dict(kind='floor', floor_id=floor, x=1, y=0))
        with self.assertRaises(ValueError):
            remove_floor(self.cfg, self.path, floor)
        entry = trash_survey(self.cfg, self.path)
        with self.assertRaises(ValueError):
            clear_placement(self.cfg, self.path, self.run)
        restore_entry(self.cfg, entry)
        self.assertEqual(load_spatial(self.cfg, self.path)['placements'][self.run]['x'], 1)
        asset = self.path.parent / 'spatial' / self.path.stem / (floor + '.png')
        saved = asset.read_bytes()
        asset.write_bytes(b'invalid')
        with self.assertRaises(ValueError):
            read_floor(self.cfg, self.path, floor)
        asset.write_bytes(saved)
        clear_placement(self.cfg, self.path, self.run)
        remove_floor(self.cfg, self.path, floor)
        self.assertNotIn(floor, load_spatial(self.cfg, self.path)['floors'])
