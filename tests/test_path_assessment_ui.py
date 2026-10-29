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
    def test_path_dialog_fits_field_width(self):
        with tempfile.TemporaryDirectory() as tmp:
            context=dict(run_id='synthetic',observation=dict(location=dict(longitude_deg=-86.6,latitude_deg=34.7)),
                         candidate=dict(lon=-86.5,lat=34.8,verification='operator-entered'))
            dialog=PathAssessmentDialog(None,AppConfig(data_dir=tmp),context)
            dialog.resize(900,650)
            dialog.show();self.app.processEvents()
            self.assertLessEqual(dialog.width(),900)
            dialog.close()
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

    def test_incomplete_terrain_displays_partial_profile_without_clearance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'dem.tif';make_dem(path,True)
            context=dict(run_id='synthetic',observation=dict(location=dict(longitude_deg=-96.999,latitude_deg=32.995)),
                         candidate=dict(lon=-96.991,lat=32.995,verification='operator-entered'))
            dialog=PathAssessmentDialog(None,AppConfig(data_dir=tmp),context)
            try:
                dialog.file.setText(str(path));dialog.source.setText('Synthetic');dialog.datum.setText('NAVD88');dialog.units.setCurrentText('m')
                dialog.receiver.setValue(10);dialog.site.setValue(10);dialog.confirm.setChecked(True)
                dialog.run_assessment();deadline=time.monotonic()+10
                while dialog.worker is not None and time.monotonic()<deadline:
                    self.app.processEvents();time.sleep(.01)
                self.assertIsNotNone(dialog.assessment,dialog.status.text())
                self.assertEqual(dialog.assessment['profile']['status'],'incomplete')
                self.assertIsNotNone(dialog.assessment['profile_png'])
                self.assertFalse(dialog.preview.pixmap().isNull())
                self.assertIn('no clearance conclusion',dialog.status.text().lower())
                self.assertTrue(dialog.keep.isEnabled())
            finally:dialog.close()

    def test_all_missing_terrain_does_not_claim_a_graph_is_shown(self):
        from veilbreaker.terrain_profile import assess_profile
        with tempfile.TemporaryDirectory() as tmp:
            context=dict(run_id='synthetic',observation=dict(location=dict(longitude_deg=-96.999,latitude_deg=32.995)),
                         candidate=dict(lon=-96.991,lat=32.995,verification='operator-entered'))
            dialog=PathAssessmentDialog(None,AppConfig(data_dir=tmp),context)
            try:
                dialog.job_ready({'profile':assess_profile([0,10,20],[None,None,None],2,10)})
                self.assertIn('no partial profile',dialog.status.text().lower())
                self.assertNotIn('graph shows',dialog.status.text().lower())
            finally:dialog.close()

    def test_installed_terrain_prefills_path_and_provenance(self):
        from veilbreaker.regional_packs import RegionalPackStore
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'dem.tif'
            make_dem(source)
            config = AppConfig(data_dir=tmp)
            store = RegionalPackStore(config.root / 'regional-packs')
            row = store.install_local('terrain', source,
                                      dict(name='Test terrain', source='Synthetic 3DEP', license='Test only',
                                           source_date='2026-10-27', vertical_datum='NAVD88', units='m'), lambda: False)
            context = dict(run_id='synthetic', observation=dict(location=dict(longitude_deg=-96.999, latitude_deg=32.995)),
                           candidate=dict(lon=-96.991, lat=32.995, verification='operator-entered'))
            dialog = PathAssessmentDialog(None, config, context)
            self.assertEqual(dialog.installed.count(), 1)
            self.assertTrue(dialog.use_installed_terrain())
            self.assertEqual(dialog.file.text(), str(store.data_path(row['pack_id'])))
            self.assertIn('Synthetic 3DEP', dialog.source.text())
            self.assertEqual(dialog.datum.text(), 'NAVD88')
            self.assertEqual(dialog.units.currentText(), 'm')
            self.assertEqual(dialog.expected_pack_sha256, row['sha256'])
            dialog.datum.setText('Different datum')
            dialog.receiver.setValue(10)
            dialog.site.setValue(10)
            dialog.confirm.setChecked(True)
            dialog.run_assessment()
            self.assertIsNone(dialog.worker)
            self.assertIn('reselect', dialog.status.text().lower())
            dialog.close()

    def test_installed_coverage_selects_adjacent_tiles_and_assesses_path(self):
        from veilbreaker.regional_packs import RegionalPackStore
        from tests.test_terrain_tiles import tile
        with tempfile.TemporaryDirectory() as tmp:
            config = AppConfig(data_dir=tmp)
            store = RegionalPackStore(config.root / 'regional-packs')
            for west, name, elevation in [(-97.0, 'West', 100), (-96.99, 'East', 110)]:
                source = Path(tmp) / (name + '.tif')
                tile(source, west, elevation)
                store.install_local('terrain', source,
                                    dict(name=name, source='Synthetic', license='Test only',
                                         source_date='2026-10-27', vertical_datum='NAVD88', units='m'), lambda: False)
            context = dict(run_id='synthetic', observation=dict(location=dict(longitude_deg=-96.999, latitude_deg=32.995)),
                           candidate=dict(lon=-96.981, lat=32.995, verification='operator-entered'))
            dialog = PathAssessmentDialog(None, config, context)
            self.assertTrue(dialog.use_installed_coverage())
            self.assertEqual(len(dialog.selected_packs), 2)
            dialog.receiver.setValue(10)
            dialog.site.setValue(10)
            dialog.confirm.setChecked(True)
            dialog.run_assessment()
            deadline = time.monotonic() + 10
            while dialog.worker is not None and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.01)
            self.assertIsNone(dialog.worker)
            self.assertIsNotNone(dialog.assessment, dialog.status.text())
            self.assertEqual(len(dialog.assessment['regional_packs']), 2)
            self.assertNotIn(None, dialog.assessment['terrain']['elevations_m'])
            from veilbreaker.path_assessment_report import assessment_html
            report = assessment_html(dialog.assessment)
            self.assertIn('West', report)
            self.assertIn('East', report)
            self.assertIn('Sample count', report)
            dialog.close()
