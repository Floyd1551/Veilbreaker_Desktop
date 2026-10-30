"""Optional sparse checks of installed terrain cells over a survey area."""
import math
from contextlib import ExitStack

from .area_coverage import _intersection
from .regional_packs import _bounds
from .terrain_raster import _metadata, _path


def sample_area(store, bounds, cancelled, grid_size=11):
    """Inspect grid-cell centers. Results never establish full raster coverage."""
    area = _bounds(bounds)
    if type(grid_size) is not int or not 2 <= grid_size <= 41:
        raise ValueError('Terrain preview grid must be between 2 and 41 points per side.')
    def check():
        if cancelled():
            raise ValueError('Terrain preview cancelled.')
    check()
    rows = []
    for row in store.list_packs():
        if row.get('kind') != 'terrain' or row.get('status') != 'available':
            continue
        try:
            if _intersection(area, _bounds(row.get('bounds_wgs84'))):
                rows.append(row)
        except ValueError:
            continue
    note = ('Sparse grid sample only; unsampled no-data holes may exist. '
            'Terrain is bare earth. Checksums were not reverified by this preview.')
    if not rows:
        return dict(status='no terrain packs', total=0, valid=0, missing=0, note=note, examples=[])
    if len(rows) > 16:
        raise ValueError('Terrain preview supports at most 16 overlapping packs; choose a smaller area.')
    import numpy as np
    import rasterio
    from pyproj import Transformer, network
    from rasterio.windows import Window
    network.set_network_enabled(False)
    west,south,east,north=area
    points=[(west+(east-west)*(x+.5)/grid_size, south+(north-south)*(y+.5)/grid_size)
            for y in range(grid_size) for x in range(grid_size)]
    valid=missing=outside=nodata=0;examples=[];datasets=[]
    with ExitStack() as stack:
        stack.enter_context(rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',PROJ_NETWORK='OFF'))
        for row in rows:
            check()
            path=_path(store.data_path(row['pack_id']))
            before=path.stat()
            ds=stack.enter_context(rasterio.open(path,driver='GTiff'))
            metadata=_metadata(ds,path,dict(source=row['source'],vertical_datum=row['vertical_datum'],units=row['units']))
            transformer=Transformer.from_crs('EPSG:4326',ds.crs,always_xy=True,allow_ballpark=False,only_best=True)
            datasets.append((row,path,before,ds,metadata,transformer))
        for lon,lat in points:
            check();inside=False;found=False
            for row,path,before,ds,metadata,transformer in datasets:
                extent=row['bounds_wgs84']
                if not (extent[0] <= lon <= extent[2] and extent[1] <= lat <= extent[3]):
                    continue
                x,y=transformer.transform(lon,lat,errcheck=True)
                pixel_row,pixel_col=ds.index(x,y)
                if not (0 <= pixel_row < ds.height and 0 <= pixel_col < ds.width):
                    continue
                inside=True
                value=ds.read(1,window=Window(pixel_col,pixel_row,1,1),masked=True)
                if value.size and not bool(np.ma.getmaskarray(value)[0,0]) and math.isfinite(float(value[0,0])):
                    found=True;break
            if found:
                valid+=1
            else:
                missing+=1
                if inside: nodata+=1
                else: outside+=1
                if len(examples)<10:examples.append([round(lon,6),round(lat,6)])
        for row,path,before,ds,metadata,transformer in datasets:
            after=path.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
                raise ValueError('A terrain pack changed during preview. Retry with stable files.')
    datums=sorted({row['vertical_datum'] for row in rows})
    units=sorted({row['units'] for row in rows})
    return dict(status='sampled',grid_size=grid_size,total=len(points),valid=valid,missing=missing,
                outside=outside,nodata=nodata,examples=examples,pack_count=len(rows),
                datums=datums,units=units,compatible=len(datums)==1 and len(units)==1,note=note)
