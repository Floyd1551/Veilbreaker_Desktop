"""Explicit, bounded integrity checks for installed regional area packs.

Checksums establish file integrity against the local manifest only. They do not
establish completeness of any dataset, geographic coverage, or terrain quality.
"""
from .area_coverage import _intersection
from .core import utcnow_iso
from .regional_packs import _bounds

MAX_MATCHING_PACKS = 128
_PROVENANCE = ('pack_id', 'name', 'kind', 'source', 'source_date', 'license',
               'sha256', 'bounds_wgs84', 'coverage_note')


def verify_area_packs(store, bounds, cancelled, progress=lambda _: None):
    """Verify intersecting regional packs without changing their registration.

    ``complete`` indicates the bounded inspection finished, not that the area
    has any data or that every inspected file passed. ``all_verified`` is true
    only when there was at least one pack and every identified check passed.
    """
    area = _bounds(bounds)
    if not callable(cancelled) or not callable(progress):
        raise ValueError('Invalid verification callback.')

    def check():
        if cancelled():
            raise ValueError('Area pack verification cancelled.')

    check()
    matching = []
    warnings = []
    complete = True
    for row in store.list_packs():
        check()
        if row.get('kind') == 'unknown':
            complete = False
            if 'An invalid pack manifest could not be checked for area overlap.' not in warnings:
                warnings.append('An invalid pack manifest could not be checked for area overlap.')
            continue
        if row.get('kind') not in ('terrain', 'structures'):
            continue
        try:
            extent = _bounds(row.get('bounds_wgs84'))
        except (ValueError, TypeError, OverflowError):
            complete = False
            warning = 'A regional pack has invalid bounds and could not be checked for area overlap.'
            if warning not in warnings:
                warnings.append(warning)
            continue
        if _intersection(area, extent):
            matching.append(row)

    if len(matching) > MAX_MATCHING_PACKS:
        complete = False
        warnings.append(f'Verification limit is {MAX_MATCHING_PACKS} packs; remaining intersecting packs were not checked.')
    packs = []
    for index, row in enumerate(matching[:MAX_MATCHING_PACKS], 1):
        check()
        item = {key: row.get(key) for key in _PROVENANCE}
        progress(f'Verifying area pack {index} of {min(len(matching), MAX_MATCHING_PACKS)}: {row.get("name") or row["pack_id"]}')
        if row.get('status') != 'available':
            item.update(status='unavailable', detail='The pack file is missing or its size changed.')
            packs.append(item)
            continue
        try:
            manifest = store._manifest(row['pack_id'])
            listed = {key: value for key, value in row.items() if key != 'status'}
            if manifest != listed:
                raise ValueError('The pack manifest changed during verification.')
            path = store.data_path(row['pack_id'])
            before = path.stat()
            verified = store.verify(row['pack_id'], cancelled)
            check()
            after = path.stat()
            if ((before.st_size, before.st_mtime_ns, before.st_ino) !=
                    (after.st_size, after.st_mtime_ns, after.st_ino) or
                    store._manifest(row['pack_id']) != manifest):
                raise ValueError('The pack or its manifest changed during verification.')
            if verified:
                item.update(status='verified', detail='File SHA-256 matches the installed manifest.')
            else:
                item.update(status='failed', detail='File SHA-256 does not match the installed manifest.')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            check()
            if isinstance(exc, ValueError) and 'cancel' in str(exc).lower():
                raise ValueError('Area pack verification cancelled.') from exc
            item.update(status='failed', detail='Pack could not be verified: ' + str(exc))
        packs.append(item)
    check()
    return dict(bounds=area, checked_utc=utcnow_iso(), packs=packs, complete=complete,
                all_verified=bool(packs) and complete and all(p['status'] == 'verified' for p in packs),
                warnings=warnings, total_intersecting=len(matching))
