"""Read-only measured run metrics for spatial survey views."""
import math


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
}


def clean_metrics(values):
    if not isinstance(values, dict):
        return {}
    return {key: value for key, value in values.items()
            if key in METRICS and type(value) in (int, float) and math.isfinite(value)}


def available_metrics(model):
    return [key for key in METRICS
            if any(key in clean_metrics(values) for values in model.get('run_metrics', {}).values())]


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
