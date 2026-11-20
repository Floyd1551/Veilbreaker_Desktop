"""Point-in-time inspection of registered map archives for an offline area.

Header inspection is not a full tile audit. Optional checksums compare bytes
with local metadata, not an authenticated publisher statement.
"""
import hashlib
import json
import os
import re
from pathlib import Path

from .area_coverage import _intersection
from .core import utcnow_iso
from .map_pack import inspect_pack, signature
from .regional_packs import _bounds

MAX_CATALOG_BYTES = 1024 * 1024
MAX_CHECKSUM_BYTES = 16 * 1024**3
MAX_SIDECAR_BYTES = 1024 * 1024
_HASH = re.compile(r'[0-9a-fA-F]{64}\Z')
_REGISTERED = ('name', 'size', 'bounds', 'minzoom', 'maxzoom', 'attribution')


class _Cancelled(ValueError):
    pass


def _check(cancelled):
    if cancelled():
        raise _Cancelled('Map readiness check cancelled.')


def _metadata(path):
    if not path.is_file() or path.stat().st_size > MAX_SIDECAR_BYTES:
        return None
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    return value if isinstance(value, dict) else None


def _expected_checksum(path, included):
    """Use only local metadata; its checksum is not an authentication claim."""
    choices = []
    if included:
        choices.append((path.parent.parent / 'manifest.json', 'map_sha256', 'included local manifest'))
    choices.append((path.with_suffix('.json'), 'sha256', 'adjacent local sidecar'))
    for metadata_path, key, source in choices:
        try:
            value = _metadata(metadata_path)
            digest = value.get(key) if value else None
        except (OSError, ValueError, TypeError):
            continue
        if isinstance(digest, str) and _HASH.fullmatch(digest):
            return digest.lower(), source
    return None, None


def _local_path_key(path):
    value = str(path)
    if value.startswith(('\\\\', '//')) or '://' in value:
        return None
    return os.path.normcase(os.path.abspath(value))


def _hash_archive(path, expected_signature, cancelled):
    before = signature(path)
    if before != expected_signature:
        raise ValueError('Map archive changed after header inspection.')
    if before[2] > MAX_CHECKSUM_BYTES:
        return None
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        stat = os.fstat(stream.fileno())
        if (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns) != before:
            raise ValueError('Map archive changed before checksum verification.')
        while chunk := stream.read(1024 * 1024):
            _check(cancelled)
            digest.update(chunk)
        stat = os.fstat(stream.fileno())
        if (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns) != before:
            raise ValueError('Map archive changed during checksum verification.')
    _check(cancelled)
    if signature(path) != before:
        raise ValueError('Map archive changed during checksum verification.')
    return digest.hexdigest()


def check_catalog_maps(catalog_path, included_path, bounds, cancelled, progress=lambda _: None, verify_checksum=False):
    """Inspect catalog and optional bundled map; never mutate registrations.

    ``complete`` indicates all identifiable archives could be inspected. It
    does not mean that the area has a map or that tiles are complete. Checksum
    absence does not make an otherwise valid archive unusable.
    """
    try:
        area = _bounds(bounds)
    except OverflowError as exc:
        raise ValueError('Enter valid area bounds.') from exc
    if not callable(cancelled) or not callable(progress) or type(verify_checksum) is not bool:
        raise ValueError('Invalid map readiness options.')
    _check(cancelled)
    warnings, rejected, entries, registered = [], [], [], []
    complete = True
    catalog = Path(catalog_path)
    try:
        if catalog.exists():
            if catalog.stat().st_size > MAX_CATALOG_BYTES:
                raise ValueError('Map catalog exceeds the size limit.')
            registered = json.loads(catalog.read_text(encoding='utf-8-sig'))
            if (not isinstance(registered, list) or len(registered) > 100 or
                    any(not isinstance(row, dict) or not isinstance(row.get('path'), str) for row in registered)):
                raise ValueError('Map catalog has invalid entries.')
    except (OSError, ValueError, TypeError, RecursionError):
        registered = []
        warnings.append('Map catalog is unavailable or invalid; registered maps could not be checked.')
        complete = False

    included_string = str(included_path) if included_path is not None else None
    included_key = _local_path_key(included_string) if included_string is not None else None
    rows = [(row, included_key is not None and _local_path_key(row['path']) == included_key) for row in registered]
    if included_string is not None and not any(included for _, included in rows):
        rows.append(({'path': included_string}, True))
    seen = set()
    for number, (row, included) in enumerate(rows, 1):
        _check(cancelled)
        raw_path = row['path']
        item = {'name': row.get('name') or Path(raw_path).name or 'Unnamed map',
                'path': raw_path, 'bounds': row.get('bounds'), 'source_date': row.get('source_date')}
        progress(f'Inspecting map {number} of {len(rows)}: {item["name"]}')
        # UNC shares are network-dependent and can block without cancellation.
        if raw_path.startswith(('\\\\', '//')) or '://' in raw_path:
            item.update(status='unsupported_remote', detail='Network or remote map paths were not checked for offline use.')
            rejected.append(item); complete = False; continue
        try:
            path = Path(raw_path).resolve()
            if str(path) in seen:
                continue
            seen.add(str(path))
            if not path.is_file():
                item.update(status='missing', detail='Map archive is not available at its registered path.')
                rejected.append(item); complete = False; continue
            pack = inspect_pack(path)
            if any(key in row and row[key] != pack[key] for key in _REGISTERED):
                item.update(status='changed', detail='Map header or metadata changed since registration; review and register it again.')
                rejected.append(item); complete = False; continue
            if not _intersection(area, _bounds(pack['bounds'])):
                continue
            checksum_status, checksum_source = 'not_checked', None
            expected = actual = None
            if verify_checksum:
                expected, checksum_source = _expected_checksum(path, included)
                if expected is None:
                    checksum_status = 'unavailable'
                else:
                    actual = _hash_archive(path, pack['signature'], cancelled)
                    if actual is None:
                        checksum_status = 'unavailable'
                        warnings.append('A map exceeds the checksum size limit; its bytes were not checked.')
                    elif actual != expected:
                        item.update(status='checksum_mismatch', detail='Map SHA-256 does not match local reference metadata.',
                                    expected_sha256=expected, actual_sha256=actual, checksum_source=checksum_source)
                        rejected.append(item); complete = False; continue
                    else:
                        checksum_status = 'verified'
            entries.append(dict(pack, available=True, source_date=row.get('source_date') or ('Included map' if included else None),
                                header_status='included' if included else 'matched', checksum_status=checksum_status,
                                checksum_source=checksum_source, expected_sha256=expected, actual_sha256=actual))
        except _Cancelled:
            raise
        except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
            item.update(status='invalid', detail='Map archive could not be inspected: ' + str(exc))
            rejected.append(item); complete = False
    _check(cancelled)
    return dict(entries=entries, rejected=rejected, warnings=warnings, complete=complete, checked_utc=utcnow_iso())
