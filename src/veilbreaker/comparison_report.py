"""Visit-pair annotations and portable comparison reports, separate from evidence."""
import hashlib
import json
from pathlib import Path
from .core import utcnow_iso
from .recovery import atomic_json
from .survey_report import table, text


def notes_path(root, baseline, current):
    key = hashlib.sha256(json.dumps([baseline, current]).encode('utf-8')).hexdigest()
    return Path(root) / 'survey-comparisons' / (key + '.json')


def load_notes(root, baseline, current):
    path = notes_path(root, baseline, current)
    if not path.exists():
        return {'notes': '', 'updated_utc': None}
    value = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(value, dict) or value.get('baseline') != baseline or
            value.get('current') != current or not isinstance(value.get('notes'), str)):
        raise ValueError('Saved comparison notes are invalid.')
    return value


def save_notes(root, baseline, current, notes):
    if not isinstance(notes, str) or len(notes) > 2000:
        raise ValueError('Change notes must contain at most 2000 characters.')
    value = {'baseline': baseline, 'current': current, 'notes': notes, 'updated_utc': utcnow_iso()}
    path = notes_path(root, baseline, current)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(path, value)
    return value


def report_html(result, notes='', updated_utc=None):
    parts = ['<!doctype html><html><head><meta charset="utf-8"><title>Survey visit comparison</title>',
             '<style>body{font-family:Arial,sans-serif;color:#172131;background:white;margin:28px;}'
             'h1,h2{color:#126759;}table{border-collapse:collapse;border-color:#ccd6df;}'
             'th{background:#e8f3f0;}td{vertical-align:top;}</style></head><body>',
             '<h1>Survey visit comparison</h1>', '<p>Site: ' + text(result.get('site_id')) + '</p>',
             table(['Visit', 'Name', 'Created (UTC)', 'Survey ID', 'Collection state'],
                   [[name, *[result[side].get(k) for k in ('name', 'created_utc', 'survey_id', 'status')]]
                    for name, side in [('Baseline', 'baseline'), ('Current', 'current')]]),
             '<h2>Recorded change</h2><p>' + text(notes or 'No change notes recorded.') + '</p>',
             '<p>Operator annotation; it does not establish the cause of measured changes. Updated (UTC): ' + text(updated_utc or 'Not saved') + '</p>',
             '<p>Original settings: ' + ('match' if result.get('settings_match') else 'different or unavailable') + '.</p>',
             '<p>' + text(result.get('interpretation', 'Change is current minus baseline, not an improvement score.')) + '</p>']
    rows = result.get('rows', [])
    for title, selected in [('Measured changes (including unchanged values)', [r for r in rows if r['delta'] is not None]),
                            ('Unavailable comparisons', [r for r in rows if r['delta'] is None])]:
        parts.append(f'<h2>{title}</h2>')
        parts.append(table(['Point / metric', 'Baseline', 'Current', 'Change / reason'],
            [[r['point'] + ' / ' + r['metric'], r['baseline'], r['current'],
              r['delta'] if r['delta'] is not None else r['notes'] or 'Change unavailable'] for r in selected]) if selected else '<p>None.</p>')
    refs = sorted({(r['point'], r.get('baseline_run') or 'Unavailable', r.get('current_run') or 'Unavailable') for r in rows})
    parts.extend(['<h2>Run references</h2>', table(['Point', 'Baseline run', 'Current run'], refs),
                  '<p>This report is a comparison snapshot, not an integrity verification. Original survey and run evidence remain unchanged.</p></body></html>'])
    return '\n'.join(parts)
