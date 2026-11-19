import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from veilbreaker.area_pack_integrity import verify_area_packs
from veilbreaker.regional_packs import RegionalPackStore
from tests.test_terrain_raster import make_dem, rasterio


@unittest.skipIf(rasterio is None, 'terrain dependencies unavailable')
class AreaPackIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = RegionalPackStore(self.root / 'packs')
        source = self.root / 'dem.tif'
        make_dem(source)
        self.terrain = self.store.install_local('terrain', source, dict(name='Fixture terrain',
            source='Synthetic DEM', source_date='2026-11-19', license='Test terms',
            vertical_datum='NAVD88', units='m'), lambda: False)
        source = self.root / 'structures.json'
        source.write_text(json.dumps(dict(type='FeatureCollection', features=[dict(type='Feature',
            geometry=dict(type='Point', coordinates=[-96.995, 32.995]),
            properties=dict(structure_id='fixture'))])), encoding='utf-8')
        self.structure = self.store.install_local('structures', source, dict(name='Fixture structures',
            source='Fixture registry', source_date='2026-11-18', license='Test terms',
            bounds_wgs84=[-97, 32.99, -96.99, 33]), lambda: False)
        self.area = [-97, 32.99, -96.99, 33]

    def test_verifies_intersecting_terrain_and_structure_with_provenance(self):
        result = verify_area_packs(self.store, self.area, lambda: False)
        self.assertTrue(result['complete'])
        self.assertEqual(result['total_intersecting'], 2)
        self.assertEqual({p['kind'] for p in result['packs']}, {'terrain', 'structures'})
        self.assertEqual({p['status'] for p in result['packs']}, {'verified'})
        for pack in result['packs']:
            self.assertTrue(pack['sha256'])
            self.assertTrue(pack['source_date'])
            self.assertTrue(pack['license'])
        self.assertEqual(verify_area_packs(self.store, [-90, 35, -89, 36], lambda: False)['packs'], [])

    def test_same_size_corruption_and_missing_are_not_verified(self):
        data = self.store.data_path(self.structure['pack_id'])
        original = data.read_bytes()
        altered = original.replace(b'fixture', b'Fixture')
        self.assertEqual(len(original), len(altered))
        data.write_bytes(altered)
        self.store.data_path(self.terrain['pack_id']).unlink()
        result = verify_area_packs(self.store, self.area, lambda: False)
        by_id = {p['pack_id']: p for p in result['packs']}
        self.assertEqual(by_id[self.structure['pack_id']]['status'], 'failed')
        self.assertEqual(by_id[self.terrain['pack_id']]['status'], 'unavailable')
        self.assertTrue(result['complete'])

    def test_cancel_before_or_during_check(self):
        with self.assertRaisesRegex(ValueError, 'cancel'):
            verify_area_packs(self.store, self.area, lambda: True)
        calls = 0
        def cancelled():
            nonlocal calls
            calls += 1
            return calls > 4
        with self.assertRaisesRegex(ValueError, 'cancel'):
            verify_area_packs(self.store, self.area, cancelled)
        with patch.object(self.store, 'verify', side_effect=ValueError('Pack verification cancelled.')):
            with self.assertRaisesRegex(ValueError, 'cancel'):
                verify_area_packs(self.store, self.area, lambda: False)

    def test_limit_and_unknown_manifest_disclose_incomplete_check(self):
        unknown = self.store.root / ('f' * 32)
        unknown.mkdir()
        (unknown / 'manifest.json').write_text('{}', encoding='utf-8')
        with patch('veilbreaker.area_pack_integrity.MAX_MATCHING_PACKS', 1):
            result = verify_area_packs(self.store, self.area, lambda: False)
        self.assertFalse(result['complete'])
        self.assertEqual(result['total_intersecting'], 2)
        self.assertEqual(len(result['packs']), 1)
        self.assertTrue(any('manifest' in w.lower() for w in result['warnings']))
        self.assertTrue(any('limit' in w.lower() for w in result['warnings']))

    def test_file_changed_while_checking_never_reports_verified(self):
        original_verify = self.store.verify
        def mutate(pack_id, cancelled):
            verified = original_verify(pack_id, cancelled)
            if pack_id == self.structure['pack_id']:
                data = self.store.data_path(pack_id)
                data.write_bytes(data.read_bytes().replace(b'fixture', b'Fixture'))
            return verified
        with patch.object(self.store, 'verify', side_effect=mutate):
            result = verify_area_packs(self.store, self.area, lambda: False)
        by_id = {p['pack_id']: p for p in result['packs']}
        self.assertEqual(by_id[self.structure['pack_id']]['status'], 'failed')

    def test_malformed_manifest_bounds_do_not_crash_preview(self):
        manifest = self.store.root / self.structure['pack_id'] / 'manifest.json'
        value = json.loads(manifest.read_text(encoding='utf-8'))
        value['bounds_wgs84'] = [-(10 ** 400), 0, 0, 1]
        manifest.write_text(json.dumps(value), encoding='utf-8')
        result = verify_area_packs(self.store, self.area, lambda: False)
        self.assertFalse(result['complete'])
        self.assertTrue(any('bounds' in warning for warning in result['warnings']))


if __name__ == '__main__':
    unittest.main()
