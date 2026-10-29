"""Read-only regional readiness preview; extents are not verified coverage."""
import sqlite3
from contextlib import closing
from pathlib import Path

from .cell_reference import active_reference, _folder
from .regional_packs import _bounds


def _intersection(a, b):
    west, south, east, north = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    return [west, south, east, north] if west < east and south < north else None


def _rectangles(rows, key, target, available):
    found = []
    for row in rows:
        if not available(row):
            continue
        try:
            extent = _bounds(row.get(key))
        except (ValueError, TypeError):
            continue
        if clipped := _intersection(target, extent):
            found.append((row, clipped))
    return found


def _gaps(area, rectangles):
    west, south, east, north = area
    edges = sorted({west, east, *(p for r in rectangles for p in (r[0], r[2]))})
    gaps = []
    for left, right in zip(edges, edges[1:]):
        intervals = sorted((r[1], r[3]) for r in rectangles if r[0] <= left and r[2] >= right)
        cursor = south
        for low, high in intervals:
            if low > cursor:
                gaps.append([left, cursor, right, low])
            cursor = max(cursor, high)
        if cursor < north:
            gaps.append([left, cursor, right, north])
    return gaps


def area_preview(bounds, regional_rows, map_rows, cell_root, cancelled=lambda: False):
    area = _bounds(bounds)
    if cancelled():
        raise ValueError('Area preview cancelled.')
    terrain = _rectangles([r for r in regional_rows if r.get('kind') == 'terrain'], 'bounds_wgs84', area,
                          lambda r: r.get('status') == 'available')
    gaps = _gaps(area, [r[1] for r in terrain])
    maps = _rectangles(map_rows, 'bounds', area, lambda r: r.get('available') is True)
    structures = _rectangles([r for r in regional_rows if r.get('kind') == 'structures'], 'bounds_wgs84', area,
                             lambda r: r.get('status') == 'available')
    map_full = any(not _gaps(area, [rectangle]) for _, rectangle in maps)
    result = {
        'bounds': area,
        'map': {'status': 'bounds contain area' if map_full else 'bounds overlap area' if maps else 'no available map bounds',
                'packs': [r for r, _ in maps],
                'note': 'Bounds and zoom range do not prove every map tile or local detail is available.'},
        'terrain': {'status': 'bounds cover area' if terrain and not gaps else 'bounds have gaps' if terrain else 'no available terrain bounds',
                    'packs': [r for r, _ in terrain], 'gaps': gaps[:100], 'gap_count': len(gaps),
                    'note': 'Raster bounds only; no-data gaps, vertical datum compatibility and checksum verification require further checks.'},
        'structures': {'status': 'declared bounds overlap' if structures else 'no structure extent overlaps',
                       'packs': [r for r, _ in structures],
                       'note': 'Declared extents do not prove structure completeness or serving-cell association.'},
        'cell': {'status': 'no active cell reference', 'count': None, 'groups': [],
                 'note': 'Cell records are estimated positions, not verified towers; counts do not prove complete coverage.'},
    }
    try:
        reference = active_reference(Path(cell_root))
    except (OSError, ValueError, KeyError, TypeError):
        reference = None
        result['cell'].update(status='reference unavailable', note='The active cell reference could not be opened. Repair or select a reference before relying on cell counts.')
    if reference:
        database = _folder(cell_root, reference['dataset_id']) / 'cells.sqlite'
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
            db.set_progress_handler(lambda: 1 if cancelled() else 0, 10000)
            try:
                rows = db.execute("SELECT radio,mcc,mnc,COUNT(*) FROM cells WHERE "
                    "json_extract(payload,'$.lon') BETWEEN ? AND ? AND json_extract(payload,'$.lat') BETWEEN ? AND ? "
                    "GROUP BY radio,mcc,mnc ORDER BY radio,mcc,mnc", (area[0], area[2], area[1], area[3])).fetchall()
            except sqlite3.OperationalError as exc:
                if cancelled():
                    raise ValueError('Area preview cancelled.') from exc
                raise ValueError('Cell reference could not be inspected: ' + str(exc)) from exc
        groups = [dict(radio=r[0],mcc=r[1],mnc=r[2],count=r[3]) for r in rows]
        result['cell'].update(status='records found' if groups else 'no records found', count=sum(r['count'] for r in groups),
                              groups=groups, source=reference.get('source'), date=reference.get('date'),
                              attribution=reference.get('attribution'), sha256=reference.get('sha256'))
    if cancelled():
        raise ValueError('Area preview cancelled.')
    return result
