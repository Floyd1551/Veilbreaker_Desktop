import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from veilbreaker.fcc_asr import install_fcc_asr
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
