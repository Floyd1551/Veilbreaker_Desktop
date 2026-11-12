"""Durable, source-preserving local copies of mobile surveys; no diagnostic runs."""
import os
import re
from pathlib import Path

from .android_capture import MAX_BYTES, require
from .mobile_survey_import import load_mobile_survey
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


def read_mobile_survey(config, digest):
    folder = _folder(config, digest)
    path = folder / 'source.json'
    require(not _link_or_reparse(folder) and folder.is_dir() and not _link_or_reparse(path) and path.is_file(),
            'Saved mobile survey is missing or unsafe; the stored copy was preserved.')
    loaded = load_mobile_survey(path)
    require(loaded['sha256'] == digest, 'Saved mobile survey has changed; the stored copy was preserved.')
    return dict(loaded, path=str(path))


def list_mobile_surveys(config):
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
            loaded = read_mobile_survey(config, folder.name)
            survey = loaded['survey']
            rows.append({'sha256': loaded['sha256'], 'name': survey['name'], 'lifecycle': survey['lifecycle'],
                         'created_utc': survey['created_utc'], 'point_count': len(survey['points'])})
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
    require(len(rows) + unavailable < MAX_SURVEYS, 'Mobile survey library is full.')
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
