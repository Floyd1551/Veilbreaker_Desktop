"""Managed regional terrain and physical-structure reference packs."""
import hashlib
import json
import math
import re
import shutil
import uuid
from pathlib import Path

from .core import utcnow_iso
from .terrain_raster import inspect_dem

MAX_STRUCTURES_BYTES = 64 * 1024 * 1024
MAX_TERRAIN_BYTES = 8 * 1024 * 1024 * 1024
DATA_FILES = {'terrain': 'terrain.tif', 'structures': 'structures.geojson'}


def _bounds(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
        raise ValueError('Enter finite WGS84 bounds: west, south, east, north.')
    west, south, east, north = map(float, value)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError('Invalid WGS84 bounding box.')
    return [west, south, east, north]


def _text(metadata, key, maximum=500):
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'Enter a valid {key.replace("_", " ")}.')
    return value.strip()


def _structures(path, declared):
    if path.stat().st_size > MAX_STRUCTURES_BYTES:
        raise ValueError('Structure pack exceeds 64 MiB.')
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Structure pack must be valid UTF-8 GeoJSON.') from exc
    if not isinstance(document, dict) or document.get('type') != 'FeatureCollection' or not isinstance(document.get('features'), list):
        raise ValueError('Structure pack must be a GeoJSON FeatureCollection.')
    if 'crs' in document:
        raise ValueError('Structure GeoJSON must use WGS84 longitude/latitude without a projected CRS declaration.')
    features = document['features']
    if not features or len(features) > 100_000:
        raise ValueError('Structure pack must contain 1–100,000 points.')
    ids = set()
    west, south, east, north = declared
    for feature in features:
        if not isinstance(feature, dict) or feature.get('type') != 'Feature':
            raise ValueError('Structure feature is invalid.')
        geometry, properties = feature.get('geometry'), feature.get('properties')
        if not isinstance(geometry, dict) or geometry.get('type') != 'Point' or not isinstance(properties, dict):
            raise ValueError('Structure features must be Point features.')
        coordinates = geometry.get('coordinates')
        if not isinstance(coordinates, list) or len(coordinates) != 2:
            raise ValueError('Structure point needs WGS84 longitude and latitude.')
        lon, lat = coordinates
        if type(lon) not in (int, float) or type(lat) not in (int, float) or not all(math.isfinite(v) for v in (lon, lat)):
            raise ValueError('Structure coordinates must be finite numbers.')
        if not west <= lon <= east or not south <= lat <= north:
            raise ValueError('Structure point lies outside the declared coverage.')
        key = properties.get('structure_id')
        if not isinstance(key, str) or not key.strip() or len(key) > 80:
            raise ValueError('Every structure needs a source identifier.')
        if key in ids:
            raise ValueError('Structure pack contains duplicate identifiers.')
        ids.add(key)
        owner = properties.get('owner')
        if owner is not None and (not isinstance(owner, str) or len(owner) > 200):
            raise ValueError('Invalid structure owner.')
        height = properties.get('height_agl_m')
        if height is not None and (type(height) not in (int, float) or not math.isfinite(height) or not 0 <= height <= 2000):
            raise ValueError('Invalid structure height above ground.')
    return len(features)


