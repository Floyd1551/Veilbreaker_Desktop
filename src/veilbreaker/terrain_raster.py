"""Local-only regional GeoTIFF sampling. GIS dependencies are imported lazily."""
import hashlib
import math
from pathlib import Path


def _path(path):
    value=str(path)
    if '://' in value or value.startswith(('/vsi','\\\\','//')):raise ValueError('Select a local GeoTIFF, not a URL or virtual/remote path.')
    path=Path(path).resolve()
    if path.suffix.lower() not in ('.tif','.tiff') or not path.is_file():raise ValueError('Select a local GeoTIFF file.')
    sidecars=[path.with_name(path.name+suffix) for suffix in ('.msk','.aux.xml','.ovr','.aux')]
    sidecars += [path.with_suffix(suffix) for suffix in ('.tfw','.tifw','.wld')]
    if any(sidecar.exists() for sidecar in sidecars):raise ValueError('External raster sidecars are unsupported; prepare a self-contained GeoTIFF.')
    if path.stat().st_size>8*1024**3:raise ValueError('Select a regional DEM no larger than 8 GiB.')
    return path


def _metadata(ds,path,declared):
    for key in ('source','vertical_datum'):
        value=declared.get(key)
        if not isinstance(value,str) or not value.strip() or value.strip().lower() in ('unknown','unspecified') or len(value)>500:
            raise ValueError('Confirm terrain source and vertical datum from its documentation.')
    if declared.get('units') not in ('m','ft','us-ft'):raise ValueError('Confirm elevation units: m, ft or us-ft.')
    if ds.driver!='GTiff' or ds.count!=1 or ds.crs is None:raise ValueError('Use a single-band GeoTIFF with a declared horizontal CRS.')
    if ds.dtypes[0] not in ('int16','int32','uint16','uint32','float32','float64'):raise ValueError('Unsupported elevation raster data type.')
    if any(Path(f).resolve()!=path for f in ds.files):raise ValueError('External raster sidecars are not supported; use a self-contained GeoTIFF.')
    if ds.units[0] and ds.units[0] not in ({'m','metre','meter'} if declared['units']=='m' else {'ft','foot'} if declared['units']=='ft' else {'us-ft','US survey foot'}):
        raise ValueError('Declared elevation units conflict with raster metadata.')
    if abs(ds.transform.a*ds.transform.e-ds.transform.b*ds.transform.d)<1e-20:raise ValueError('Invalid raster georeferencing.')
    if not all(math.isfinite(v) for v in (ds.scales[0],ds.offsets[0])) or ds.scales[0]<=0:raise ValueError('Invalid elevation scale/offset.')
    return dict(scale=ds.scales[0],offset=ds.offsets[0],source=declared['source'],vertical_datum=declared['vertical_datum'],units=declared['units'],
                crs=ds.crs.to_string(),bounds=list(ds.bounds),width=ds.width,height=ds.height,
                transform=list(ds.transform),nodata=ds.nodata if ds.nodata is not None and math.isfinite(ds.nodata) else None,
                sampling='nearest raster cell; half-pixel geodesic spacing',name=path.name)


def inspect_dem(path,declared_metadata):
    path=_path(path)
    import rasterio
    with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',PROJ_NETWORK='OFF'):
        with rasterio.open(path,driver='GTiff') as ds:return _metadata(ds,path,declared_metadata)


def sample_path(path,start_lonlat,end_lonlat,declared_metadata,cancelled):
    path=_path(path)
    for point in (start_lonlat,end_lonlat):
        if len(point)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in point) or not -180<=point[0]<=180 or not -85<=point[1]<=85:
            raise ValueError('Invalid or unsupported endpoint coordinates.')
    def check():
        if cancelled():raise ValueError('Terrain assessment cancelled.')
    check()
    import rasterio
    import numpy as np
    from pyproj import Geod,Transformer,network
    network.set_network_enabled(False)
    geod=Geod(ellps='WGS84');azimuth,_,length=geod.inv(*start_lonlat,*end_lonlat)
    if not 0<length<=100000:raise ValueError('Select distinct endpoints no more than 100 km apart.')
    digest=hashlib.sha256();before=path.stat()
    with path.open('rb') as stream:
        while chunk:=stream.read(1024*1024):check();digest.update(chunk)
    with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',PROJ_NETWORK='OFF',GDAL_CACHEMAX=64*1024*1024):
        with rasterio.open(path,driver='GTiff') as ds:
            metadata=_metadata(ds,path,declared_metadata)
            forward=Transformer.from_crs('EPSG:4326',ds.crs,always_xy=True,allow_ballpark=False,only_best=True)
            backward=Transformer.from_crs(ds.crs,'EPSG:4326',always_xy=True,allow_ballpark=False,only_best=True)
            resolutions=[]
            for i in range(17):
                lon,lat,_=geod.fwd(*start_lonlat,azimuth,length*i/16)
                x,y=forward.transform(lon,lat,errcheck=True)
                for dx,dy in ((ds.transform.a,ds.transform.d),(ds.transform.b,ds.transform.e)):
                    q=backward.transform(x+dx,y+dy,errcheck=True)
                    resolution=abs(geod.inv(lon,lat,*q)[2])
                    if not math.isfinite(resolution) or resolution<=0:raise ValueError('Cannot establish terrain resolution.')
                    resolutions.append(resolution)
            spacing=min(resolutions)/2
            count=max(3,math.ceil(length/spacing)+1)
            if count>4096:raise ValueError('Path needs more than 4096 samples at this DEM resolution. Choose a shorter path or a coarser regional DEM.')
            distances=[length*i/(count-1) for i in range(count)]
            points=[geod.fwd(*start_lonlat,azimuth,x)[:2] for x in distances]
            coords=[forward.transform(*point,errcheck=True) for point in points]
            elevations=[];factor={'m':1.,'ft':.3048,'us-ft':1200/3937}[metadata['units']]
            for (x,y),sample in zip(coords,ds.sample(coords,indexes=1,masked=True)):
                check();row,col=ds.index(x,y)
                value=None
                if 0<=row<ds.height and 0<=col<ds.width and not bool(np.ma.getmaskarray(sample)[0]):
                    z=(float(sample[0])*ds.scales[0]+ds.offsets[0])*factor
                    if math.isfinite(z):value=z
                elevations.append(value)
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('DEM changed while it was being read. Retry with a stable file.')
    metadata.update(sha256=digest.hexdigest(),sample_spacing_m=length/(count-1),minimum_pixel_m=min(resolutions),
                    horizontal_transform_accuracy_m=forward.accuracy)
    return dict(distances_m=distances,elevations_m=elevations,dem=metadata,coordinates=points,
                endpoints=[list(start_lonlat),list(end_lonlat)])
