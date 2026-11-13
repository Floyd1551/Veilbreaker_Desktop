"""Recover survey-owned mobile evidence only from an exact original copy."""
import os

from .core import utcnow_iso
from .mobile_survey_import import load_mobile_survey
from .mobile_survey_library import _link_or_reparse
from .recovery import atomic_json
from .survey import _editable_session, _session_path, session_lock
from .survey_mobile_evidence import _folder


def _matching_record(session, loaded):
    records = session.get('mobile_sources', [])
    if not isinstance(records, list) or len(records) > 20:
        raise ValueError('Invalid survey mobile evidence records.')
    matching = [r for r in records if isinstance(r, dict) and r.get('sha256') == loaded['sha256']]
    if len(matching) != 1:
        raise ValueError('The selected source does not match a unique attachment in this survey.')
    record = matching[0]
    if record.get('name') != loaded['survey']['name'] or record.get('point_count') != len(loaded['survey']['points']):
        raise ValueError('The selected source does not match the recorded attachment metadata.')
    if 'recovery' in record:
        raise ValueError('This mobile source already has a recovery record; existing evidence was preserved.')
    return record


def _write_new(target, loaded):
    created = False
    try:
        with target.open('xb') as output:
            created = True
            output.write(loaded['raw_bytes'])
            output.flush()
            os.fsync(output.fileno())
        if load_mobile_survey(target)['raw_bytes'] != loaded['raw_bytes']:
            raise ValueError('Restored mobile source failed integrity validation.')
    except BaseException:
        if created:
            target.unlink(missing_ok=True)
        raise


def _recover(config, path, source, *, missing_only):
    loaded = load_mobile_survey(source)
    path = _session_path(config, path)
    with session_lock(path):
        session = _editable_session(config, path)
        record = _matching_record(session, loaded)
        folder = _folder(config, path, create=True)
        target = folder / (loaded['sha256'] + '.json')
        if _link_or_reparse(target):
            raise ValueError('The survey-owned source is unsafe; it was preserved.')
        if not target.exists():
            _write_new(target, loaded)
            status = 'missing_restored'
        else:
            if missing_only:
                raise ValueError('The survey-owned source already exists; it was preserved. Inspect it before restoring.')
            if not target.is_file():
                raise ValueError('The survey-owned source is unsafe; it was preserved.')
            try:
                original = load_mobile_survey(target)
            except ValueError:
                original = None
            if original is not None and original['raw_bytes'] == loaded['raw_bytes']:
                raise ValueError('The survey-owned source is intact; no recovery is needed.')
            recovery = folder / ('recovered-' + loaded['sha256'] + '.json')
            if _link_or_reparse(recovery):
                raise ValueError('The existing recovery asset is unsafe; it was preserved.')
            if recovery.exists():
                if not recovery.is_file():
                    raise ValueError('The existing recovery asset is unsafe; it was preserved.')
                try:
                    existing = load_mobile_survey(recovery)
                except ValueError as exc:
                    raise ValueError('The existing recovery asset is invalid; it was preserved.') from exc
                if existing['raw_bytes'] != loaded['raw_bytes']:
                    raise ValueError('The existing recovery asset does not match; it was preserved.')
            else:
                _write_new(recovery, loaded)
            timestamp = utcnow_iso()
            record['recovery'] = dict(filename=recovery.name, sha256=loaded['sha256'], restored_utc=timestamp)
            session.setdefault('edit_history', []).append(dict(timestamp=timestamp,
                action='recover damaged mobile evidence', sha256=loaded['sha256'], recovery_file=recovery.name))
            # A crash or late error may occur after journal replacement. Retain the
            # verified copy even if commit raises; a later attempt can reuse it.
            atomic_json(path, session)
            status = 'damaged_recovered'
    return {'sha256': loaded['sha256'], 'status': status}


def recover_mobile_source(config, path, source):
    """Restore a missing source or link an exact, separate copy of a damaged source."""
    return _recover(config, path, source, missing_only=False)


def restore_missing_mobile_source(config, path, source):
    """Copy matching original bytes into an absent asset; never replace evidence."""
    return _recover(config, path, source, missing_only=True)['sha256']
