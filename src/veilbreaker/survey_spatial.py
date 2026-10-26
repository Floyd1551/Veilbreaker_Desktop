"""Operator placement sidecars. Captured coordinates and run evidence are immutable."""
import hashlib
import json
import math
import re
import shutil
import uuid
from pathlib import Path
from .core import utcnow_iso
from .recovery import atomic_json
from .survey import _session_path, _editable_session, session_lock
from .survey_imagery import decode_image, MAX_BYTES


def _root(config, path):
    path = _session_path(config, path)
    return path.parent / 'spatial' / path.stem


def _number(value, low, high):
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        raise ValueError('Position or scale must contain finite values in the supported range.')
    return float(value)


def _floor_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'floor-[0-9a-f]{32}', value):
        raise ValueError('Invalid floor identifier.')
    return value


def _placement(value, floors):
    if not isinstance(value, dict):
        raise ValueError('Invalid manual placement.')
    if value.get('kind') == 'geographic':
        return dict(kind='geographic', latitude=_number(value.get('latitude'), -85.05112878, 85.05112878),
                    longitude=_number(value.get('longitude'), -180, 180))
    if value.get('kind') == 'floor':
        floor = _floor_id(value.get('floor_id'))
        if floor not in floors:
            raise ValueError('Choose an imported floor plan.')
        return dict(kind='floor', floor_id=floor, x=_number(value.get('x'), 0, 1), y=_number(value.get('y'), 0, 1))
    raise ValueError('Choose geographic or floor-plan placement.')


