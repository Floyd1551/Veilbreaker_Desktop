"""Bounded offline search of independently sourced physical-structure packs.

These are physical-reference records, not inferred cell matches or evidence
that a structure is currently present or serving the receiver.
"""
import hashlib
import heapq
import json
import math

from .cell_matching import distance_bearing
from .regional_packs import MAX_STRUCTURES_BYTES, _bounds

MAX_PACKS = 128
MAX_FEATURES = 1_000_000
MAX_RESULTS = 200
_EARTH_RADIUS_M = 6371008.8


def _check(cancelled):
    if cancelled():
        raise ValueError('Structure search cancelled.')


def _number(value, lower, upper, label):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and lower <= value <= upper
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError('Enter a valid ' + label + '.')
    return float(value)


def _search_boxes(latitude, longitude, radius_m):
    angle = radius_m / _EARTH_RADIUS_M
    lat = math.radians(latitude)
    south, north = max(-90., latitude - math.degrees(angle)), min(90., latitude + math.degrees(angle))
    if south <= -90 or north >= 90 or math.cos(lat) <= math.sin(angle):
        return [(-180., south, 180., north)]
    width = math.degrees(math.asin(min(1., math.sin(angle) / math.cos(lat))))
    west, east = longitude - width, longitude + width
    if west < -180:
        return [(west + 360., south, 180., north), (-180., south, east, north)]
    if east > 180:
        return [(west, south, 180., north), (-180., south, east - 360., north)]
    return [(west, south, east, north)]


def _intersects(left, right):
    return left[0] <= right[2] and left[2] >= right[0] and left[1] <= right[3] and left[3] >= right[1]


def _box_covered(box, extents):
    """Conservatively check a rectangle against the union of pack extents."""
    west, south, east, north = box
    edges = {west, east}
    for left, bottom, right, top in extents:
        if _intersects(box, (left, bottom, right, top)):
            edges.update((max(west, left), min(east, right)))
    edges = sorted(edges)
    for x0, x1 in zip(edges, edges[1:]):
        if x1 <= x0:
            continue
        mid = (x0 + x1) / 2
        intervals = sorted((max(south, bottom), min(north, top))
                           for left, bottom, right, top in extents
                           if left <= mid <= right and bottom <= north and top >= south)
        covered_to = south
        for bottom, top in intervals:
            if bottom > covered_to:
                break
            covered_to = max(covered_to, top)
            if covered_to >= north:
                break
        if covered_to < north:
            return False
    return True


def _read_verified(store, row, cancelled):
    """Hash the same bounded bytes that are decoded, not an earlier read."""
    path = store.data_path(row['pack_id'])
    expected_size = row.get('bytes')
    if type(expected_size) is not int or not 0 < expected_size <= MAX_STRUCTURES_BYTES:
        raise ValueError('Structure pack has an invalid size.')
    digest = hashlib.sha256()
    chunks = []
    size = 0
    with path.open('rb') as stream:
        while True:
            _check(cancelled)
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > expected_size or size > MAX_STRUCTURES_BYTES:
                raise ValueError('Structure pack size changed.')
            digest.update(chunk)
            chunks.append(chunk)
    if size != expected_size or digest.hexdigest() != row.get('sha256'):
        raise ValueError('Structure pack checksum changed.')
    try:
        document = json.loads(b''.join(chunks))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('Structure pack is not valid GeoJSON.') from exc
    features = document.get('features') if isinstance(document, dict) and document.get('type') == 'FeatureCollection' else None
    if not isinstance(features, list) or not features or len(features) > 100_000 or 'crs' in document:
        raise ValueError('Structure pack has an invalid feature collection.')
    return features


def _optional_text(value, maximum):
    return value if isinstance(value, str) and len(value) <= maximum else None


