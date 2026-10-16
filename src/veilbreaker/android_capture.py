"""Versioned public-API Android captures, independent of Android tooling."""
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import uuid

MAX_BYTES = 16 * 1024 * 1024
REASONS = {'not_reported', 'unsupported_api', 'permission_denied', 'timeout', 'unknown'}
OUTCOMES = {'complete', 'partial', 'cancelled', 'failed'}
SIGNALS = {'rsrp': ('dBm', -160, -20), 'rsrq': ('dB', -50, 20), 'rssi': ('dBm', -160, 0),
           'rssnr': ('dB', -30, 50), 'cqi': ('index', 0, 15), 'timing_advance': ('index', 0, 1282),
           'ss_rsrp': ('dBm', -160, -20), 'ss_rsrq': ('dB', -50, 30), 'ss_sinr': ('dB', -30, 60),
           'csi_rsrp': ('dBm', -160, -20), 'csi_rsrq': ('dB', -50, 30), 'csi_sinr': ('dB', -30, 60)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def string(value):
    return isinstance(value, str) and 0 < len(value) <= 1000


def number(value, low, high):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def utc(value):
    require(string(value), 'Missing UTC timestamp')
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(stamp.utcoffset() is not None and stamp.utcoffset().total_seconds() == 0, 'Timestamp must be UTC')
    except (ValueError, OverflowError) as exc:
        raise ValueError('Invalid UTC timestamp') from exc


def finite_tree(value):
    if isinstance(value, float):
        require(math.isfinite(value), 'Nonfinite JSON number')
    elif isinstance(value, dict):
        for item in value.values(): finite_tree(item)
    elif isinstance(value, list):
        for item in value: finite_tree(item)


def validate_location(location):
    require(isinstance(location, dict), 'Location must be an object')
    require(location.get('status') in {'available','unavailable','permission_denied','disabled'}, 'Invalid location status')
    require(location.get('source') in {'phone','external_receiver','imported'}, 'Invalid location source')
    require(string(location.get('provider')), 'Location provider required')
    if location.get('status') == 'available':
        utc(location.get('fix_utc'))
        for key, low, high in [('latitude_deg',-90,90),('longitude_deg',-180,180),('horizontal_accuracy_m',0,1e9)]:
            require(number(location.get(key),low,high), f'Invalid location {key}')
    else:
        require(all(location.get(k) is None for k in ('latitude_deg','longitude_deg','altitude_m')), 'Unavailable location cannot contain coordinates')
    for key in ('vertical_accuracy_m','speed_mps','fix_age_ms'):
        if location.get(key) is not None: require(number(location[key],0,1e15), f'Invalid {key}')
    if location.get('bearing_deg') is not None: require(number(location['bearing_deg'],0,359.999999999), 'Invalid bearing')
    if location.get('altitude_m') is not None:
        require(number(location['altitude_m'],-1e6,1e7), 'Invalid altitude')
        require(location.get('altitude_reference') in {'ellipsoid','mean_sea_level','unknown'}, 'Altitude reference required')
    if location.get('mock') is not None: require(type(location['mock']) is bool, 'Invalid mock flag')


def validate_capture(value):
    try:
        _validate_capture(value)
    except (TypeError, KeyError, OverflowError, RecursionError) as exc:
        raise ValueError('Invalid Android capture field type or nesting') from exc


def _validate_capture(value):
    require(isinstance(value,dict), 'Capture must be an object')
    finite_tree(value)
    require(value.get('format') == 'veilbreaker.android.cellular' and type(value.get('schema_version')) is int and value['schema_version'] == 1, 'Unsupported Android capture format/version')
    try: uuid.UUID(value.get('capture_id',''))
    except (ValueError, TypeError, AttributeError) as exc: raise ValueError('Invalid capture UUID') from exc
    utc(value.get('created_utc'))
    device = value.get('device')
    require(isinstance(device,dict), 'Device metadata required')
    for key in ('manufacturer','model','android_version','companion_version'):
        require(string(device.get(key)), f'Device {key} required')
    require(type(device.get('api_level')) is int and device['api_level'] >= 29, 'Android API 29 or newer required')
    collection = value.get('collection')
    require(isinstance(collection,dict) and collection.get('outcome') in OUTCOMES, 'Invalid collection outcome')
    require(collection.get('mode') in {'snapshot','session'}, 'Invalid collection mode')
    utc(collection.get('started_utc')); utc(collection.get('ended_utc'))
    require(isinstance(collection.get('permissions'),dict) and isinstance(collection.get('notes'),list), 'Collection permissions/notes required')
    subscriptions = value.get('subscriptions')
    if 'inputs' in collection:
        require(isinstance(collection['inputs'], dict), 'Invalid input selection')
        for key in ('cellular', 'location'):
            require(type(collection['inputs'].get(key)) is bool, 'Invalid input selection')
    require(isinstance(subscriptions,list) and len(subscriptions) <= 32, 'Invalid subscriptions')
    keys = []
    for sub in subscriptions:
        require(isinstance(sub,dict) and string(sub.get('key')), 'Invalid subscription key')
        keys.append(sub['key'])
    require(len(keys) == len(set(keys)), 'Duplicate subscription keys')
    observations = value.get('observations')
    require(isinstance(observations,list) and len(observations) <= 1000, 'Maximum 1000 observations')
    ids = set()
    for obs in observations:
        require(isinstance(obs,dict) and string(obs.get('observation_id')), 'Invalid observation ID')
        require(obs['observation_id'] not in ids, 'Duplicate observation ID'); ids.add(obs['observation_id'])
        require(obs.get('subscription_key') in keys, 'Unknown subscription reference')
        utc(obs.get('received_utc'))
        require(number(obs.get('elapsed_realtime_ms'),0,1e15), 'Invalid receipt monotonic timestamp')
        require(obs.get('outcome') in OUTCOMES, 'Invalid observation outcome')
        if obs.get('location') is not None: validate_location(obs['location'])
        cells = obs.get('cells')
        require(isinstance(cells,list) and len(cells) <= 256, 'Maximum 256 cells per observation')
        for cell in cells:
            require(isinstance(cell,dict) and string(cell.get('radio')), 'Invalid cell')
            require(cell.get('registered') is None or type(cell['registered']) is bool, 'Invalid registered flag')
            require(cell.get('connection_status') in {'primary','secondary','none','unknown'}, 'Invalid cell role')
            age = cell.get('age_ms')
            require(age is None or number(age,0,1e15), 'Invalid modem sample age')
            require(isinstance(cell.get('identity'),dict) and isinstance(cell.get('signal'),dict), 'Cell identity/signal objects required')
            identity = cell['identity']
            for key in ('pci','earfcn','nrarfcn','bandwidth_khz','tac'):
                if identity.get(key) is not None: require(type(identity[key]) is int and 0 <= identity[key] < 2147483647, f'Invalid {key}')
            for key in ('cell_id','mcc','mnc'):
                if identity.get(key) is not None: require(string(identity[key]), f'{key} must be a string')
            if identity.get('bands') is not None:
                require(isinstance(identity['bands'],list) and len(identity['bands']) <= 64 and all(type(b) is int and 0 < b < 1024 for b in identity['bands']), 'Invalid bands')
            for key, quantity in cell['signal'].items():
                if key not in SIGNALS: continue
                unit, low, high = SIGNALS[key]
                require(isinstance(quantity,dict) and quantity.get('unit') == unit, f'Invalid {key} unit/object')
                if quantity.get('value') is None:
                    require(quantity.get('reason') in REASONS, f'Missing reason for {key}')
                else: require(number(quantity['value'],low,high), f'Invalid {key} value; use null for unavailable')


def load_capture(path):
    with Path(path).open('rb') as stream: raw = stream.read(MAX_BYTES+1)
    require(len(raw) <= MAX_BYTES, 'Android capture exceeds 16 MiB')
    def unique(pairs):
        result = {}
        for key, item in pairs:
            require(key not in result, 'Duplicate JSON key'); result[key] = item
        return result
    try:
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique)
        validate_capture(value)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid or excessively nested Android JSON') from exc
    return {'envelope':value, 'raw_bytes':raw, 'sha256':hashlib.sha256(raw).hexdigest()}


