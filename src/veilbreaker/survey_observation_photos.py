"""Operator photos are survey annotations, not location or RF evidence."""
import hashlib
import re
import uuid
from pathlib import Path

from . import core
from .recovery import atomic_json
from .survey import _editable_session, _session_path, session_lock
from .survey_observations import _observations

MAX_BYTES = 20 * 1024 * 1024
MAX_PHOTOS = 20
MAX_THUMBNAIL_BYTES = 270000  # Keep a 20-photo self-contained report below the viewer's 8 MiB limit.
_ID = re.compile(r'[a-f0-9]{32}\Z')


def asset_directory(config, path):
    path = _session_path(config, path)
    base = (config.root / 'survey-observation-photos').resolve()
    target = (base / path.stem).resolve()
    if not target.is_relative_to(base):
        raise ValueError('Invalid survey photo location.')
    return target


def _row(session, observation_id, revision):
    if not isinstance(observation_id, str) or not _ID.fullmatch(observation_id):
        raise ValueError('Invalid observation ID.')
    if type(revision) is not int or revision < 0:
        raise ValueError('Invalid observation revision.')
    row = next ( (r for r in _observations(session) if isinstance(r, dict) and
                 r.get('id') == observation_id and not r.get('deleted_utc')), None)
    if row is None:
        raise ValueError('Observation was not found or was removed.')
    if row.get('revision', 0) != revision:
        raise ValueError('Observation changed. Reload it before changing its photo.')
    return row


def _thumbnail(raw):
    # Qt is needed only when attaching a photo, not for offline CLI exports.
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize, Qt
    from PySide6.QtGui import QImageReader
    buf = QBuffer(); buf.setData(QByteArray(raw)); buf.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buf); kind = bytes(reader.format()).lower()
    if kind not in (b'jpeg', b'jpg', b'png'):
        raise ValueError('Photo must be a readable JPEG or PNG image.')
    size = reader.size()
    if not size.isValid() or size.width() > 12000 or size.height() > 12000 or size.width() * size.height() > 64000000:
        raise ValueError('Photo dimensions are invalid or too large.')
    reader.setAutoTransform(True)
    if size.width() > 256 or size.height() > 256:
        reader.setScaledSize(size.scaled(QSize(256, 256), Qt.AspectRatioMode.KeepAspectRatio))
    image = reader.read()
    if image.isNull(): raise ValueError('Photo could not be decoded.')
    output = QBuffer(); output.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(output, 'PNG'): raise ValueError('Photo thumbnail could not be created.')
    thumbnail = bytes(output.data())
    if len(thumbnail) > MAX_THUMBNAIL_BYTES: raise ValueError('Photo thumbnail is too large.')
    return ('image/png' if kind == b'png' else 'image/jpeg'), thumbnail


def attach_photo(config, path, observation_id, source, *, expected_revision):
    source = Path(source)
    with source.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES: raise ValueError('Photo must be no larger than 20 MiB.')
    media, thumbnail = _thumbnail(raw)
    path = _session_path(config, path)
    with session_lock(path):
        session = _editable_session(config, path)
        if session.get('lifecycle') == 'completed': raise ValueError('Reopen the survey before adding photos.')
        row = _row(session, observation_id, expected_revision)
        if not row.get('photo') and sum(bool(r.get('photo')) for r in _observations(session) if isinstance(r, dict) and not r.get('deleted_utc')) >= MAX_PHOTOS:
            raise ValueError('Survey photo limit reached.')
        asset = uuid.uuid4().hex
        directory = asset_directory(config, path); directory.mkdir(parents=True, exist_ok=True)
        original_path = directory / (asset + '.source'); thumbnail_path = directory / (asset + '.png')
        photo = dict(asset_id=asset, source='operator', media_type=media, original_name=source.name[:255],
                     bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                     thumbnail_bytes=len(thumbnail), thumbnail_sha256=hashlib.sha256(thumbnail).hexdigest(), added_utc=core.utcnow_iso())
        previous = row.get('photo')
        try:
            original_path.write_bytes(raw); thumbnail_path.write_bytes(thumbnail)
            row['photo'] = photo; row['revision'] = expected_revision + 1; row['updated_utc'] = photo['added_utc']
            atomic_json(path, session)
        except Exception:
            original_path.unlink(missing_ok=True); thumbnail_path.unlink(missing_ok=True)
            raise
        _discard_unreferenced(directory, session, previous)
        return dict(row)


def _discard_unreferenced(directory, session, photo):
    """Remove superseded bytes only after the journal is safely committed."""
    if not isinstance(photo, dict): return
    asset = photo.get('asset_id')
    if not isinstance(asset, str) or not _ID.fullmatch(asset): return
    if any(isinstance(r, dict) and isinstance(r.get('photo'), dict) and r['photo'].get('asset_id') == asset
           for r in _observations(session)): return
    for suffix in ('.source', '.png'):
        try: (directory / (asset + suffix)).unlink(missing_ok=True)
        except OSError: pass  # A locked file can be cleaned up later; the journal is already saved.


def remove_photo(config, path, observation_id, *, expected_revision):
    path = _session_path(config, path)
    with session_lock(path):
        session = _editable_session(config, path)
        if session.get('lifecycle') == 'completed': raise ValueError('Reopen the survey before removing photos.')
        row = _row(session, observation_id, expected_revision)
        if not row.get('photo'): raise ValueError('Observation has no photo.')
        previous = row.pop('photo'); row['revision'] = expected_revision + 1; row['updated_utc'] = core.utcnow_iso()
        atomic_json(path, session)
        _discard_unreferenced(asset_directory(config, path), session, previous)


def photo_context(config, path, session, *, strict=False, export_dir=None):
    """Validate photo bytes; an export must not silently omit damaged assets."""
    result = {}
    directory = asset_directory(config, path)
    for row in session.get('observations', []):
        if not isinstance(row, dict) or row.get('deleted_utc') or not row.get('photo'): continue
        try:
            photo = row['photo']; asset = photo.get('asset_id')
            if not isinstance(asset, str) or not _ID.fullmatch(asset) or photo.get('media_type') not in ('image/png', 'image/jpeg'):
                raise ValueError('Invalid photo metadata.')
            def checked(suffix, size_key, hash_key, limit):
                file = directory / (asset + suffix)
                if file.is_symlink() or not file.is_file() or file.stat().st_size > limit: raise ValueError('Photo asset missing or too large.')
                data = file.read_bytes()
                if len(data) != photo.get(size_key) or hashlib.sha256(data).hexdigest() != photo.get(hash_key): raise ValueError('Photo integrity check failed.')
                return data
            raw = checked('.source', 'bytes', 'sha256', MAX_BYTES)
            thumbnail = checked('.png', 'thumbnail_bytes', 'thumbnail_sha256', MAX_THUMBNAIL_BYTES)
            if export_dir is not None:
                extension = '.png' if photo['media_type'] == 'image/png' else '.jpg'
                (Path(export_dir) / ('observation-photo-' + asset + extension)).write_bytes(raw)
            result[row['id']] = thumbnail
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            if strict: raise ValueError('Survey photo unavailable or invalid: ' + str(exc)) from exc
            result[row.get('id')] = None
    return result