def load_spatial(config, path):
    target = _root(config, path) / 'spatial.json'
    if not target.exists():
        return dict(schema_version=1, placements={}, floors={}, history=[])
    if target.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Spatial metadata exceeds the supported size.')
    data = json.loads(target.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema_version') != 1 or not isinstance(data.get('floors'), dict) or not isinstance(data.get('placements'), dict):
        raise ValueError('Invalid spatial metadata.')
    if len(data['floors']) > 20 or len(data['placements']) > 20 or not isinstance(data.get('history'), list) or len(data['history']) > 1000:
        raise ValueError('Spatial metadata limits exceeded.')
    for key, floor in data['floors'].items():
        _floor_id(key)
        if not isinstance(floor, dict) or not isinstance(floor.get('label'), str) or not 1 <= len(floor['label']) <= 100:
            raise ValueError('Invalid floor description.')
        for dimension in ('width', 'height'):
            _number(floor.get(dimension), 1, 2048)
        if not re.fullmatch('[0-9a-f]{64}', str(floor.get('sha256', ''))):
            raise ValueError('Invalid floor integrity metadata.')
        calibration = floor.get('calibration')
        if calibration is not None:
            if not isinstance(calibration, dict):
                raise ValueError('Invalid floor calibration.')
            _number(calibration.get('meters_per_pixel'), 1e-9, 100000)
            _number(calibration.get('meters'), .001, 100000)
            for key in ('first', 'second'):
                if not isinstance(calibration.get(key), list) or len(calibration[key]) != 2:
                    raise ValueError('Invalid calibration points.')
                for value in calibration[key]:
                    _number(value, 0, 1)
    for value in data['placements'].values():
        _placement(value, data['floors'])
        if value.get('source') != 'operator':
            raise ValueError('Manual placements must identify their source as operator.')
        if not isinstance(value.get('placed_utc'), str) or not value['placed_utc']:
            raise ValueError('Manual placement timestamp is missing.')
    return data


def unplaced_measurements(steps, spatial, gps_run_ids):
    """Count collected runs only; planned points are not measurements."""
    return [step['run_id'] for step in steps
            if step.get('evidence_zip') and step['run_id'] not in gps_run_ids
            and step['run_id'] not in spatial['placements']]


def _edit(config, path):
    session = _editable_session(config, path)
    if session.get('lifecycle') == 'completed':
        raise ValueError('Reopen the survey before editing placements.')
    return session, load_spatial(config, path)


def _save(config, path, data, action, **context):
    if len(data['history']) >= 1000:
        raise ValueError('Spatial edit history is full; start a new survey.')
    data['history'].append(dict(action=action, timestamp=utcnow_iso(), **context))
    root = _root(config, path)
    root.mkdir(parents=True, exist_ok=True)
    atomic_json(root / 'spatial.json', data)


def import_floor(config, path, source, label):
    if not isinstance(label, str) or not 1 <= len(label.strip()) <= 100:
        raise ValueError('Supply a floor label of 1–100 characters.')
    with Path(source).open('rb') as stream:
        image = decode_image(stream.read(MAX_BYTES + 1))
    path = _session_path(config, path)
    with session_lock(path):
        _, data = _edit(config, path)
        if len(data['floors']) >= 20:
            raise ValueError('A survey supports at most 20 floor plans.')
        floor = 'floor-' + uuid.uuid4().hex
        root = _root(config, path)
        root.mkdir(parents=True, exist_ok=True)
        target = root / (floor + '.png')
        if not image.save(str(target), 'PNG'):
            raise ValueError('Could not save the survey floor plan.')
        data['floors'][floor] = dict(label=label.strip(), width=image.width(), height=image.height(),
                                     sha256=hashlib.sha256(target.read_bytes()).hexdigest())
        _save(config, path, data, 'import floor', floor_id=floor)
        return floor


def read_floor(config, path, floor_id):
    floor_id = _floor_id(floor_id)
    floor = load_spatial(config, path)['floors'].get(floor_id)
    if floor is None:
        raise ValueError('Floor plan is missing.')
    target = _root(config, path) / (floor_id + '.png')
    with target.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if hashlib.sha256(raw).hexdigest() != floor['sha256']:
        raise ValueError('Floor-plan integrity check failed.')
    image = decode_image(raw)
    if (image.width(), image.height()) != (floor['width'], floor['height']):
        raise ValueError('Floor-plan dimensions changed.')
    return image


def remove_floor(config, path, floor_id):
    path = _session_path(config, path)
    with session_lock(path):
        _, data = _edit(config, path)
        floor_id = _floor_id(floor_id)
        if any(p.get('floor_id') == floor_id for p in data['placements'].values()):
            raise ValueError('Clear or move this floor’s placements before removing it.')
        removed = data['floors'].pop(floor_id, None)
        # Keep immutable bytes locally for audit/recovery; unregistered assets are not exported.
        _save(config, path, data, 'remove floor', floor_id=floor_id, previous=removed)


def save_placement(config, path, run_id, value):
    path = _session_path(config, path)
    with session_lock(path):
        session, data = _edit(config, path)
        if run_id not in {step['run_id'] for step in session['steps']}:
            raise ValueError('Choose a point belonging to this survey.')
        clean = _placement(value, data['floors'])
        if clean['kind'] == 'floor':
            read_floor(config, path, clean['floor_id'])
        previous = data['placements'].get(run_id)
        clean.update(source='operator', placed_utc=utcnow_iso())
        data['placements'][run_id] = clean
        _save(config, path, data, 'place point', run_id=run_id, previous=previous, placement=clean)


def clear_placement(config, path, run_id):
    path = _session_path(config, path)
    with session_lock(path):
        _, data = _edit(config, path)
        previous = data['placements'].pop(run_id, None)
        _save(config, path, data, 'clear placement', run_id=run_id, previous=previous)


def calibrate_floor(config, path, floor_id, first, second, meters):
    path = _session_path(config, path)
    with session_lock(path):
        _, data = _edit(config, path)
        floor = data['floors'].get(_floor_id(floor_id))
        if floor is None or not isinstance(first, list) or not isinstance(second, list) or len(first) != 2 or len(second) != 2:
            raise ValueError('Choose two points on an imported floor.')
        a = [_number(v, 0, 1) for v in first]
        b = [_number(v, 0, 1) for v in second]
        distance = _number(meters, .001, 100000)
        pixels = math.hypot((a[0] - b[0]) * floor['width'], (a[1] - b[1]) * floor['height'])
        if pixels < 1:
            raise ValueError('Calibration points must be at least one image pixel apart.')
        floor['calibration'] = dict(first=a, second=b, meters=distance, meters_per_pixel=distance / pixels)
        _save(config, path, data, 'calibrate floor', floor_id=floor_id, calibration=floor['calibration'])


def export_spatial(config, path, destination):
    # Atomic metadata and immutable floor bytes allow a read-only snapshot while
    # collection already owns the survey lock. Never reacquire that lock here.
    data = load_spatial(config, path)
    if not data['floors'] and not data['placements'] and not data['history']:
        return
    for floor in data['floors']:
        read_floor(config, path, floor)
        shutil.copyfile(_root(config, path) / (floor + '.png'), Path(destination) / (floor + '.png'))
    atomic_json(Path(destination) / 'spatial.json', data)


def add_manual_features(model, spatial, steps):
    labels = {s['run_id']: s.get('label') or s['run_id'] for s in steps}
    count = 0
    for run_id, placement in spatial['placements'].items():
        if run_id not in labels or placement['kind'] != 'geographic':
            continue
        row = dict(id='manual-' + str(count), run_id=run_id, label=labels[run_id], observation_id='Operator placement',
                   quality=dict(qualified=False, label='Manual placement', reasons=['Operator supplied; not GPS evidence']),
                   manual=True, renderable=True, latitude_deg=placement['latitude'], longitude_deg=placement['longitude'],
                   source='operator', placed_utc=placement['placed_utc'])
        model['rows'].append(row)
        model['features']['features'].append(dict(type='Feature', id=row['id'],
            geometry=dict(type='Point', coordinates=[placement['longitude'], placement['latitude']]), properties=row))
        count += 1
    model['counts']['manual'] = count
