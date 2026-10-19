"""Location evidence quality without mixing phone and desktop clocks."""
import math
import html
import csv
import io


def _number(value):
    try: return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError: return False


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


def report_html(rows, fragment=False):
    def esc(value):
        return html.escape('Not exposed' if value is None else str(value))
    body = '<h2>Location evidence</h2><p>Qualified fixes: age ≤10 seconds, horizontal accuracy ≤25 m, and not marked mock. The first qualified fix represents this capture.</p>'
    body += '<table><tr><th>Observation</th><th>Quality</th><th>Latitude</th><th>Longitude</th><th>Accuracy (m)</th><th>Age (ms)</th></tr>'
    for row in rows:
        values = [row.get('observation_id'), row['quality']['label'], row.get('latitude_deg'),
                  row.get('longitude_deg'), row.get('horizontal_accuracy_m'), row.get('fix_age_ms')]
        body += '<tr>' + ''.join('<td>' + esc(value) + '</td>' for value in values) + '</tr>'
    body += '</table><p>Coordinates identify the receiver, not the cell tower.</p>'
    if fragment:
        return body
    return '<!doctype html><html><head><meta charset="utf-8"><title>Location evidence</title><style>body{font-family:sans-serif;padding:24px}table{border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #aaa;text-align:left}</style></head><body>' + body + '</body></html>'


def report_csv(rows):
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    keys = ('observation_id', 'received_utc', 'latitude_deg', 'longitude_deg',
            'horizontal_accuracy_m', 'fix_age_ms', 'source', 'provider')
    writer.writerow((*keys, 'quality'))
    for row in rows:
        values = [row.get(key) for key in keys] + [row['quality']['label']]
        writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for v in values])
    return output.getvalue()
