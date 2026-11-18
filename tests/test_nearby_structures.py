import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from veilbreaker.nearby_structures import nearby_structures
from veilbreaker.regional_packs import RegionalPackStore


class NearbyStructureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = RegionalPackStore(self.root / 'packs')

    def install(self, name, rows, bounds=None):
        features = [dict(type='Feature', geometry=dict(type='Point', coordinates=[lon, lat]),
                         properties=dict(structure_id=ident, height_agl_m=height, carrier='unverified'))
                    for ident, lon, lat, height in rows]
        source = self.root / (name + '.geojson')
        source.write_text(json.dumps(dict(type='FeatureCollection', features=features)), encoding='utf-8')
        return self.store.install_local('structures', source, dict(name=name, source='Example registry',
            license='Example license', source_date='2026-11-01', bounds_wgs84=bounds or [-87, 34, -86, 35]), lambda: False)

    def test_nearest_across_packs_with_source_provenance_and_no_cell_claim(self):
        a = self.install('a', [('far', -86.8, 34.7, 31), ('near', -86.501, 34.7, 40)])
        b = self.install('b', [('middle', -86.52, 34.7, None)])
        result = nearby_structures(self.store, 34.7, -86.5, radius_km=50, limit=2)
        self.assertEqual([r['structure_id'] for r in result['candidates']], ['near', 'middle'])
        self.assertEqual(result['total_matches'], 3)
        self.assertTrue(result['truncated'])
        candidate = result['candidates'][0]
        self.assertEqual(candidate['pack_id'], a['pack_id'])
        self.assertEqual(candidate['source'], 'Example registry')
        self.assertEqual(candidate['source_date'], '2026-11-01')
        self.assertEqual(candidate['sha256'], a['sha256'])
        self.assertEqual(candidate['reference_kind'], 'physical structure')
        self.assertNotIn('carrier', candidate)
        self.assertNotIn('cell_id', candidate)
        self.assertLess(candidate['distance_m'], 100)
        self.assertEqual({r['pack_id'] for r in result['packs']}, {a['pack_id'], b['pack_id']})

    def test_changed_pack_is_excluded_and_warning_is_shown(self):
        row = self.install('bad', [('point', -86.5, 34.7, 25)])
        path = self.store.data_path(row['pack_id'])
        raw = path.read_bytes()
        path.write_bytes(raw.replace(b'point', b'other'))
        self.assertEqual(len(path.read_bytes()), len(raw))
        result = nearby_structures(self.store, 34.7, -86.5)
        self.assertEqual(result['candidates'], [])
        self.assertTrue(result['warnings'])
        self.assertTrue(result['search_incomplete'])

    def test_declared_coverage_distinguishes_partial_and_absent_search_area(self):
        self.install('small', [('point', -86.5, 34.7, 25)], [-86.51, 34.69, -86.49, 34.71])
        result = nearby_structures(self.store, 34.7, -86.5, radius_km=10)
        self.assertEqual(result['declared_coverage'], 'partial')
        self.assertTrue(result['search_incomplete'])
        self.assertTrue(any('bounding area' in warning for warning in result['warnings']))
        empty = nearby_structures(self.store, 40, -100, radius_km=10)
        self.assertEqual(empty['declared_coverage'], 'none')
        self.assertTrue(empty['search_incomplete'])

    def test_multiple_pack_extents_can_cover_bounding_area(self):
        self.install('left', [('left', -86.55, 34.7, 25)], [-87, 34, -86.5, 35])
        self.install('right', [('right', -86.45, 34.7, 25)], [-86.5, 34, -86, 35])
        result = nearby_structures(self.store, 34.7, -86.5, radius_km=10)
        self.assertEqual(result['declared_coverage'], 'full')
        self.assertFalse(result['search_incomplete'])

    def test_dateline_search_includes_both_sides_without_inventing_a_match(self):
        self.install('east', [('e', 179.95, 10, 30)], [179, 9, 180, 11])
        self.install('west', [('w', -179.95, 10, 30)], [-180, 9, -179, 11])
        result = nearby_structures(self.store, 10, 179.99, radius_km=20)
        self.assertEqual({c['structure_id'] for c in result['candidates']}, {'e', 'w'})
        self.assertFalse(result['search_incomplete'])
        self.assertIn('does not establish a serving cell', result['warnings'][0])

    def test_search_limit_discloses_that_nearer_results_may_be_missing(self):
        self.install('a', [('a1', -86.52, 34.7, 10), ('a2', -86.51, 34.7, 10)])
        self.install('b', [('b1', -86.501, 34.7, 10)])
        with patch('veilbreaker.nearby_structures.MAX_FEATURES', 2):
            result = nearby_structures(self.store, 34.7, -86.5, radius_km=50)
        self.assertTrue(result['search_incomplete'])
        self.assertTrue(any('may omit closer' in warning for warning in result['warnings']))

    def test_fcc_position_datum_and_registration_survive_as_reference_provenance(self):
        from tests.test_fcc_asr import archive, ra, co
        from veilbreaker.fcc_asr import install_fcc_asr
        source = archive(self.root, [ra()], [co()])
        pack = install_fcc_asr(self.store, source, [-87.2, 34.3, -86.2, 35.2],
                               '2026-10-25', 'FCC test', lambda: False)['installed']
        result = nearby_structures(self.store, 34.73, -86.59, radius_km=10)
        candidate = result['candidates'][0]
        self.assertEqual(candidate['pack_id'], pack['pack_id'])
        self.assertEqual(candidate['registration_number'], '1234567')
        self.assertIn('NAD83', candidate['position_source'])
        self.assertEqual(candidate['registration_status'], 'Constructed')
        self.assertNotIn('carrier', candidate)

    def test_invalid_parameters_and_cancellation_fail_safely(self):
        for lat, lon, radius, limit in [(float('nan'), 0, 10, 5), (0, 181, 10, 5),
                                       (0, 0, 0, 5), (0, 0, 101, 5), (0, 0, 10, 0),
                                       (True, 0, 10, 5), (10 ** 400, 0, 10, 5)]:
            with self.subTest(lat=lat, lon=lon, radius=radius, limit=limit), self.assertRaises(ValueError):
                nearby_structures(self.store, lat, lon, radius_km=radius, limit=limit)
        with self.assertRaisesRegex(ValueError, 'cancel'):
            nearby_structures(self.store, 34.7, -86.5, cancelled=lambda: True)

    def test_out_of_range_manifest_bounds_do_not_crash_search(self):
        row = self.install('invalid_bounds', [('point', -86.5, 34.7, 25)])
        manifest_path = self.store.root / row['pack_id'] / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['bounds_wgs84'][0] = 10 ** 400
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        result = nearby_structures(self.store, 34.7, -86.5)
        self.assertTrue(result['search_incomplete'])
        self.assertEqual(result['candidates'], [])


if __name__ == '__main__':
    unittest.main()