class RegionalPackStore:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def _folder(self, pack_id):
        if not isinstance(pack_id, str) or not re.fullmatch(r'[a-f0-9]{32}', pack_id):
            raise ValueError('Invalid regional pack identifier.')
        folder = self.root / pack_id
        if folder.resolve().parent != self.root or folder.is_symlink():
            raise ValueError('Invalid regional pack path.')
        return folder

    def _manifest(self, pack_id):
        folder = self._folder(pack_id)
        path = folder / 'manifest.json'
        if path.stat().st_size > 65536:
            raise ValueError('Regional pack manifest is too large.')
        row = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(row, dict) or row.get('schema_version') != 1 or row.get('pack_id') != pack_id
                or row.get('kind') not in DATA_FILES or row.get('data_file') != DATA_FILES[row['kind']]):
            raise ValueError('Invalid regional pack manifest.')
        return row

    def list_packs(self):
        if not self.root.exists():
            return []
        rows = []
        for folder in sorted(self.root.iterdir()):
            if not re.fullmatch(r'[a-f0-9]{32}', folder.name) or not folder.is_dir():
                continue
            try:
                row = self._manifest(folder.name)
                data = folder / row['data_file']
                status = 'missing' if not data.is_file() else 'available' if data.stat().st_size == row['bytes'] else 'changed-size'
                rows.append(dict(row, status=status))
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                rows.append({'pack_id': folder.name, 'name': folder.name, 'kind': 'unknown', 'status': 'invalid manifest'})
        return rows

    def data_path(self, pack_id):
        row = self._manifest(pack_id)
        path = self._folder(pack_id) / row['data_file']
        if path.is_symlink() or not path.is_file() or path.stat().st_size != row['bytes']:
            raise ValueError('Regional pack data is missing or changed; verify or reinstall it.')
        return path

    def verify(self, pack_id, cancelled=lambda: False):
        row = self._manifest(pack_id)
        path = self._folder(pack_id) / row['data_file']
        if path.is_symlink() or not path.is_file() or path.stat().st_size != row['bytes']:
            return False
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while chunk := stream.read(1024 * 1024):
                if cancelled():
                    raise ValueError('Pack verification cancelled.')
                digest.update(chunk)
        return digest.hexdigest() == row['sha256']

    def install_local(self, kind, source, metadata, cancelled, progress=lambda _: None):
        if kind not in DATA_FILES:
            raise ValueError('Choose terrain or physical structures.')
        source = Path(source)
        if not source.is_file() or source.is_symlink():
            raise ValueError('Choose a local pack file.')
        limit = MAX_TERRAIN_BYTES if kind == 'terrain' else MAX_STRUCTURES_BYTES
        if source.stat().st_size > limit:
            raise ValueError('Regional pack exceeds the size limit.')
        name = _text(metadata, 'name', 100)
        provenance = {key: _text(metadata, key) for key in ('source', 'license', 'source_date')}
        if kind == 'terrain':
            declared = {'source': provenance['source'], 'vertical_datum': _text(metadata, 'vertical_datum'),
                        'units': metadata.get('units')}
            if source.suffix.lower() not in ('.tif', '.tiff'):
                raise ValueError('Terrain pack must be a self-contained GeoTIFF.')
        else:
            declared_bounds = _bounds(metadata.get('bounds_wgs84'))
            if declared_bounds[2] - declared_bounds[0] > 5 or declared_bounds[3] - declared_bounds[1] > 5:
                raise ValueError('Declare a regional structure extent no larger than 5° × 5°.')
            if source.suffix.lower() not in ('.geojson', '.json'):
                raise ValueError('Structure pack must be GeoJSON.')
        if cancelled():
            raise ValueError('Pack installation cancelled.')
        self.root.mkdir(parents=True, exist_ok=True)
        pack_id = uuid.uuid4().hex
        staging = self.root / ('.staging-' + pack_id)
        staging.mkdir()
        try:
            target = staging / DATA_FILES[kind]
            digest = hashlib.sha256()
            size = 0
            with source.open('rb') as incoming, target.open('wb') as outgoing:
                while chunk := incoming.read(1024 * 1024):
                    if cancelled():
                        raise ValueError('Pack installation cancelled.')
                    size += len(chunk)
                    if size > limit:
                        raise ValueError('Regional pack exceeds the size limit.')
                    outgoing.write(chunk)
                    digest.update(chunk)
                    progress({'bytes': size})
            row = dict(schema_version=1, pack_id=pack_id, kind=kind, name=name,
                       **provenance, imported_utc=utcnow_iso(), sha256=digest.hexdigest(),
                       bytes=size, data_file=DATA_FILES[kind])
            if metadata.get('download_origin'):
                origin = metadata['download_origin']
                if (not isinstance(origin, str) or not origin.startswith('https://')
                        or any(character in origin for character in ('?', '#', '@'))):
                    raise ValueError('Invalid sanitized download origin.')
                row['download_origin'] = origin
                row['download_integrity'] = metadata.get('download_integrity', 'computed SHA-256 only')
            if metadata.get('download_requested_origin'):
                requested = metadata['download_requested_origin']
                if (not isinstance(requested, str) or not requested.startswith('https://')
                        or any(character in requested for character in ('?', '#', '@'))):
                    raise ValueError('Invalid sanitized requested download origin.')
                row['download_requested_origin'] = requested
            if kind == 'terrain':
                details = inspect_dem(target, declared)
                from rasterio.warp import transform_bounds
                bounds = transform_bounds(details['crs'], 'EPSG:4326', *details['bounds'], densify_pts=21)
                row.update(bounds_wgs84=_bounds(bounds), vertical_datum=declared['vertical_datum'],
                           units=declared['units'], crs=details['crs'], width=details['width'],
                           height=details['height'], coverage_note='Raster bounds; no-data gaps may exist.')
            else:
                row.update(bounds_wgs84=declared_bounds, record_count=_structures(target, declared_bounds),
                           coverage_note='Declared reference extent, not completeness; no serving-cell association.')
            if cancelled():
                raise ValueError('Pack installation cancelled.')
            (staging / 'manifest.json').write_text(json.dumps(row, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            staging.rename(self._folder(pack_id))
            return row
        finally:
            if staging.exists():
                if staging.resolve().parent != self.root:
                    raise ValueError('Unsafe staging path.')
                shutil.rmtree(staging)

    def remove(self, pack_id):
        folder = self._folder(pack_id)
        if not folder.is_dir():
            return False
        self._manifest(pack_id)
        if folder.resolve().parent != self.root:
            raise ValueError('Unsafe pack path.')
        shutil.rmtree(folder)
        return True

    def query_structures(self, pack_id, bounds, limit=1000):
        row = self._manifest(pack_id)
        if row['kind'] != 'structures':
            raise ValueError('Select a physical-structure pack.')
        west, south, east, north = _bounds(bounds)
        path = self.data_path(pack_id)
        if not self.verify(pack_id):
            raise ValueError('Structure pack checksum changed.')
        document = json.loads(path.read_text(encoding='utf-8'))
        result = []
        for feature in document['features']:
            lon, lat = feature['geometry']['coordinates']
            if west <= lon <= east and south <= lat <= north:
                properties = feature['properties']
                result.append(dict(structure_id=properties['structure_id'], owner=properties.get('owner'),
                                   height_agl_m=properties.get('height_agl_m'), lon=lon, lat=lat,
                                   reference_kind='physical structure'))
                if len(result) >= limit:
                    break
        return result
