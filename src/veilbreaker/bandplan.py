"""Offline reference annotations; no inference about received signal identity."""
import csv
import io
import json
import math
from pathlib import Path

NOTICE = 'Expected uses only; not signal identification or permission to transmit. Selected bands, not a complete allocation table. Unlabeled frequencies may have other uses.'


def validate_plan(data):
    if not isinstance(data, dict) or not isinstance(data.get('bands'), list) or not 1 <= len(data['bands']) <= 1000:
        raise ValueError('Band plan must contain 1–1000 bands.')
    def text(value, limit=500):
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError('Band names and metadata must be nonempty text within the length limit.')
        return value.strip()
    result = {key: text(data.get(key, default)) for key, default in (
        ('name', 'Custom band plan'), ('region', 'Custom'), ('version', 'User supplied'))}
    rows = []
    for row in data['bands']:
        if not isinstance(row, dict):
            raise ValueError('Each band must be an object.')
        try:
            if isinstance(row['min_mhz'], bool) or isinstance(row['max_mhz'], bool):
                raise ValueError()
            low, high = float(row['min_mhz']), float(row['max_mhz'])
            if not (math.isfinite(low) and math.isfinite(high) and 0 <= low <= high <= 1000000):
                raise ValueError()
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError('Band limits must be finite MHz values: 0 <= min <= max <= 1000000.') from exc
        rows.append({'min_mhz': low, 'max_mhz': high, 'kind': 'marker' if low == high else 'band',
                     'label': text(row.get('label', row.get('band')), 120),
                     'service': text(row.get('service', row.get('expected_use')) or 'User supplied reference'),
                     'source': text(row.get('source') or 'User supplied; unverified')})
    result['bands'] = sorted(rows, key=lambda row: (row['min_mhz'], row['max_mhz'], row['label']))
    return result


def load_plan(path):
    path = Path(path)
    with path.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Band plan exceeds 1 MiB.')
    try:
        content = raw.decode('utf-8-sig')
        if path.suffix.lower() == '.csv':
            data = {'name': path.stem, 'bands': list(csv.DictReader(io.StringIO(content)))}
        elif path.suffix.lower() == '.json':
            data = json.loads(content)
            if isinstance(data, list):
                data = {'name': path.stem, 'bands': data}
        else:
            raise ValueError('Choose a CSV or JSON band plan.')
        return validate_plan(data)
    except (UnicodeError, csv.Error, RecursionError) as exc:
        raise ValueError('Cannot read this UTF-8 band plan.') from exc


def default_plan():
    return load_plan(Path(__file__).parent / 'assets' / 'us-band-plan.json')


def bands_at(plan, frequency):
    return [band for band in plan['bands'] if band['min_mhz'] <= frequency < band['max_mhz']
            or frequency == band['min_mhz'] == band['max_mhz']]
