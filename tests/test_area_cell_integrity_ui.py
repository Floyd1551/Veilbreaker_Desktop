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


def verification(status):
    return dict(status=status, dataset_id='a' * 32, expected_sha256='b' * 64,
                actual_sha256='c' * 64, bytes=1024, checked_utc='2026-11-19T12:00:00Z',
                detail='<Check> & detail')


class CellIntegrityPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_default_is_explicitly_not_checked_and_opt_in_invalidates_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=tmp))
            try:
                self.assertFalse(dialog.coverage_verify_cell.isChecked())
                model = area_preview([-97, 32, -96, 34], [], [], Path(tmp) / 'refs')
                dialog.job_ready({'coverage': model})
                dialog.coverage_table.selectRow(2)
                self.assertIn('not checked', dialog.coverage_details.toPlainText().lower())
                self.assertIn('not checked', report_html(model).lower())
                dialog.coverage_verify_cell.setChecked(True)
                self.assertIsNone(dialog.coverage_result)
                self.assertFalse(dialog.coverage_save.isEnabled())
            finally:
                dialog.close()

    def test_separate_verification_exposes_result_and_escapes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('veilbreaker.cell_reference.verify_reference_database', return_value=verification('verified')) as verify, \
                 patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                model = _coverage_job(Path(tmp), Path(tmp) / 'catalog.json', [-97, 32, -96, 34], None,
                                      lambda: False, lambda _: None, verify_cell=True)['coverage']
            verify.assert_called_once()
            self.assertEqual(model['cell_integrity']['status'], 'verified')
            html = report_html(model)
            for expected in ('Cell database integrity', 'verified', '&lt;Check&gt; &amp; detail', 'b' * 64,
                             'c' * 64, 'separate', '2026-11-19T12:00:00Z'):
                self.assertIn(expected, html)
            self.assertNotIn('<Check>', html)

    def test_legacy_or_changed_result_does_not_present_counts_as_verified(self):
        for status in ('legacy_unverified', 'changed', 'missing', 'invalid'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                preview = area_preview([-97, 32, -96, 34], [], [], Path(tmp) / 'refs')
                preview['cell'].update(status='records found', count=12, groups=[dict(radio='LTE', mcc=311, mnc=480, count=12)])
                with patch('veilbreaker.area_coverage.area_preview', return_value=preview), \
                     patch('veilbreaker.cell_reference.verify_reference_database', return_value=verification(status)), \
                     patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                    model = _coverage_job(Path(tmp), Path(tmp) / 'catalog.json', [-97, 32, -96, 34], None,
                                          lambda: False, lambda _: None, verify_cell=True)['coverage']
                self.assertIsNone(model['cell']['count'])
                self.assertEqual(model['cell']['groups'], [])
                self.assertIn('withheld', model['cell']['note'].lower())
                self.assertIn(status, report_html(model))

    def test_withheld_records_are_not_mistaken_for_no_records_in_area(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = area_preview([-97, 32, -96, 34], [], [], Path(tmp) / 'refs')
            model['cell'].update(status='counts withheld', count=None, source='OpenCellID', groups=[])
            model['cell_integrity'] = verification('legacy_unverified')
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=tmp))
            try:
                dialog.job_ready({'coverage': model})
                dialog.coverage_table.selectRow(2)
                details = dialog.coverage_details.toPlainText()
                self.assertIn('Records: withheld / unavailable', details)
                self.assertNotIn('None in area', details)
                self.assertIn('Records: withheld / unavailable', report_html(model))
            finally:
                dialog.close()

    def test_real_reference_count_is_tied_to_stable_verified_database(self):
        from test_cell_reference import HEADER, ROW, META
        from veilbreaker.cell_reference import import_reference, activate_reference
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'cells.csv'
            source.write_text(HEADER + ROW, encoding='utf-8')
            ref = import_reference(root / 'cell-references', source, META, lambda: False, lambda _: None)
            activate_reference(root / 'cell-references', ref['dataset_id'])
            with patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                model = _coverage_job(root, root / 'catalog.json', [-180, -90, 180, 90], None,
                                      lambda: False, lambda _: None, verify_cell=True)['coverage']
            self.assertEqual(model['cell_integrity']['status'], 'verified')
            self.assertEqual(model['cell_integrity']['counts_status'], 'stable')
            self.assertGreater(model['cell']['count'], 0)
            self.assertNotEqual(model['cell']['sha256'], model['cell_integrity']['actual_sha256'])

    def test_changed_database_between_query_and_hash_withholds_count(self):
        from test_cell_reference import HEADER, ROW, META
        from veilbreaker.cell_reference import import_reference, activate_reference
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'cells.csv'
            source.write_text(HEADER + ROW, encoding='utf-8')
            ref = import_reference(root / 'cell-references', source, META, lambda: False, lambda _: None)
            activate_reference(root / 'cell-references', ref['dataset_id'])
            database = root / 'cell-references' / ref['dataset_id'] / 'cells.sqlite'
            def query_then_change(*args):
                result = area_preview(*args)
                with database.open('ab') as stream:
                    stream.write(b'corruption')
                return result
            with patch('veilbreaker.area_coverage.area_preview', side_effect=query_then_change), \
                 patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                model = _coverage_job(root, root / 'catalog.json', [-180, -90, 180, 90], None,
                                      lambda: False, lambda _: None, verify_cell=True)['coverage']
            self.assertEqual(model['cell_integrity']['status'], 'changed')
            self.assertEqual(model['cell_integrity']['counts_status'], 'unverified')
            self.assertIsNone(model['cell']['count'])

    def test_legacy_reference_keeps_unverified_status_and_withholds_counts(self):
        import json
        from test_cell_reference import HEADER, ROW, META
        from veilbreaker.cell_reference import import_reference, activate_reference
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'cells.csv'; source.write_text(HEADER + ROW, encoding='utf-8')
            ref = import_reference(root / 'cell-references', source, META, lambda: False, lambda _: None)
            activate_reference(root / 'cell-references', ref['dataset_id'])
            path = root / 'cell-references' / ref['dataset_id'] / 'manifest.json'
            manifest = json.loads(path.read_text(encoding='utf-8'))
            manifest.pop('database_sha256'); manifest.pop('database_bytes')
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                model = _coverage_job(root, root / 'catalog.json', [-180, -90, 180, 90], None,
                                      lambda: False, lambda _: None, verify_cell=True)['coverage']
            self.assertEqual(model['cell_integrity']['status'], 'legacy_unverified')
            self.assertIsNone(model['cell']['count'])
            self.assertIn('withheld', model['cell']['status'])

    def test_active_reference_switched_during_query_withholds_counts(self):
        from test_cell_reference import HEADER, ROW, META
        from veilbreaker.cell_reference import import_reference, activate_reference
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'cells.csv'; source.write_text(HEADER + ROW, encoding='utf-8')
            cell_root = root / 'cell-references'
            first = import_reference(cell_root, source, META, lambda: False, lambda _: None)
            second = import_reference(cell_root, source, dict(META, date='2026-11-19'), lambda: False, lambda _: None)
            activate_reference(cell_root, first['dataset_id'])
            def query_then_switch(*args):
                result = area_preview(*args)
                activate_reference(cell_root, second['dataset_id'])
                return result
            with patch('veilbreaker.area_coverage.area_preview', side_effect=query_then_switch), \
                 patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                model = _coverage_job(root, root / 'catalog.json', [-180, -90, 180, 90], None,
                                      lambda: False, lambda _: None, verify_cell=True)['coverage']
            self.assertEqual(model['cell_integrity']['status'], 'verified')
            self.assertEqual(model['cell_integrity']['counts_status'], 'unverified')
            self.assertIsNone(model['cell']['count'])

    def test_reference_switched_for_query_then_restored_withholds_counts(self):
        from test_cell_reference import HEADER, ROW, META
        from veilbreaker.cell_reference import import_reference, activate_reference
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'cells.csv'; source.write_text(HEADER + ROW, encoding='utf-8')
            cell_root = root / 'cell-references'
            first = import_reference(cell_root, source, META, lambda: False, lambda _: None)
            second = import_reference(cell_root, source, dict(META, date='2026-11-19'), lambda: False, lambda _: None)
            activate_reference(cell_root, first['dataset_id'])
            def temporarily_switch(*args):
                activate_reference(cell_root, second['dataset_id'])
                result = area_preview(*args)
                activate_reference(cell_root, first['dataset_id'])
                return result
            with patch('veilbreaker.area_coverage.area_preview', side_effect=temporarily_switch), \
                 patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                model = _coverage_job(root, root / 'catalog.json', [-180, -90, 180, 90], None,
                                      lambda: False, lambda _: None, verify_cell=True)['coverage']
            self.assertEqual(model['cell_integrity']['dataset_id'], first['dataset_id'])
            self.assertEqual(model['cell']['dataset_id'], second['dataset_id'])
            self.assertEqual(model['cell_integrity']['counts_status'], 'unverified')
            self.assertIsNone(model['cell']['count'])
            self.assertIn(first['dataset_id'], report_html(model))
            self.assertIn(second['dataset_id'], report_html(model))
            self.assertIn('not applicable', report_html(model).lower())

    def test_cancelled_verification_stops_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('veilbreaker.cell_reference.verify_reference_database', side_effect=ValueError('Verification cancelled')), \
                 patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                with self.assertRaisesRegex(ValueError, 'cancel'):
                    _coverage_job(Path(tmp), Path(tmp) / 'catalog.json', [-97, 32, -96, 34], None,
                                  lambda: False, lambda _: None, verify_cell=True)


if __name__ == '__main__':
    unittest.main()
