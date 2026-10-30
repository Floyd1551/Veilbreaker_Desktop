"""Read-only measured run metrics for spatial survey views."""
import math
from .display_labels import source_label

UNATTRIBUTED = '__unattributed__'


METRICS = {
    'rsrp': ('RSRP', 'dBm'),
    'rsrq': ('RSRQ', 'dB'),
    'sinr': ('SINR', 'dB'),
    'rssi': ('Cellular RSSI', 'dBm'),
    'wifi_rssi_dbm': ('Wi-Fi RSSI', 'dBm'),
    'wifi_channel_util_pct': ('Wi-Fi channel use', '%'),
    'download_mbps': ('Downlink', 'Mbps'),
    'upload_mbps': ('Uplink', 'Mbps'),
    'latency_ms': ('Latency', 'ms'),
    'jitter_ms': ('Jitter', 'ms'),
    'packet_loss_pct': ('Packet loss', '%'),
    'phone_lte_rsrp': ('Phone LTE RSRP', 'dBm'),
    'phone_lte_rsrq': ('Phone LTE RSRQ', 'dB'),
    'phone_lte_rssi': ('Phone LTE RSSI', 'dBm'),
    'phone_nr_rsrp': ('Phone NR SS-RSRP', 'dBm'),
    'phone_nr_rsrq': ('Phone NR SS-RSRQ', 'dB'),
    'phone_nr_sinr': ('Phone NR SS-SINR', 'dB'),
    'live_phone_lte_rsrp': ('Live phone LTE RSRP', 'dBm'),
    'live_phone_lte_rsrq': ('Live phone LTE RSRQ', 'dB'),
    'live_phone_lte_rssi': ('Live phone LTE RSSI', 'dBm'),
    'live_phone_nr_rsrp': ('Live phone NR SS-RSRP', 'dBm'),
    'live_phone_nr_rsrq': ('Live phone NR SS-RSRQ', 'dB'),
    'live_phone_nr_sinr': ('Live phone NR SS-SINR', 'dB'),
}


def clean_metrics(values):
    if not isinstance(values, dict):
        return {}
    return {key: value for key, value in values.items()
            if key in METRICS and type(value) in (int, float) and math.isfinite(value)}


def metric_provenance(key, collection):
    """Return only collector and receipt details persisted with this metric."""
    collection = collection if isinstance(collection, dict) else {}
    sources_map = collection.get('metric_sources')
    sources_map = sources_map if isinstance(sources_map, dict) else {}
    raw = sources_map.get(key)
    sources = [source for source in raw if isinstance(source, str)] if isinstance(raw, list) else []
    result = {'sources': list(dict.fromkeys(sources))}
    records = collection.get('collectors')
    if isinstance(records, list) and len(result['sources']) == 1:
        record = next((row for row in records if isinstance(row, dict) and row.get('source') == sources[0]), None)
        if record:
            if isinstance(record.get('started_utc'), str):
                result['started_utc'] = record['started_utc']
            duration = record.get('duration_s')
            if type(duration) in (int, float) and math.isfinite(duration) and duration >= 0:
                result['duration_s'] = duration
    if len(result['sources']) == 1 and result['sources'][0] in ('android_input', 'android_usb', 'android_import'):
        phone = collection.get('android')
        if isinstance(phone, dict):
            if isinstance(phone.get('received_utc'), str):
                result['received_utc'] = phone['received_utc']
            age = phone.get('age_ms')
            if type(age) in (int, float) and math.isfinite(age) and age >= 0:
                result['age_ms'] = age
    return result


def source_options(model, key):
    sources = []
    for run_id, metrics in model.get('run_metrics', {}).items():
        if key not in clean_metrics(metrics):
            continue
        context = model.get('run_context', {}).get(run_id, {}).get(key, {})
        named = context.get('sources') or [UNATTRIBUTED]
        for source in named:
            if source not in sources:
                sources.append(source)
    return sources


def source_matches(model, run_id, key, source):
    if source is None:
        return True
    if key not in clean_metrics(model.get('run_metrics', {}).get(run_id, {})):
        return False
    context = model.get('run_context', {}).get(run_id, {}).get(key, {})
    named = context.get('sources') or []
    return not named if source == UNATTRIBUTED else source in named


