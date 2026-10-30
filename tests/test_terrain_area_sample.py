import tempfile
import unittest
from pathlib import Path

from veilbreaker.regional_packs import RegionalPackStore
from veilbreaker.terrain_area_sample import sample_area
from tests.test_terrain_raster import make_dem, rasterio


@unittest.skipIf(rasterio is None, 'terrain dependencies unavailable')
class TerrainAreaSampleTests(unittest.TestCase):
    def prepare(self, root, nodata=False):
        source=Path(root)/'dem.tif';make_dem(source,nodata)
        store=RegionalPackStore(Path(root)/'packs')
        store.install_local('terrain',source,dict(name='Test',source='Fixture',license='Test',
            source_date='2026-10-29',vertical_datum='NAVD88',units='m'),lambda:False)
        return store

    def test_sparse_samples_find_nodata_and_explain_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            store=self.prepare(folder,nodata=True)
            result=sample_area(store,[-97,32.99,-96.99,33],lambda:False)
            self.assertEqual(result['total'],121)
            self.assertGreater(result['missing'],0)
            self.assertGreater(result['valid'],0)
            self.assertEqual(result['missing']+result['valid'],121)
            self.assertIn('sparse',result['note'].lower())

    def test_outside_raster_is_missing_and_cancelled_checks_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            store=self.prepare(folder)
            result=sample_area(store,[-97,32.99,-96.98,33],lambda:False)
            self.assertGreater(result['missing'],0)
            with self.assertRaisesRegex(ValueError,'cancel'):
                sample_area(store,[-97,32.99,-96.99,33],lambda:True)

    def test_no_rasters_do_not_report_successful_samples(self):
        with tempfile.TemporaryDirectory() as folder:
            result=sample_area(RegionalPackStore(Path(folder)/'packs'),[-97,32,-96,33],lambda:False)
            self.assertEqual(result['status'],'no terrain packs')
            self.assertEqual(result['total'],0)

    def test_denser_grid_is_bounded_and_reports_selected_resolution(self):
        with tempfile.TemporaryDirectory() as folder:
            store=self.prepare(folder,nodata=True)
            result=sample_area(store,[-97,32.99,-96.99,33],lambda:False,grid_size=41)
            self.assertEqual(result['total'],1681)
            self.assertEqual(result['grid_size'],41)
            self.assertGreater(result['nodata'],0)
            self.assertIn('Sparse',result['note'])
            for invalid in (True,1,42):
                with self.assertRaises(ValueError):sample_area(store,[-97,32.99,-96.99,33],lambda:False,grid_size=invalid)

    def test_overlap_fills_missing_samples_but_mixed_datums_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            store=self.prepare(folder,nodata=True)
            source=Path(folder)/'second.tif';make_dem(source)
            store.install_local('terrain',source,dict(name='Second',source='Fixture',license='Test',
                source_date='2026-10-29',vertical_datum='Other',units='m'),lambda:False)
            result=sample_area(store,[-97,32.99,-96.99,33],lambda:False)
            self.assertEqual(result['missing'],0)
            self.assertFalse(result['compatible'])
            self.assertEqual(result['datums'],['NAVD88','Other'])


if __name__ == '__main__':
    unittest.main()
