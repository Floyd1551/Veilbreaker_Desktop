"""Restore a missing survey-owned mobile source from an exact original copy."""
import os

from .mobile_survey_import import load_mobile_survey
from .mobile_survey_library import _link_or_reparse
from .survey import _editable_session, _session_path, session_lock
from .survey_mobile_evidence import _folder


def restore_missing_mobile_source(config, path, source):
    """Copy only matching original bytes into an absent asset; never replace evidence."""
    loaded = load_mobile_survey(source)
    path = _session_path(config, path)
    with session_lock(path):
        session = _editable_session(config, path)
        records = session.get('mobile_sources', [])
        if not isinstance(records, list) or len(records) > 20:
            raise ValueError('Invalid survey mobile evidence records.')
        matching = [r for r in records if isinstance(r, dict) and r.get('sha256') == loaded['sha256']]
        if len(matching) != 1:
            raise ValueError('The selected source does not match a unique attachment in this survey.')
        record = matching[0]
        if record.get('name') != loaded['survey']['name'] or record.get('point_count') != len(loaded['survey']['points']):
            raise ValueError('The selected source does not match the recorded attachment metadata.')
        target = _folder(config, path, create=True) / (loaded['sha256'] + '.json')
        if target.exists() or _link_or_reparse(target):
            raise ValueError('The survey-owned source already exists; it was preserved. Inspect it before restoring.')
        created = False
        try:
            with target.open('xb') as output:
                created = True
                output.write(loaded['raw_bytes'])
                output.flush()
                os.fsync(output.fileno())
            if load_mobile_survey(target)['sha256'] != loaded['sha256']:
                raise ValueError('Restored mobile source failed integrity validation.')
        except BaseException:
            if created:
                target.unlink(missing_ok=True)
            raise
    return loaded['sha256']