def provenance_label(context):
    context = context if isinstance(context, dict) else {}
    named = context.get('sources') or []
    source = ', '.join(source_label(item) for item in named) if named else 'Source unrecorded'
    if context.get('statistic') and context.get('window_start_utc'):
        identity = context.get('cell_identity') or {}
        cell = ', '.join(f'{key} {identity[key]}' for key in ('mcc', 'mnc', 'tac', 'cell_id', 'pci', 'earfcn', 'nrarfcn') if identity.get(key) is not None)
        band = context.get('band_reported')
        carrier = context.get('carrier_reported')
        return (f"{source} · {context['statistic']} of {context.get('sample_count', 0)} fresh uncached modem samples"
                f" · Receipt window {context['window_start_utc']} to {context.get('window_end_utc', '?')}"
                f" · Reported {context.get('radio', 'cell')} {cell or 'identity unavailable'}"
                + (f' · carrier {carrier}' if carrier else '') + (f' · band {band}' if band else '')
                + (f" · subscription {context['subscription']}" if context.get('subscription') else '')
                + (f" · reported receiver model {context['receiver_reported']}" if context.get('receiver_reported') else '')
                + ' · Reported model does not identify a physical device; confirm equipment comparability. Reported cell identity does not locate a physical tower or DAS antenna')
    if context.get('received_utc'):
        age = context.get('age_ms')
        return f"{source} · Phone observation received {context['received_utc']}" + (f" · sample age {age:g} ms" if age is not None else ' · sample age unrecorded')
    if context.get('started_utc'):
        duration = context.get('duration_s')
        return f"{source} · Collector started {context['started_utc']}" + (f" · duration {duration:g} s" if duration is not None else ' · duration unrecorded')
    return source + ' · Capture time unrecorded'


def available_metrics(model):
    return [key for key in METRICS
            if any(key in clean_metrics(values) for values in model.get('run_metrics', {}).values()) or
               any(key in clean_metrics(row.get('metrics')) for group in model.get('cell_groups', {}).values()
                   for row in group.get('runs', {}).values())]


def cell_group_options(model, metric_key):
    if not isinstance(metric_key,str) or not metric_key.startswith('live_phone_'):
        return []
    return [(key, group['label']) for key,group in model.get('cell_groups',{}).items()
            if any(metric_key in clean_metrics(row.get('metrics')) for row in group.get('runs',{}).values())]


def select_cell_group(model, selection):
    """Construct a transient view; never alter captured or persisted run metrics."""
    live_runs=sum(any(key.startswith('live_phone_') for key in values) for values in model.get('run_metrics',{}).values())
    suppress_automatic=selection is None and live_runs > 1
    if selection is None and not suppress_automatic:
        return model
    metrics={run:{k:v for k,v in values.items() if not k.startswith('live_phone_')}
             for run,values in model.get('run_metrics',{}).items()}
    context={run:{k:v for k,v in values.items() if not k.startswith('live_phone_')}
             for run,values in model.get('run_context',{}).items()}
    group=model.get('cell_groups',{}).get(selection,{}) if selection is not None else {}
    for run,row in group.get('runs',{}).items():
        metrics.setdefault(run,{}).update(clean_metrics(row.get('metrics')))
        context.setdefault(run,{}).update(row.get('context',{}))
    return dict(model,run_metrics=metrics,run_context=context,auto_live_suppressed=suppress_automatic)


def metric_scale(model, key):
    if key not in METRICS:
        raise ValueError('Unsupported survey metric.')
    values = [metrics[key] for metrics in model.get('run_metrics', {}).values()
              if key in metrics and type(metrics[key]) in (int, float) and math.isfinite(metrics[key])]
    if not values:
        return None
    return {'minimum': min(values), 'maximum': max(values), 'count': len(values),
            'label': METRICS[key][0], 'unit': METRICS[key][1]}


def point_metric(model, run_id, key, scale):
    if scale is None:
        return None
    value = model.get('run_metrics', {}).get(run_id, {}).get(key)
    if type(value) not in (int, float) or not math.isfinite(value):
        return None
    low, high = scale['minimum'], scale['maximum']
    if high == low:
        color = '#52b7ca'
    else:
        ratio = max(0.0, min(1.0, (value - low) / (high - low)))
        a, b = (72, 119, 202), (245, 191, 93)
        color = '#%02x%02x%02x' % tuple(round(x + (y - x) * ratio) for x, y in zip(a, b))
    return {'value': value, 'color': color, 'unit': scale['unit'], 'label': scale['label']}


def floor_measurements(steps, placements, floor_id, metric_key=None, source_filter=None, run_context=None):
    """Return positioned scans and a color scale scoped to one floor only."""
    positioned = []
    run_metrics = {}
    for index, step in enumerate(steps, 1):
        run_id = step['run_id']
        position = placements.get(run_id)
        if not position or position.get('kind') != 'floor' or position.get('floor_id') != floor_id:
            continue
        positioned.append({'run_id': run_id, 'scan_label': step.get('label') or run_id,
                           'number': index, 'x': position['x'], 'y': position['y'],
                           'placed_utc': position.get('placed_utc')})
        run_metrics[run_id] = clean_metrics(step.get('metrics'))
    model = {'run_metrics': run_metrics, 'run_context': run_context or {}}
    if source_filter is not None:
        positioned = [marker for marker in positioned if source_matches(model, marker['run_id'], metric_key, source_filter)]
        run_metrics = {run_id: values for run_id, values in run_metrics.items()
                       if source_matches(model, run_id, metric_key, source_filter)}
        model['run_metrics'] = run_metrics
    scale = metric_scale(model, metric_key) if metric_key else None
    for marker in positioned:
        marker['metric'] = point_metric(model, marker['run_id'], metric_key, scale) if metric_key else None
    return positioned, scale
