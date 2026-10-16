"""Location evidence quality without mixing phone and desktop clocks."""
import math


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def qualify_location(location):
    location = location or {}
    reasons = []
    if location.get('status') != 'available':
        reasons.append('No fix')
    for key, limit in (('latitude_deg', 90), ('longitude_deg', 180)):
        value = location.get(key)
        if not _number(value) or abs(value) > limit:
            reasons.append('Missing or invalid coordinates')
            break
    age = location.get('fix_age_ms')
    accuracy = location.get('horizontal_accuracy_m')
    if not _number(age) or age < 0:
        reasons.append('Unknown fix age')
    elif age > 10000:
        reasons.append('Old fix')
    if not _number(accuracy) or accuracy < 0:
        reasons.append('Unknown accuracy')
    elif accuracy > 25:
        reasons.append('Low accuracy')
    if location.get('mock') is True:
        reasons.append('Mock location')
    return {'qualified': not reasons, 'reasons': reasons,
            'label': 'Qualified fix' if not reasons else '; '.join(reasons)}


def location_rows(envelope):
    rows = []
    for observation in envelope.get('observations', []):
        location = dict(observation.get('location') or {})
        offsets = []
        age = location.get('fix_age_ms')
        for cell in observation.get('cells', []):
            modem_age = cell.get('age_ms')
            offset = modem_age - age if (_number(age) and age >= 0 and
                                        _number(modem_age) and modem_age >= 0) else None
            offsets.append({'radio': cell.get('radio'), 'identity': cell.get('identity'),
                            'location_after_modem_ms': offset})
        rows.append(dict(location, observation_id=observation.get('observation_id'),
                         received_utc=observation.get('received_utc'),
                         quality=qualify_location(location), cell_offsets=offsets))
    return rows


def representative_fix(rows):
    """First qualified observation; never invent an averaged position."""
    return next((row for row in rows if row['quality']['qualified']), None)
