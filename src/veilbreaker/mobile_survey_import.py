"""Read-only review and explicit extraction of mobile survey captures."""
import hashlib
import json
from pathlib import Path
import uuid

from .android_capture import MAX_BYTES, require, utc, validate_capture


def _unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'Duplicate JSON key in mobile survey')
        value[key] = item
    return value


def _reject_constant(value):
    raise ValueError('Nonfinite number in mobile survey JSON')


def _validate(survey):
    require(isinstance(survey, dict), 'Mobile survey must be an object')
    require(survey.get('format') == 'veilbreaker.mobile.survey' and type(survey.get('schema_version')) is int
            and survey['schema_version'] == 1, 'Unsupported mobile survey format/version')
    try:
        uuid.UUID(survey.get('survey_id', ''))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Invalid mobile survey ID') from exc
    name = survey.get('name')
    require(isinstance(name, str) and 1 <= len(name.strip()) <= 80 and not any(ord(c) < 32 for c in name), 'Invalid mobile survey name')
    utc(survey.get('created_utc'))
    require(survey.get('lifecycle') in ('open', 'completed'), 'Invalid mobile survey state')
    if survey['lifecycle'] == 'completed': utc(survey.get('completed_utc'))
    points = survey.get('points')
    require(isinstance(points, list) and len(points) <= 20, 'Mobile survey may contain at most 20 points')
    seen = set()
    for index, point in enumerate(points, 1):
        require(isinstance(point, dict), f'Invalid mobile point {index}')
        utc(point.get('attached_utc'))
        note = point.get('operator_note')
        require(note is None or (isinstance(note, str) and len(note) <= 500 and
                not any(ord(c) < 32 and c != '\n' for c in note)), f'Invalid operator note at point {index}')
        capture = point.get('capture')
        try:
            validate_capture(capture)
        except ValueError as exc:
            raise ValueError(f'Invalid capture at point {index}: {exc}') from exc
        capture_id = str(uuid.UUID(capture['capture_id']))
        require(capture_id not in seen, 'Duplicate capture in mobile survey')
        seen.add(capture_id)


def load_mobile_survey(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, 'Mobile survey exceeds 16 MiB')
    try:
        survey = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique, parse_constant=_reject_constant)
        _validate(survey)
    except (UnicodeError, RecursionError, TypeError) as exc:
        raise ValueError('Invalid or excessively nested mobile survey JSON') from exc
    return {'survey': survey, 'sha256': hashlib.sha256(raw).hexdigest()}


def write_selected_capture(source, expected_sha256, index, destination):
    """Revalidate the source and write a new standalone capture without replacing files."""
    loaded = load_mobile_survey(source)
    require(loaded['sha256'] == expected_sha256, 'Mobile survey changed since preview; reopen it before extracting.')
    points = loaded['survey']['points']
    require(type(index) is int and 0 <= index < len(points), 'Choose a valid mobile survey point')
    payload = json.dumps(points[index]['capture'], indent=2, ensure_ascii=False, allow_nan=False).encode('utf-8')
    target = Path(destination)
    created = False
    try:
        with target.open('xb') as stream:
            created = True
            stream.write(payload)
    except BaseException:
        if created:
            target.unlink(missing_ok=True)
        raise
    return target
