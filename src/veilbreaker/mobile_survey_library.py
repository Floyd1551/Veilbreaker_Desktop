"""Durable, source-preserving local copies of mobile surveys; no diagnostic runs."""
import os
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .android_capture import MAX_BYTES, require, utc
from .mobile_survey_import import _unique, _reject_constant, load_mobile_survey
from .survey import session_lock

MAX_SURVEYS = 100
MAX_TOTAL_BYTES = 128 * 1024 * 1024
_HASH = re.compile(r'[0-9a-f]{64}\Z')


def _link_or_reparse(path):
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)
    except FileNotFoundError:
        return False


def _root(config, create=False):
    root = Path(config.root) / 'mobile-surveys'
    if create:
        root.mkdir(parents=True, exist_ok=True)
    if _link_or_reparse(root) or (root.exists() and not root.is_dir()):
        raise ValueError('Mobile survey storage is not a safe directory.')
    return root


def _folder(config, digest):
    require(isinstance(digest, str) and _HASH.fullmatch(digest) is not None, 'Invalid mobile survey identifier.')
    return _root(config) / digest


def _trash_marker(folder, digest):
    path = folder / 'trash.json'
    if not path.exists() and not _link_or_reparse(path): return None
    require(not _link_or_reparse(path) and path.is_file(), 'Mobile survey Trash marker is unsafe; data was preserved.')
    with path.open('rb') as stream: raw = stream.read(4097)
    require(len(raw) <= 4096, 'Mobile survey Trash marker is invalid; data was preserved.')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique, parse_constant=_reject_constant)
        require(isinstance(value, dict) and set(value) == {'format', 'schema_version', 'sha256', 'removed_utc'} and
                value['format'] == 'veilbreaker.mobile-survey-trash' and type(value['schema_version']) is int and
                value['schema_version'] == 1 and value['sha256'] == digest, 'Mobile survey Trash marker is invalid; data was preserved.')
        utc(value['removed_utc'])
        return value
    except (UnicodeError, RecursionError, TypeError, KeyError) as exc:
        raise ValueError('Mobile survey Trash marker is invalid; data was preserved.') from exc


def read_mobile_survey(config, digest, *, include_trashed=False):
    require(type(include_trashed) is bool, 'Invalid mobile survey visibility.')
    folder = _folder(config, digest)
    path = folder / 'source.json'
    require(not _link_or_reparse(folder) and folder.is_dir() and not _link_or_reparse(path) and path.is_file(),
            'Saved mobile survey is missing or unsafe; the stored copy was preserved.')
    marker = _trash_marker(folder, digest)
    require(include_trashed or marker is None, 'This mobile survey is in Trash; restore it before opening or importing again.')
    loaded = load_mobile_survey(path)
    require(loaded['sha256'] == digest, 'Saved mobile survey has changed; the stored copy was preserved.')
    return dict(loaded, path=str(path))


def list_mobile_surveys(config, *, trashed=False):
    require(type(trashed) is bool, 'Invalid mobile survey visibility.')
    root = _root(config)
    if not root.exists(): return [], 0
    entries = [path for path in root.iterdir() if _HASH.fullmatch(path.name)]
    require(len(entries) <= MAX_SURVEYS, 'Mobile survey library exceeds its entry limit.')
    rows = []; unavailable = 0; total = 0
    for folder in entries:
        try:
            source = folder / 'source.json'
            require(not _link_or_reparse(folder) and not _link_or_reparse(source) and source.is_file(), 'Unsafe mobile survey file.')
            size = source.stat().st_size
            require(size <= MAX_BYTES and total + size <= MAX_TOTAL_BYTES, 'Mobile survey library exceeds its size limit.')
            total += size
            loaded = read_mobile_survey(config, folder.name, include_trashed=True)
            marker = _trash_marker(folder, folder.name)
            if (marker is not None) != trashed: continue
            survey = loaded['survey']
            rows.append({'sha256': loaded['sha256'], 'name': survey['name'], 'lifecycle': survey['lifecycle'],
                         'created_utc': survey['created_utc'], 'point_count': len(survey['points']),
                         'removed_utc': marker['removed_utc'] if marker else None})
        except (OSError, ValueError):
            unavailable += 1
    rows.sort(key=lambda row: row['created_utc'], reverse=True)
    return rows, unavailable


def import_mobile_survey(config, source, expected_sha256):
    """Save exact validated source bytes once. Existing or damaged copies are never replaced."""
    loaded = load_mobile_survey(source)
    require(loaded['sha256'] == expected_sha256, 'Mobile survey changed since preview; reopen it before importing.')
    root = _root(config, create=True)
    require(not _link_or_reparse(root / 'library.lock'), 'Mobile survey library lock is unsafe.')
    with session_lock(root / 'library.json'):
        return _import_locked(config, root, loaded)