def normalize_selection(envelope, observation_id, cell_index):
    validate_capture(envelope)
    obs = next((o for o in envelope['observations'] if o['observation_id'] == observation_id), None)
    require(obs is not None and type(cell_index) is int and 0 <= cell_index < len(obs['cells']), 'Select a valid observation and cell')
    cell = obs['cells'][cell_index]
    require(cell.get('registered') is True, 'Select an explicitly registered serving cell')
    require(cell['radio'] in {'LTE','NR'}, 'Only LTE/NR serving cells support analysis in this version')
    mapping = {'rsrp':'lte_rsrp','rsrq':'lte_rsrq','rssi':'lte_rssi'} if cell['radio'] == 'LTE' else {'ss_rsrp':'nr_rsrp','ss_rsrq':'nr_rsrq','ss_sinr':'nr_sinr'}
    metrics = {'android_capture_id':envelope['capture_id'], 'android_observation_id':observation_id,
               'android_source':'public_api_import', 'android_radio':cell['radio'], 'modem_registered':True}
    fields = {}
    for source, target in mapping.items():
        val = cell['signal'].get(source,{}).get('value')
        if val is not None:
            metrics[target] = val; fields[target] = f'cells[{cell_index}].signal.{source}'
            alias = target.split('_', 1)[1]
            metrics[alias] = val
            fields[alias] = fields[target]
    # Other signal quantities retain their physical meaning in a separate namespace.
    for key in SIGNALS:
        val = cell['signal'].get(key,{}).get('value')
        if val is not None: metrics['android_'+key] = val
    prefix = 'lte_' if cell['radio'] == 'LTE' else 'nr_'
    for key in ('pci','earfcn','nrarfcn'):
        if cell['identity'].get(key) is not None: metrics[prefix+key] = cell['identity'][key]
    notes = [f'Android imported observation, not desktop acquisition. Device: {envelope["device"]["manufacturer"]} {envelope["device"]["model"]}.',
             f'Received: {obs["received_utc"]}; sample age at phone receipt: {cell.get("age_ms")} ms (None means unknown).',
             f'Source collection: {envelope["collection"]["outcome"]}; observation: {obs["outcome"]}. No other cells, subscriptions or host measurements were merged.']
    if cell['connection_status'] in {'none', 'unknown'}:
        notes.append(f"Android reports registered=true with connection status {cell['connection_status']}; primary/secondary role is not confirmed. Selection uses explicit registration only.")
    return {'metrics':metrics, 'notes':notes, 'provenance':{'capture_id':envelope['capture_id'], 'observation_id':observation_id,
            'cell_index':cell_index, 'registered':True, 'connection_status':cell['connection_status'], 'subscription_key':obs['subscription_key'], 'device':envelope['device'],
            'received_utc':obs['received_utc'], 'age_ms':cell.get('age_ms'), 'location':obs.get('location'),
            'collection_outcome':envelope['collection']['outcome'], 'observation_outcome':obs['outcome'], 'field_mapping':fields}}
