"""Local-only regional GeoTIFF sampling. GIS dependencies are imported lazily."""
import hashlib
import math
from contextlib import ExitStack
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


def sample_path_tiles(tiles, start_lonlat, end_lonlat, cancelled):
    """Sample one geodesic across compatible local DEM tiles without filling gaps."""
    if not isinstance(tiles, (list, tuple)) or not 1 <= len(tiles) <= 16:
        raise ValueError('Select 1–16 installed terrain tiles.')
    for point in (start_lonlat, end_lonlat):
        if (len(point) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in point)
                or not -180 <= point[0] <= 180 or not -85 <= point[1] <= 85):
            raise ValueError('Invalid or unsupported endpoint coordinates.')
    def check():
        if cancelled():
            raise ValueError('Terrain assessment cancelled.')
    check()
    import numpy as np
    import rasterio
    from pyproj import Geod, Transformer, network
    network.set_network_enabled(False)
    geod = Geod(ellps='WGS84')
    azimuth, _, length = geod.inv(*start_lonlat, *end_lonlat)
    if not 0 < length <= 100000:
        raise ValueError('Select distinct endpoints no more than 100 km apart.')
    entries = []
    with ExitStack() as stack:
        stack.enter_context(rasterio.Env(GDAL_PAM_ENABLED='NO', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                                         PROJ_NETWORK='OFF', GDAL_CACHEMAX=64 * 1024 * 1024))
        for spec in tiles:
            if not isinstance(spec, dict) or not isinstance(spec.get('metadata'), dict):
                raise ValueError('Invalid terrain tile selection.')
            path = _path(spec.get('path'))
            before = path.stat()
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                while chunk := stream.read(1024 * 1024):
                    check()
                    digest.update(chunk)
            expected = spec.get('sha256')
            if expected and digest.hexdigest() != expected:
                raise ValueError('Installed terrain tile checksum changed. Reverify or reinstall it.')
            ds = stack.enter_context(rasterio.open(path, driver='GTiff'))
            metadata = _metadata(ds, path, spec['metadata'])
            metadata['sha256'] = digest.hexdigest()
            forward = Transformer.from_crs('EPSG:4326', ds.crs, always_xy=True,
                                           allow_ballpark=False, only_best=True)
            backward = Transformer.from_crs(ds.crs, 'EPSG:4326', always_xy=True,
                                            allow_ballpark=False, only_best=True)
            resolutions = []
            for i in range(17):
                lon, lat, _ = geod.fwd(*start_lonlat, azimuth, length * i / 16)
                x, y = forward.transform(lon, lat, errcheck=True)
                for dx, dy in ((ds.transform.a, ds.transform.d), (ds.transform.b, ds.transform.e)):
                    q = backward.transform(x + dx, y + dy, errcheck=True)
                    resolution = abs(geod.inv(lon, lat, *q)[2])
                    if not math.isfinite(resolution) or resolution <= 0:
                        raise ValueError('Cannot establish terrain resolution.')
                    resolutions.append(resolution)
            entries.append(dict(path=path, before=before, dataset=ds, metadata=metadata,
                                forward=forward, resolution=min(resolutions),
                                pack_id=spec.get('pack_id'), sample_count=0))
        datums = {entry['metadata']['vertical_datum'] for entry in entries}
        units = {entry['metadata']['units'] for entry in entries}
        if len(datums) != 1:
            raise ValueError('Terrain tiles have different vertical datum declarations.')
        if len(units) != 1:
            raise ValueError('Terrain tiles have different elevation units.')
        minimum_pixel = min(entry['resolution'] for entry in entries)
        count = max(3, math.ceil(length / (minimum_pixel / 2)) + 1)
        if count > 4096:
            raise ValueError('Path needs more than 4096 samples at this DEM resolution. Choose a shorter path or coarser terrain.')
        distances = [length * i / (count - 1) for i in range(count)]
        points = [geod.fwd(*start_lonlat, azimuth, distance)[:2] for distance in distances]
        elevations = [None] * count
        conversion = {'m': 1., 'ft': .3048, 'us-ft': 1200 / 3937}[next(iter(units))]
        # Prefer the finer raster in overlap; a no-data cell may fall through to another tile.
        for entry in sorted(entries, key=lambda item: item['resolution']):
            ds = entry['dataset']
            coords = [entry['forward'].transform(*point, errcheck=True) for point in points]
            for index, ((x, y), sample) in enumerate(zip(coords, ds.sample(coords, indexes=1, masked=True))):
                check()
                if elevations[index] is not None:
                    continue
                row, col = ds.index(x, y)
                if 0 <= row < ds.height and 0 <= col < ds.width and not bool(np.ma.getmaskarray(sample)[0]):
                    z = (float(sample[0]) * ds.scales[0] + ds.offsets[0]) * conversion
                    if math.isfinite(z):
                        elevations[index] = z
                        entry['sample_count'] += 1
        for entry in entries:
            after = entry['path'].stat()
            before = entry['before']
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError('DEM changed while it was being read. Retry with stable files.')
    records = [dict(pack_id=entry['pack_id'], name=entry['metadata']['name'],
                    source=entry['metadata']['source'], vertical_datum=entry['metadata']['vertical_datum'],
                    units=entry['metadata']['units'], crs=entry['metadata']['crs'],
                    sha256=entry['metadata']['sha256'], sample_count=entry['sample_count'],
                    minimum_pixel_m=entry['resolution']) for entry in entries]
    combined_hash = hashlib.sha256(''.join(row['sha256'] for row in records).encode('ascii')).hexdigest()
    dem = dict(source='Installed terrain mosaic', vertical_datum=next(iter(datums)),
               units=next(iter(units)), crs='multiple rasters' if len({row['crs'] for row in records}) > 1 else records[0]['crs'],
               sha256=combined_hash, sample_spacing_m=length / (count - 1),
               minimum_pixel_m=minimum_pixel, sampling='nearest raster cell; finer tile first; no interpolation',
               tile_count=len(records))
    return dict(distances_m=distances, elevations_m=elevations, dem=dem, tiles=records,
                missing_samples=elevations.count(None), coordinates=points,
                endpoints=[list(start_lonlat), list(end_lonlat)])
