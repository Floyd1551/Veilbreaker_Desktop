"""Offline frozen GIS acceptance check, using an explicitly synthetic terrain tile."""
import json
from pathlib import Path

def smoke(destination):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from PySide6.QtWidgets import QApplication
    from .terrain_raster import sample_path
    from .terrain_profile import assess_profile
    from .path_assessment_report import profile_png
    target=Path(destination);target.mkdir(parents=True,exist_ok=True)
    path=target/'synthetic-dem.tif'
    data=np.full((100,100),100,dtype='float32');data[:,45:55]=130
    with rasterio.open(path,'w',driver='GTiff',width=100,height=100,count=1,dtype='float32',crs='EPSG:4326',transform=from_origin(-97,33,.0001,.0001),nodata=-9999) as ds:ds.write(data,1)
    terrain=sample_path(path,[-96.999,32.995],[-96.991,32.995],dict(source='Synthetic acceptance fixture',vertical_datum='NAVD88',units='m'),lambda:False)
    result=assess_profile(terrain['distances_m'],terrain['elevations_m'],10,10,1900)
    assert result['status']=='sampled terrain obstructed',result
    app=QApplication.instance() or QApplication([])
    (target/'profile.png').write_bytes(profile_png(result))
    report=dict(passed=True,profile=result,dem=terrain['dem'])
    (target/'terrain-smoke.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Terrain raster/projection/profile smoke passed')
    return 0
