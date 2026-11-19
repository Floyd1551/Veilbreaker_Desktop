import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from veilbreaker.area_coverage import area_preview
from veilbreaker.area_coverage_report import report_html
from veilbreaker.core import AppConfig
from veilbreaker.regional_packs_ui import RegionalPacksDialog, _coverage_job


def result(status='verified', complete=True):
    return dict(bounds=[-97, 32, -96, 34], checked_utc='2026-11-19T12:00:00Z', complete=complete,
                total_intersecting=1, warnings=[], packs=[dict(pack_id='a'*32, name='<Terrain>', kind='terrain',
                source='USGS & test', source_date='2026-10-01', license='Test', sha256='b'*64,
                bounds_wgs84=[-97, 32, -96, 34], coverage_note='Extent only', status=status, detail='Changed')])


class IntegrityPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_report_includes_per_pack_results_and_escapes_reference_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = area_preview([-97, 32, -96, 34], [], [], Path(tmp) / 'refs')
            model['integrity'] = result('failed')
            model['terrain']['sample'] = {'status': 'skipped_integrity', 'note': 'Sampling skipped because terrain integrity failed.'}
            html = report_html(model)
            for value in ('&lt;Terrain&gt;', 'USGS &amp; test', 'failed', 'b'*64, 'Sampling skipped', 'not coverage'):
                self.assertIn(value, html)
            self.assertNotIn('<Terrain>', html)

    def test_integrity_opt_in_and_changed_option_invalidates_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=tmp))
            try:
                self.assertFalse(dialog.coverage_verify.isChecked())
                model = area_preview([-97, 32, -96, 34], [], [], Path(tmp) / 'refs')
                model['integrity'] = result()
                dialog.job_ready({'coverage': model})
                self.assertEqual(dialog.coverage_table.rowCount(), 5)
                dialog.coverage_table.selectRow(4)
                self.assertIn('Terrain', dialog.coverage_details.toPlainText())
                self.assertIn('verified', dialog.coverage_details.toPlainText())
                dialog.coverage_verify.setChecked(True)
                self.assertIsNone(dialog.coverage_result)
                self.assertFalse(dialog.coverage_save.isEnabled())
            finally:
                dialog.close()

    def test_verification_control_fits_field_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=tmp))
            try:
                dialog.resize(760, 650); dialog.workspace_tabs.setCurrentIndex(2)
                dialog.show(); self.app.processEvents()
                self.assertLessEqual(dialog.width(), 760)
                bottom = dialog.coverage_verify.mapTo(dialog, dialog.coverage_verify.rect().bottomRight())
                self.assertLessEqual(bottom.x(), dialog.width())
                self.assertLessEqual(bottom.y(), dialog.height())
            finally:
                dialog.close()

    def test_failed_integrity_skips_sampling_but_preserves_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('veilbreaker.area_pack_integrity.verify_area_packs', return_value=result('failed')) as verify, \
                 patch('veilbreaker.terrain_area_sample.sample_area') as sample, \
                 patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                value = _coverage_job(Path(tmp), Path(tmp) / 'catalog.json', [-97, 32, -96, 34], 11,
                                      lambda: False, lambda _: None, verify_integrity=True)['coverage']
            verify.assert_called_once()
            sample.assert_not_called()
            self.assertEqual(value['integrity']['packs'][0]['status'], 'failed')
            self.assertEqual(value['terrain']['sample']['status'], 'skipped_integrity')

    def test_default_preview_does_not_verify_packs(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('veilbreaker.area_pack_integrity.verify_area_packs') as verify, \
                 patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                value = _coverage_job(Path(tmp), Path(tmp) / 'catalog.json', [-97, 32, -96, 34], None,
                                      lambda: False, lambda _: None)['coverage']
            verify.assert_not_called()
            self.assertNotIn('integrity', value)

    def test_incomplete_integrity_skips_sample_and_failed_structure_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('veilbreaker.area_pack_integrity.verify_area_packs', return_value=result(complete=False)), \
                 patch('veilbreaker.terrain_area_sample.sample_area') as sample, \
                 patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                value = _coverage_job(Path(tmp), Path(tmp) / 'catalog.json', [-97, 32, -96, 34], 11,
                                      lambda: False, lambda _: None, verify_integrity=True)['coverage']
                sample.assert_not_called()
                self.assertEqual(value['terrain']['sample']['status'], 'skipped_integrity')
            structure = result('failed'); structure['packs'][0]['kind'] = 'structures'
            with patch('veilbreaker.area_pack_integrity.verify_area_packs', return_value=structure), \
                 patch('veilbreaker.terrain_area_sample.sample_area', return_value={'status': 'none'}) as sample, \
                 patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                _coverage_job(Path(tmp), Path(tmp) / 'catalog.json', [-97, 32, -96, 34], 11,
                              lambda: False, lambda _: None, verify_integrity=True)
                sample.assert_called_once()

    def test_cancel_after_integrity_never_starts_sampling(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = {'cancelled': False}
            def verify(*args):
                state['cancelled'] = True
                return result('failed')
            with patch('veilbreaker.area_pack_integrity.verify_area_packs', side_effect=verify), \
                 patch('veilbreaker.terrain_area_sample.sample_area') as sample, \
                 patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                with self.assertRaisesRegex(ValueError, 'cancel'):
                    _coverage_job(Path(tmp), Path(tmp) / 'catalog.json', [-97, 32, -96, 34], 11,
                                  lambda: state['cancelled'], lambda _: None, verify_integrity=True)
                sample.assert_not_called()

    def test_real_structure_pack_verification_and_same_size_corruption(self):
        import json
        from veilbreaker.regional_packs import RegionalPackStore
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'structures.geojson'
            source.write_text(json.dumps({'type': 'FeatureCollection', 'features': [{'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [-96.99, 32.99]},
                'properties': {'structure_id': 'fixture'}}]}), encoding='utf-8')
            store = RegionalPackStore(root / 'regional-packs')
            row = store.install_local('structures', source, {'name': 'Real fixture', 'source': 'Registry',
                'source_date': '2026-11-19', 'license': 'Fixture', 'bounds_wgs84': [-97.1, 32.8, -96.8, 33.1]}, lambda: False)
            with patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                preview = _coverage_job(root, root / 'catalog.json', [-97, 32.9, -96.9, 33], None,
                                        lambda: False, lambda _: None, verify_integrity=True)['coverage']
                self.assertEqual(preview['integrity']['packs'][0]['status'], 'verified')
                self.assertIn('Registry', report_html(preview))
                data = store.data_path(row['pack_id'])
                original = data.read_bytes(); data.write_bytes(original.replace(b'fixture', b'Fixture'))
                preview = _coverage_job(root, root / 'catalog.json', [-97, 32.9, -96.9, 33], None,
                                        lambda: False, lambda _: None, verify_integrity=True)['coverage']
                self.assertEqual(preview['integrity']['packs'][0]['status'], 'failed')

    def test_dialog_background_verification_exposes_results_and_saves_report(self):
        import json
        import time
        from veilbreaker.regional_packs import RegionalPackStore
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); config = AppConfig(data_dir=tmp)
            source = root / 'structure.geojson'
            source.write_text(json.dumps({'type': 'FeatureCollection', 'features': [{'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [-96.99, 32.99]},
                'properties': {'structure_id': 'fixture'}}]}), encoding='utf-8')
            RegionalPackStore(config.root / 'regional-packs').install_local('structures', source,
                {'name': 'Field reference', 'source': 'Registry', 'source_date': '2026-11-19',
                 'license': 'Fixture', 'bounds_wgs84': [-97.1, 32.8, -96.8, 33.1]}, lambda: False)
            dialog = RegionalPacksDialog(None, config)
            try:
                dialog.coverage_bounds.setText('-97, 32.9, -96.9, 33')
                dialog.coverage_verify.setChecked(True)
                with patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                    dialog.check_coverage()
                    deadline = time.monotonic() + 10
                    while dialog.worker is not None and time.monotonic() < deadline:
                        self.app.processEvents(); time.sleep(.01)
                self.assertIsNone(dialog.worker)
                self.assertEqual(dialog.coverage_result['integrity']['packs'][0]['status'], 'verified')
                self.assertTrue(dialog.coverage_save.isEnabled())
                target = root / 'preview.html'
                with patch('veilbreaker.regional_packs_ui.QFileDialog.getSaveFileName', return_value=(str(target), 'HTML')):
                    dialog.save_coverage_report()
                self.assertIn('Field reference', target.read_text(encoding='utf-8'))
            finally:
                dialog.close()

    def test_malformed_overflowing_pack_extent_does_not_prevent_integrity_preview(self):
        import json
        from veilbreaker.regional_packs import RegionalPackStore
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'structures.geojson'
            source.write_text(json.dumps({'type': 'FeatureCollection', 'features': [{'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [-96.99, 32.99]},
                'properties': {'structure_id': 'fixture'}}]}), encoding='utf-8')
            store = RegionalPackStore(root / 'regional-packs')
            row = store.install_local('structures', source, {'name': 'Malformed', 'source': 'Registry',
                'source_date': '2026-11-19', 'license': 'Fixture', 'bounds_wgs84': [-97.1, 32.8, -96.8, 33.1]}, lambda: False)
            manifest = store.root / row['pack_id'] / 'manifest.json'
            metadata = json.loads(manifest.read_text(encoding='utf-8'))
            metadata['bounds_wgs84'] = [-(10 ** 400), 32, -96, 34]
            manifest.write_text(json.dumps(metadata), encoding='utf-8')
            with patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                preview = _coverage_job(root, root / 'catalog.json', [-97, 32.9, -96.9, 33], None,
                                        lambda: False, lambda _: None, verify_integrity=True)['coverage']
            self.assertFalse(preview['integrity']['complete'])
            self.assertTrue(any('invalid bounds' in warning for warning in preview['integrity']['warnings']))
            self.assertIn('invalid bounds', report_html(preview))

    def test_damaged_cell_reference_does_not_prevent_independent_pack_verification(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); cells = root / 'cell-references'; folder = cells / ('a' * 32)
            folder.mkdir(parents=True)
            (cells / 'active.json').write_text(json.dumps({'dataset_id': 'a' * 32}), encoding='utf-8')
            (folder / 'manifest.json').write_text(json.dumps({'dataset_id': 'a' * 32}), encoding='utf-8')
            (folder / 'cells.sqlite').write_bytes(b'not a sqlite database')
            with patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                preview = _coverage_job(root, root / 'catalog.json', [-97, 32.9, -96.9, 33], None,
                                        lambda: False, lambda _: None, verify_integrity=True)['coverage']
            self.assertEqual(preview['cell']['status'], 'reference unavailable')
            self.assertIsNone(preview['cell']['count'])
            self.assertIn('integrity', preview)
            self.assertIn('reference unavailable', report_html(preview))

    def test_cancel_area_preview_without_closing_or_losing_inputs(self):
        import threading
        import time
        started = threading.Event()
        def wait_for_cancel(root, catalog, bounds, grid, cancelled, progress, verify_integrity=False):
            started.set()
            while not cancelled(): time.sleep(.005)
            raise ValueError('Area verification cancelled.')
        with tempfile.TemporaryDirectory() as tmp:
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=tmp))
            dialog.show()
            try:
                dialog.coverage_bounds.setText('-97, 32.9, -96.9, 33')
                dialog.coverage_verify.setChecked(True)
                self.assertFalse(dialog.coverage_cancel.isEnabled())
                with patch('veilbreaker.regional_packs_ui._coverage_job', side_effect=wait_for_cancel):
                    dialog.check_coverage()
                    self.assertTrue(started.wait(5))
                    self.assertTrue(dialog.coverage_cancel.isEnabled())
                    dialog.coverage_cancel.click()
                    self.assertFalse(dialog.coverage_cancel.isEnabled())
                    deadline = time.monotonic() + 5
                    while dialog.worker is not None and time.monotonic() < deadline:
                        self.app.processEvents(); time.sleep(.01)
                self.assertIsNone(dialog.worker)
                self.assertTrue(dialog.isVisible())
                self.assertEqual(dialog.coverage_bounds.text(), '-97, 32.9, -96.9, 33')
                self.assertTrue(dialog.coverage_verify.isChecked())
                self.assertIn('cancel', dialog.status.text().lower())
                self.assertFalse(dialog.coverage_cancel.isEnabled())
                self.assertTrue(dialog.coverage_check.isEnabled())
                self.assertIsNone(dialog.coverage_result)
            finally:
                dialog.close()


if __name__ == '__main__': unittest.main()
