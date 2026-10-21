import tempfile
import unittest
from pathlib import Path
try:
    import rasterio
    import numpy as np
    from rasterio.transform import from_origin
except ImportError:
    rasterio=None
from veilbreaker.terrain_raster import sample_path,inspect_dem

META=dict(source='Synthetic fixture',vertical_datum='NAVD88',units='m')

def make_dem(path,nodata=False):
    data=np.full((100,100),100,dtype='float32')
    if nodata:data[:,45:55]=-9999
    with rasterio.open(path,'w',driver='GTiff',width=100,height=100,count=1,dtype='float32',crs='EPSG:4326',transform=from_origin(-97,33,.0001,.0001),nodata=-9999) as ds:ds.write(data,1)

@unittest.skipIf(rasterio is None,'terrain dependency unavailable')
class RasterTests(unittest.TestCase):
    def test_sample_units_coverage_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'dem.tif';make_dem(path)
            result=sample_path(path,[-96.999,32.995],[-96.991,32.995],META,lambda:False)
            self.assertGreater(len(result['distances_m']),3)
            self.assertTrue(all(x==100 for x in result['elevations_m']))
            feet=sample_path(path,[-96.999,32.995],[-96.991,32.995],dict(META,units='ft'),lambda:False)
            self.assertAlmostEqual(feet['elevations_m'][0],30.48)
            outside=sample_path(path,[-96.999,32.995],[-96.98,32.995],META,lambda:False)
            self.assertIn(None,outside['elevations_m'])
            make_dem(path,True)
            self.assertIn(None,sample_path(path,[-96.999,32.995],[-96.991,32.995],META,lambda:False)['elevations_m'])
            with self.assertRaises(ValueError):sample_path(path,[-96.999,32.995],[-96.991,32.995],META,lambda:True)
            with self.assertRaises(ValueError):inspect_dem(path,dict(META,vertical_datum='Unknown'))
    def test_remote_paths_rejected(self):
        for path in ['https://example.com/a.tif','/vsicurl/https://example.com/a.tif']:
            with self.assertRaises(ValueError):inspect_dem(path,META)

    def test_projected_raster_and_resolution_limit(self):
        from pyproj import Transformer
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'projected.tif'
            x,y=Transformer.from_crs(4326,3857,always_xy=True).transform(-97,33)
            with rasterio.open(path,'w',driver='GTiff',width=100,height=100,count=1,dtype='float32',crs='EPSG:3857',transform=from_origin(x,y,20,20)) as ds:
                ds.write(np.full((100,100),125,dtype='float32'),1)
            result=sample_path(path,[-96.999,32.995],[-96.991,32.995],META,lambda:False)
            self.assertTrue(all(z==125 for z in result['elevations_m']))
            self.assertEqual(result['dem']['crs'],'EPSG:3857')
            make_dem(path)
            with self.assertRaisesRegex(ValueError,'4096'):
                sample_path(path,[-96.999,32.995],[-96.5,32.995],META,lambda:False)

    def test_elevation_scale_and_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'scaled.tif';make_dem(path)
            with rasterio.open(path,'r+') as ds:ds.scales=[.5];ds.offsets=[10]
            result=sample_path(path,[-96.999,32.995],[-96.991,32.995],META,lambda:False)
            self.assertTrue(all(z==60 for z in result['elevations_m']))

    def test_external_mask_is_rejected_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'masked.tif';make_dem(path)
            with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
                with rasterio.open(path,'r+') as ds:
                    mask=np.full((100,100),255,dtype='uint8');mask[:,45:55]=0;ds.write_mask(mask)
            self.assertTrue(path.with_name(path.name+'.msk').exists())
            with self.assertRaisesRegex(ValueError,'sidecar'):
                sample_path(path,[-96.999,32.995],[-96.991,32.995],META,lambda:False)
