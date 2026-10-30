import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from veilbreaker.fcc_asr import install_fcc_asr, install_conus_fcc_asr
from veilbreaker.regional_packs import RegionalPackStore

BOUNDS = [-87.2, 34.3, -86.2, 35.2]


def ra(registration='1234567', status='C', dismantled='', height='90.5'):
    fields = [''] * 46
    fields[0], fields[1], fields[3], fields[8], fields[13], fields[30] = 'RA', 'REG', registration, status, dismantled, height
    return '|'.join(fields)


def co(registration='1234567', kind='T', latitude=('34', '43', '48', 'N'), longitude=('86', '35', '24', 'W')):
    fields = [''] * 18
    fields[0], fields[1], fields[3], fields[5] = 'CO', 'REG', registration, kind
    fields[6:10], fields[11:15] = latitude, longitude
    fields[10], fields[15] = '125028.0', '311724.0'  # FCC total-seconds fields, not DMS degrees
    return '|'.join(fields)


def archive(root, rows, coordinates):
    path = root / 'r_tower.zip'
    with zipfile.ZipFile(path, 'w') as out:
        out.writestr('RA.dat', '\n'.join(rows) + '\n')
        out.writestr('CO.dat', '\n'.join(coordinates) + '\n')
    return path


class FccAsrTests(unittest.TestCase):
    def test_conus_import_tiles_and_resumes_with_verified_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = archive(root, [ra(), ra('2345678'), ra('3456789', 'G')],
                             [co(), co('2345678', latitude=('40','42','46','N'), longitude=('74','0','21','W')),
                              co('3456789', latitude=('40','42','46','N'), longitude=('74','0','21','W'))])
            store = RegionalPackStore(root / 'packs')
            first = install_conus_fcc_asr(store, source, '2026-10-25', lambda: False)
            self.assertEqual(first['record_count'], 2)
            self.assertEqual(len(first['installed']), 2)
            self.assertEqual(first['skipped'], 0)
            for pack in first['installed']:
                self.assertTrue(store.verify(pack['pack_id']))
                self.assertIn(first['archive_sha256'], pack['source'])
                self.assertLessEqual(pack['bounds_wgs84'][2]-pack['bounds_wgs84'][0], 5)
            again = install_conus_fcc_asr(store, source, '2026-10-25', lambda: False)
            self.assertEqual(len(again['installed']), 0)
            self.assertEqual(again['skipped'], 2)
            self.assertEqual(len(store.list_packs()), 2)

    def test_conus_tile_edges_have_one_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = archive(root, [ra()], [co(latitude=('35','0','0','N'),longitude=('90','0','0','W'))])
            store = RegionalPackStore(root/'packs')
            result = install_conus_fcc_asr(store, source, '2026-10-25', lambda: False)
            self.assertEqual(result['record_count'], 1)
            self.assertEqual(len(result['installed']), 1)

    def test_conus_interruption_retains_completed_pack_and_retry_repairs_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=archive(root,[ra(),ra('2345678')],[co(),co('2345678',latitude=('40','42','46','N'),longitude=('74','0','21','W'))])
            store=RegionalPackStore(root/'packs'); stopping=[False]
            original=store.install_local
            def install(*args, **kwargs):
                result=original(*args, **kwargs); stopping[0]=True; return result
            store.install_local=install
            with self.assertRaisesRegex(ValueError,'cancel'):
                install_conus_fcc_asr(store,source,'2026-10-25',lambda:stopping[0])
            self.assertEqual(len(store.list_packs()),1)
            store.install_local=original
            result=install_conus_fcc_asr(store,source,'2026-10-25',lambda:False)
            self.assertEqual((len(result['installed']),result['skipped']),(1,1))
            victim=store.data_path(result['packs'][0]['pack_id'])
            data=victim.read_bytes(); victim.write_bytes(data.replace(b'FCC',b'XXX',1))
            result=install_conus_fcc_asr(store,source,'2026-10-25',lambda:False)
            self.assertEqual((len(result['installed']),result['skipped']),(1,1))

    def test_conus_bad_archive_does_not_install_any_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=archive(root, ['RA|bad'], [co()]); store=RegionalPackStore(root/'packs')
            with self.assertRaisesRegex(ValueError, 'schema'):
                install_conus_fcc_asr(store,source,'2026-10-25',lambda:False)
            self.assertEqual(store.list_packs(), [])

    def test_import_dialog_offers_conus_without_regional_bounds(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        from veilbreaker.fcc_asr_ui import FccAsrImportDialog
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            dialog = FccAsrImportDialog(None, Path(directory))
            try:
                dialog.mode.setCurrentIndex(1)
                self.assertFalse(dialog.bounds.isEnabled())
                self.assertIn('CONUS', dialog.install.text())
                dialog.mode.setCurrentIndex(0)
                self.assertTrue(dialog.bounds.isEnabled())
            finally: dialog.close()

    def test_region_install_uses_constructed_tower_records_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = archive(root, [ra(), ra('2345678', 'G'), ra('3456789', 'C', '01/01/2024')],
                             [co(), co('2345678'), co('3456789'), co('9876543', 'A')])
            store = RegionalPackStore(root / 'packs')
            result = install_fcc_asr(store, source, BOUNDS, '2026-10-25', 'Huntsville ASR', lambda: False)
            pack = result['installed']
            data = json.loads(store.data_path(pack['pack_id']).read_text(encoding='utf-8'))
            self.assertEqual(pack['record_count'], 1)
            self.assertEqual(pack['source_date'], '2026-10-25')
            self.assertIn(result['archive_sha256'], pack['source'])
            point = data['features'][0]
            lon, lat = point['geometry']['coordinates']
            self.assertAlmostEqual(lon, -86.59)
            self.assertAlmostEqual(lat, 34.73)
            self.assertEqual(point['properties']['structure_id'], 'FCC ASR 1234567')
            self.assertEqual(point['properties']['height_agl_m'], 90.5)
            self.assertNotIn('carrier', point['properties'])
            self.assertTrue(store.verify(pack['pack_id']))

    def test_rejects_duplicate_coordinates_instead_of_guessing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = archive(root, [ra()], [co(), co(longitude=('86', '36', '00', 'W'))])
            with self.assertRaisesRegex(ValueError, 'multiple tower coordinates'):
                install_fcc_asr(RegionalPackStore(root / 'packs'), source, BOUNDS, '2026-10-25', 'Test', lambda: False)

    def test_bad_schema_and_cancel_leave_no_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = archive(root, ['RA|bad'], ['CO|bad'])
            store = RegionalPackStore(root / 'packs')
            with self.assertRaisesRegex(ValueError, 'schema'):
                install_fcc_asr(store, source, BOUNDS, '2026-10-25', 'Test', lambda: False)
            with self.assertRaisesRegex(ValueError, 'cancel'):
                install_fcc_asr(store, source, BOUNDS, '2026-10-25', 'Test', lambda: True)
            self.assertEqual(store.list_packs(), [])

    def test_invalid_positions_and_wrong_date_do_not_create_a_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = archive(root, [ra()], [co(latitude=('34', '61', '0', 'N'))])
            store = RegionalPackStore(root / 'packs')
            with self.assertRaisesRegex(ValueError, 'date'):
                install_fcc_asr(store, source, BOUNDS, 'yesterday', 'Test', lambda: False)
            with self.assertRaisesRegex(ValueError, 'No constructed'):
                install_fcc_asr(store, source, BOUNDS, '2026-10-25', 'Test', lambda: False)
            self.assertEqual(store.list_packs(), [])

    def test_rejects_application_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = archive(root, [ra().replace('RA|REG|', 'RA|APP|', 1)], [co()])
            store = RegionalPackStore(root / 'packs')
            with self.assertRaisesRegex(ValueError, 'registration'):
                install_fcc_asr(store, source, BOUNDS, '2026-10-25', 'Test', lambda: False)
            self.assertEqual(store.list_packs(), [])


if __name__ == '__main__':
    unittest.main()
