"""Attach immutable mobile survey sources without creating diagnostic runs."""
import re
import os
import uuid
from collections import Counter
from pathlib import Path

from .core import utcnow_iso
from .mobile_survey_import import load_mobile_survey
from .mobile_survey_library import _link_or_reparse
from .recovery import atomic_json
from .survey import _editable_session, _session_path, read_session, session_lock

_HASH = re.compile(r'[0-9a-f]{64}\Z')


def _folder(config, path, create=False):
    path = _session_path(config, path)
    parent = path.parent / 'mobile-evidence'
    folder = parent / path.stem
    if create:
        for item in (parent, folder):
            if _link_or_reparse(item):
                raise ValueError('Survey evidence storage is unsafe.')
            item.mkdir(exist_ok=True)
    for item in (parent, folder):
        if _link_or_reparse(item) or (item.exists() and not item.is_dir()):
            raise ValueError('Survey evidence storage is unsafe.')
    return folder


def read_attached_mobile_surveys(config, path, session):
    records = session.get('mobile_sources', [])
    if not isinstance(records, list) or len(records) > 20:
        raise ValueError('Invalid attached mobile survey records.')
    result = []
    folder = _folder(config, path)
    seen = set()
    for record in records:
        digest = record.get('sha256') if isinstance(record, dict) else None
        if not isinstance(digest, str) or not _HASH.fullmatch(digest) or digest in seen:
            raise ValueError('Invalid attached mobile survey identifier.')
        seen.add(digest)
        target = folder / (digest + '.json')
        if _link_or_reparse(target) or not target.is_file():
            raise ValueError('Attached mobile survey is missing or unsafe.')
        loaded = load_mobile_survey(target)
        if loaded['sha256'] != digest:
            raise ValueError('Attached mobile survey failed integrity validation.')
        if record.get('name') != loaded['survey']['name'] or record.get('point_count') != len(loaded['survey']['points']):
            raise ValueError('Attached mobile survey metadata does not match its source.')
        result.append(dict(loaded, path=str(target)))
    return result


def read_attached_mobile_surveys_for_map(config, path, session):
    """Return verified sources and warnings for read-only display only.

    Export and mutation must keep using the strict reader. A damaged source
    cannot supply labels, notes, coordinates, or manual placements.
    """
    records = session.get('mobile_sources', [])
    if not isinstance(records, list) or len(records) > 20:
        return [], ['Mobile evidence list is invalid; attached mobile points are unavailable. Original evidence was preserved.']
    counts = Counter(record.get('sha256') for record in records if isinstance(record, dict)
                     and isinstance(record.get('sha256'), str) and _HASH.fullmatch(record['sha256']))
    loaded, warnings, warned = [], [], set()
    for index, record in enumerate(records, 1):
        digest = record.get('sha256') if isinstance(record, dict) else None
        valid = isinstance(digest, str) and _HASH.fullmatch(digest) is not None
        label = digest[:12] if valid else f'record {index}'
        if not valid:
            warnings.append(f'Mobile source {label} is invalid or duplicated; its points are unavailable. Original evidence was preserved.')
            continue
        if counts[digest] > 1:
            if digest not in warned:
                warnings.append(f'Mobile source {label} is duplicated; its points are unavailable. Original evidence was preserved.')
                warned.add(digest)
            continue
        try:
            loaded.extend(read_attached_mobile_surveys(config, path, {'mobile_sources': [record]}))
        except (OSError, ValueError, TypeError, KeyError):
            warnings.append(f'Mobile source {label} is unavailable or failed integrity validation; its points are omitted. Original evidence was preserved.')
    return loaded, warnings


def attach_mobile_survey(config, path, source):
    loaded = load_mobile_survey(source)
    points = loaded['survey']['points']
    if not points:
        raise ValueError('The mobile survey has no saved captures to attach.')
    path = _session_path(config, path)
    with session_lock(path):
        session = _editable_session(config, path)
        if session['lifecycle'] == 'completed':
            raise ValueError('Reopen the survey before adding mobile evidence.')
        existing = read_attached_mobile_surveys(config, path, session)
        ids = {str(uuid.UUID(p['capture']['capture_id'])) for item in existing for p in item['survey']['points']}
        if any(str(uuid.UUID(p['capture']['capture_id'])) in ids for p in points):
            raise ValueError('A capture is already attached to this survey.')
        if len(ids) + len(points) > 20:
            raise ValueError('A survey can contain at most 20 attached mobile captures.')
        folder = _folder(config, path, create=True)
        target = folder / (loaded['sha256'] + '.json')
        created = False
        try:
            if target.exists() or _link_or_reparse(target):
                if _link_or_reparse(target) or not target.is_file():
                    raise ValueError('Existing mobile evidence copy is unsafe.')
                existing_copy = load_mobile_survey(target)
                if existing_copy['raw_bytes'] != loaded['raw_bytes']:
                    raise ValueError('Existing mobile evidence copy does not match; data was preserved.')
            else:
                with target.open('xb') as stream:
                    created = True
                    stream.write(loaded['raw_bytes'])
                    stream.flush()
                    os.fsync(stream.fileno())
            session.setdefault('mobile_sources', []).append(dict(sha256=loaded['sha256'],
                name=loaded['survey']['name'], point_count=len(points), attached_utc=utcnow_iso()))
            atomic_json(path, session)
        except BaseException:
            if created:
                target.unlink(missing_ok=True)
            raise
    return read_session(config, path)