def _import_locked(config, root, loaded):
    folder = _folder(config, loaded['sha256'])
    if folder.exists() or _link_or_reparse(folder):
        existing = read_mobile_survey(config, loaded['sha256'])
        return {'path': existing['path'], 'sha256': loaded['sha256'], 'imported': False}
    rows, unavailable = list_mobile_surveys(config)
    removed, _ = list_mobile_surveys(config, trashed=True)
    require(len(rows) + len(removed) + unavailable < MAX_SURVEYS, 'Mobile survey library is full, including copies in Trash.')
    total = 0
    for entry in root.iterdir():
        if not _HASH.fullmatch(entry.name): continue
        candidate = entry / 'source.json'
        if _link_or_reparse(entry) or _link_or_reparse(candidate):
            raise ValueError('Unsafe mobile survey entry; stored data was preserved.')
        if candidate.is_file(): total += candidate.stat().st_size
    require(len(loaded['raw_bytes']) <= MAX_BYTES and total + len(loaded['raw_bytes']) <= MAX_TOTAL_BYTES,
            'Mobile survey library storage limit reached.')
    folder.mkdir()  # no merging or replacing another import
    target = folder / 'source.json'
    created = False
    try:
        with target.open('xb') as stream:
            created = True
            stream.write(loaded['raw_bytes']); stream.flush(); os.fsync(stream.fileno())
    except BaseException:
        if created:
            try: target.unlink(missing_ok=True)
            except OSError: pass
        try: folder.rmdir()
        except OSError: pass
        raise
    return {'path': str(target), 'sha256': loaded['sha256'], 'imported': True}


def trash_mobile_survey(config, digest):
    """Hide a validated copy without moving or modifying its evidence bytes."""
    root = _root(config)
    require(root.is_dir() and not _link_or_reparse(root / 'library.lock'), 'Mobile survey library is unavailable or unsafe.')
    with session_lock(root / 'library.json'):
        read_mobile_survey(config, digest)
        folder = _folder(config, digest); marker = folder / 'trash.json'
        require(_trash_marker(folder, digest) is None, 'Mobile survey is already in Trash.')
        payload = json.dumps({'format': 'veilbreaker.mobile-survey-trash', 'schema_version': 1, 'sha256': digest,
                              'removed_utc': datetime.now(timezone.utc).isoformat()}, ensure_ascii=False).encode('utf-8')
        created = False
        try:
            with marker.open('xb') as stream:
                created = True; stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        except BaseException:
            if created:
                try: marker.unlink(missing_ok=True)
                except OSError: pass
            raise


def restore_mobile_survey(config, digest):
    """Restore only when the exact original source is still intact."""
    root = _root(config)
    require(root.is_dir() and not _link_or_reparse(root / 'library.lock'), 'Mobile survey library is unavailable or unsafe.')
    with session_lock(root / 'library.json'):
        folder = _folder(config, digest)
        require(not _link_or_reparse(folder) and folder.is_dir(), 'Saved mobile survey is missing or unsafe.')
        require(_trash_marker(folder, digest) is not None, 'Mobile survey is not in Trash.')
        read_mobile_survey(config, digest, include_trashed=True)
        (folder / 'trash.json').unlink()


def delete_trashed_mobile_survey(config, digest):
    """Permanently remove only an intact trashed library copy, never its original source."""
    root = _root(config)
    require(root.is_dir() and not _link_or_reparse(root / 'library.lock'), 'Mobile survey library is unavailable or unsafe.')
    with session_lock(root / 'library.json'):
        folder = _folder(config, digest)
        require(not _link_or_reparse(folder) and folder.is_dir(), 'Saved mobile survey is missing or unsafe.')
        require(folder.resolve(strict=True).parent == root.resolve(strict=True), 'Mobile survey path is outside the library.')
        require(_trash_marker(folder, digest) is not None, 'Move the mobile survey to Trash before permanently deleting it.')
        read_mobile_survey(config, digest, include_trashed=True)
        source, marker = folder / 'source.json', folder / 'trash.json'
        require({item.name for item in folder.iterdir()} == {'source.json', 'trash.json'},
                'Unexpected files are present; the mobile survey was preserved.')
        require(all(not _link_or_reparse(path) and path.is_file() and path.resolve(strict=True).parent == folder.resolve(strict=True)
                    for path in (source, marker)), 'Mobile survey files are unsafe; the copy was preserved.')
        try:
            source.unlink(); marker.unlink(); folder.rmdir()
        except OSError as exc:
            raise OSError('Permanent removal could not finish; some library files may remain. The original mobile source and exports were not changed.') from exc