def nearby_structures(store, latitude, longitude, radius_km=10, limit=30, cancelled=lambda: False):
    """Search verified nearby structure records; results never claim a cell match.

    ``total_matches`` counts only verified records examined. If limits or pack
    errors prevent a complete search, ``search_incomplete`` and warnings say so.
    Pack extents describe supplied data, not completeness of physical towers.
    """
    latitude = _number(latitude, -90, 90, 'receiver latitude')
    longitude = _number(longitude, -180, 180, 'receiver longitude')
    radius = _number(radius_km, 0, 100, 'radius in kilometres')
    if radius == 0:
        raise ValueError('Enter a radius greater than zero.')
    if type(limit) is not int or not 1 <= limit <= MAX_RESULTS:
        raise ValueError('Enter a result limit from 1 to 200.')
    if not callable(cancelled):
        raise ValueError('Invalid cancellation callback.')
    _check(cancelled)
    boxes = _search_boxes(latitude, longitude, radius * 1000.)
    warnings = ['Installed physical-structure records may be incomplete or outdated; proximity does not establish a serving cell, antenna location or line of sight.']
    packs, relevant = [], []
    incomplete = False
    for row in store.list_packs():
        _check(cancelled)
        if row.get('kind') == 'unknown':
            warnings.append('A regional pack manifest is invalid; its coverage and contents could not be checked.')
            incomplete = True
            continue
        if row.get('kind') != 'structures':
            continue
        try:
            bounds = _bounds(row.get('bounds_wgs84'))
        except (ValueError, OverflowError):
            warnings.append('A structure pack has invalid coverage bounds and was excluded.')
            incomplete = True
            continue
        if any(_intersects(bounds, box) for box in boxes):
            relevant.append((row, bounds))
    if not relevant:
        warnings.append('No installed structure pack declares coverage intersecting this search area.')
    if len(relevant) > MAX_PACKS:
        warnings.append(f'More than {MAX_PACKS} structure packs intersect the search; remaining packs were not checked and closer records may be omitted.')
        incomplete = True
    heap = []
    total = scanned = sequence = 0
    inspected = relevant[:MAX_PACKS]
    for pack_index, (row, bounds) in enumerate(inspected):
        _check(cancelled)
        if row.get('status') != 'available':
            warnings.append('A structure pack intersecting the search is unavailable or changed; its records were excluded.')
            incomplete = True
            continue
        try:
            fields = ('pack_id', 'name', 'source', 'source_date', 'license', 'sha256', 'coverage_note')
            if any(not isinstance(row.get(key), str) or not row[key] for key in fields):
                raise ValueError('Structure pack provenance is incomplete.')
            features = _read_verified(store, row, cancelled)
        except (OSError, ValueError, KeyError, TypeError):
            _check(cancelled)
            warnings.append('A structure pack failed integrity or provenance checks; its records were excluded.')
            incomplete = True
            continue
        provenance = dict(pack_id=row['pack_id'], pack_name=row['name'], source=row['source'],
                          source_date=row['source_date'], license=row['license'], sha256=row['sha256'],
                          bounds_wgs84=bounds, coverage_note=row['coverage_note'])
        packs.append(provenance)
        for feature in features:
            if scanned >= MAX_FEATURES:
                incomplete = True
                warnings.append(f'Search stopped after {MAX_FEATURES:,} structure entries; results may omit closer records.')
                break
            scanned += 1
            if scanned % 1024 == 0:
                _check(cancelled)
            try:
                if not isinstance(feature, dict) or feature.get('type') != 'Feature':
                    raise ValueError
                geometry = feature.get('geometry')
                properties = feature.get('properties')
                coordinates = geometry.get('coordinates') if isinstance(geometry, dict) and geometry.get('type') == 'Point' else None
                if not isinstance(coordinates, list) or len(coordinates) != 2 or not isinstance(properties, dict):
                    raise ValueError
                lon = _number(coordinates[0], -180, 180, 'structure longitude')
                lat = _number(coordinates[1], -90, 90, 'structure latitude')
                ident = properties.get('structure_id')
                if not isinstance(ident, str) or not ident.strip() or len(ident) > 80 or not (bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]):
                    raise ValueError
                owner = properties.get('owner')
                if owner is not None and _optional_text(owner, 200) is None:
                    raise ValueError
                height = properties.get('height_agl_m')
                if height is not None:
                    height = _number(height, 0, 2000, 'structure height')
            except (ValueError, TypeError):
                incomplete = True
                if 'A structure entry was invalid and omitted.' not in warnings:
                    warnings.append('A structure entry was invalid and omitted.')
                continue
            if not any(box[0] <= lon <= box[2] and box[1] <= lat <= box[3] for box in boxes):
                continue
            distance, bearing = distance_bearing(longitude, latitude, lon, lat)
            if distance > radius * 1000.:
                continue
            total += 1
            candidate = dict(provenance, structure_id=ident, owner=owner, height_agl_m=height,
                             lon=lon, lat=lat, distance_m=distance, bearing_deg=bearing,
                             reference_kind='physical structure',
                             verification='Physical structure reference; serving relationship unverified',
                             position_source=_optional_text(properties.get('position_source'), 200),
                             registration_number=_optional_text(properties.get('registration_number'), 80),
                             registration_status=_optional_text(properties.get('registration_status'), 80))
            sequence += 1
            item = (-distance, sequence, candidate)
            if len(heap) < limit:
                heapq.heappush(heap, item)
            elif distance < -heap[0][0]:
                heapq.heapreplace(heap, item)
        if scanned >= MAX_FEATURES:
            if pack_index < len(inspected) - 1 and not any('Search stopped after' in warning for warning in warnings):
                incomplete = True
                warnings.append(f'Search stopped after {MAX_FEATURES:,} structure entries; results may omit closer records.')
            break
    _check(cancelled)
    extents = [pack['bounds_wgs84'] for pack in packs]
    coverage = 'none' if not extents else ('full' if all(_box_covered(box, extents) for box in boxes) else 'partial')
    if coverage != 'full':
        incomplete = True
        warnings.append('Verified pack extents do not cover the full search bounding area; structures outside those extents were not checked.')
    candidates = sorted((item[2] for item in heap), key=lambda item: (item['distance_m'], item['pack_id'], item['structure_id']))
    return dict(candidates=candidates, packs=packs, total_matches=total, truncated=total > limit,
                declared_coverage=coverage, search_incomplete=incomplete, warnings=warnings)
