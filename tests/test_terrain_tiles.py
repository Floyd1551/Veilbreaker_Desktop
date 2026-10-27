import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
except ImportError:
    rasterio = None

from veilbreaker.terrain_raster import sample_path_tiles


META = {'source': 'Synthetic tile', 'vertical_datum': 'NAVD88', 'units': 'm'}


def tile(path, west, height):
    with rasterio.open(path, 'w', driver='GTiff', width=100, height=100, count=1,
                       dtype='float32', crs='EPSG:4326',
                       transform=from_origin(west, 33, .0001, .0001), nodata=-9999) as dataset:
        dataset.write(np.full((100, 100), height, dtype='float32'), 1)


@unittest.skipIf(rasterio is None, 'terrain dependency unavailable')
class TerrainTileTests(unittest.TestCase):
    def test_adjacent_tiles_fill_one_path_and_retain_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / 'a.tif', Path(folder) / 'b.tif'
            tile(first, -97.0, 100)
            tile(second, -96.99, 110)
            rows = [{'path': first, 'metadata': META, 'pack_id': 'a'},
                    {'path': second, 'metadata': META, 'pack_id': 'b'}]
            result = sample_path_tiles(rows, [-96.999, 32.995], [-96.981, 32.995], lambda: False)
            self.assertEqual(len(result['tiles']), 2)
            self.assertEqual({100, 110}, set(result['elevations_m']))
            self.assertNotIn(None, result['elevations_m'])
            self.assertEqual(sum(row['sample_count'] for row in result['tiles']), len(result['elevations_m']))
            self.assertEqual({row['pack_id'] for row in result['tiles']}, {'a', 'b'})

    def test_gap_remains_missing_and_datum_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / 'a.tif', Path(folder) / 'b.tif'
            tile(first, -97.0, 100)
            tile(second, -96.985, 110)
            rows = [{'path': first, 'metadata': META, 'pack_id': 'a'},
                    {'path': second, 'metadata': META, 'pack_id': 'b'}]
            result = sample_path_tiles(rows, [-96.999, 32.995], [-96.976, 32.995], lambda: False)
            self.assertIn(None, result['elevations_m'])
            self.assertGreater(result['missing_samples'], 0)
            rows[1]['metadata'] = dict(META, vertical_datum='Other datum')
            with self.assertRaisesRegex(ValueError, 'vertical datum'):
                sample_path_tiles(rows, [-96.999, 32.995], [-96.976, 32.995], lambda: False)

    def test_installed_checksum_must_match(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'a.tif'
            tile(source, -97.0, 100)
            with self.assertRaisesRegex(ValueError, 'checksum changed'):
                sample_path_tiles([{'path': source, 'metadata': META, 'pack_id': 'a',
                                    'sha256': '0' * 64}],
                                  [-96.999, 32.995], [-96.991, 32.995], lambda: False)


if __name__ == '__main__':
    unittest.main()
