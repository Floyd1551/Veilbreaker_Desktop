import json
import tempfile
import unittest
from pathlib import Path

try:
    import rasterio  # noqa: F401
    from tests.test_terrain_raster import make_dem
except ImportError:
    rasterio = None

from veilbreaker.regional_packs import RegionalPackStore


def structures(path, duplicate=False):
    features = [dict(type='Feature', geometry=dict(type='Point', coordinates=[-96.95, 32.95]),
                     properties=dict(structure_id='ASR-100', owner='Example owner', height_agl_m=35,
                                     carrier='Unverified claim'))]
    if duplicate:
        features.append(features[0])
    path.write_text(json.dumps(dict(type='FeatureCollection', features=features)), encoding='utf-8')


class RegionalPackTests(unittest.TestCase):
    @unittest.skipIf(rasterio is None, 'terrain dependency unavailable')
    def test_terrain_install_coverage_verify_and_remove(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'dem.tif'
            make_dem(source)
            store = RegionalPackStore(root / 'packs')
            metadata = dict(name='Dallas test DEM', source='Synthetic source', license='Test only',
                            source_date='2026-10-27', vertical_datum='NAVD88', units='m')
            row = store.install_local('terrain', source, metadata, lambda: False)
            self.assertEqual(row['kind'], 'terrain')
            self.assertEqual(row['vertical_datum'], 'NAVD88')
            self.assertEqual(row['bounds_wgs84'], [-97.0, 32.99, -96.99, 33.0])
            self.assertEqual(row['coverage_note'], 'Raster bounds; no-data gaps may exist.')
            self.assertEqual(len(store.list_packs()), 1)
            self.assertEqual(store.list_packs()[0]['status'], 'available')
            self.assertTrue(store.verify(row['pack_id']))
            pack_file = store.data_path(row['pack_id'])
            self.assertTrue(pack_file.is_file())
            pack_file.write_bytes(b'changed')
            self.assertFalse(store.verify(row['pack_id']))
            self.assertEqual(store.list_packs()[0]['status'], 'changed-size')
            store.remove(row['pack_id'])
            self.assertEqual(store.list_packs(), [])
            self.assertTrue(source.is_file())

    def test_structures_are_separate_references_with_declared_extent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'towers.geojson'
            structures(source)
            store = RegionalPackStore(root / 'packs')
            meta = dict(name='Dallas structures', source='Operator fixture', license='Test only',
                        source_date='2026-10-27', bounds_wgs84=[-97.1, 32.8, -96.8, 33.1])
            row = store.install_local('structures', source, meta, lambda: False)
            self.assertEqual(row['record_count'], 1)
            self.assertIn('not completeness', row['coverage_note'])
            nearby = store.query_structures(row['pack_id'], [-97, 32.9, -96.9, 33])
            self.assertEqual(nearby[0]['structure_id'], 'ASR-100')
            self.assertNotIn('carrier', nearby[0])
            self.assertEqual(store.query_structures(row['pack_id'], [-95, 32, -94, 33]), [])
            self.assertEqual(store.list_packs()[0]['status'], 'available')

    def test_bad_or_cancelled_install_keeps_existing_pack(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'towers.geojson'
            structures(source)
            store = RegionalPackStore(root / 'packs')
            meta = dict(name='Dallas structures', source='Operator fixture', license='Test only',
                        source_date='2026-10-27', bounds_wgs84=[-97.1, 32.8, -96.8, 33.1])
            original = store.install_local('structures', source, meta, lambda: False)
            structures(source, duplicate=True)
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                store.install_local('structures', source, meta, lambda: False)
            with self.assertRaisesRegex(ValueError, 'cancelled'):
                store.install_local('structures', source, meta, lambda: True)
            self.assertEqual([row['pack_id'] for row in store.list_packs()], [original['pack_id']])
            self.assertEqual(len(list((root / 'packs').glob('.staging-*'))), 0)

    def test_structure_crs_and_overbroad_extent_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'towers.geojson'
            structures(source)
            data = json.loads(source.read_text(encoding='utf-8'))
            data['crs'] = {'type': 'name', 'properties': {'name': 'EPSG:3857'}}
            source.write_text(json.dumps(data), encoding='utf-8')
            store = RegionalPackStore(root / 'packs')
            meta = dict(name='Bad structures', source='Operator fixture', license='Test only',
                        source_date='2026-10-27', bounds_wgs84=[-97.1, 32.8, -96.8, 33.1])
            with self.assertRaisesRegex(ValueError, 'WGS84'):
                store.install_local('structures', source, meta, lambda: False)
            structures(source)
            with self.assertRaisesRegex(ValueError, 'regional'):
                store.install_local('structures', source, dict(meta, bounds_wgs84=[-180, -90, 180, 90]), lambda: False)


if __name__ == '__main__':
    unittest.main()
