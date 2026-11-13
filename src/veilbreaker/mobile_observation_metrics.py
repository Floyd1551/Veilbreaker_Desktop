"""Cell-scoped mobile measurements keyed by exact map feature, never run averages.

The caller must select one capture and one complete reported cell group. These
relative colors are observed values, not coverage predictions or quality grades.
"""
import json
import math
import copy
from collections import Counter

from .mobile_survey_metrics import _SHARED_RECEIPT_VERSIONS
from .survey_metrics import METRICS, clean_metrics, metric_scale, point_metric

_KEYS = ('phone_lte_rsrp', 'phone_lte_rsrq', 'phone_lte_rssi',
         'phone_nr_rsrp', 'phone_nr_rsrq', 'phone_nr_sinr')


def _bounded_number(value, low, high):
    try:
        return type(value) in (int, float) and math.isfinite(value) and low <= value <= high
    except OverflowError:
        return False


def _candidates(model, run_id, metric_key):
    if not isinstance(run_id, str) or not run_id or metric_key not in _KEYS or not isinstance(model, dict):
        return []
    rows = model.get('rows', [])
    features = model.get('features', {}).get('features', []) if isinstance(model.get('features'), dict) else []
    if not isinstance(rows, list) or not isinstance(features, list):
        return []
    feature_counts = Counter(f.get('id') for f in features if isinstance(f, dict) and isinstance(f.get('id'), str))
    feature_by_id = {f['id']: f for f in features if isinstance(f, dict) and isinstance(f.get('id'), str)}
    row_counts = Counter(r.get('id') for r in rows if isinstance(r, dict) and isinstance(r.get('id'), str))
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        feature_id = row.get('id')
        if (not isinstance(feature_id, str) or row_counts[feature_id] != 1 or feature_counts[feature_id] != 1 or
            row.get('run_id') != run_id or row.get('source_kind') != 'mobile_survey_capture' or
            row.get('manual') or row.get('renderable') is not True or row.get('mock') is not False or
            not isinstance(row.get('quality'), dict) or row['quality'].get('qualified') is not True):
            continue
        feature = feature_by_id[feature_id]
        props, geometry = feature.get('properties'), feature.get('geometry')
        lat, lon = row.get('latitude_deg'), row.get('longitude_deg')
        if (feature.get('type') != 'Feature' or not isinstance(props, dict) or not isinstance(geometry, dict) or
            geometry.get('type') != 'Point' or not _bounded_number(lat, -85.05112878, 85.05112878) or
            not _bounded_number(lon, -180, 180) or geometry.get('coordinates') != [lon, lat] or
            any(props.get(k) != row.get(k) for k in ('id', 'run_id', 'observation_id', 'mobile_capture_id',
                'source_kind', 'manual', 'renderable', 'mock', 'quality', 'latitude_deg', 'longitude_deg',
                'fix_age_ms', 'received_utc', 'mobile_aligned'))):
            continue
        aligned = row.get('mobile_aligned')
        if not isinstance(aligned, dict):
            continue
        metrics = clean_metrics(aligned.get('metrics'))
        contexts = aligned.get('context')
        context = contexts.get(metric_key) if isinstance(contexts, dict) else None
        if metric_key not in metrics or not isinstance(context, dict):
            continue
        radio = context.get('radio')
        expected_radio = 'LTE' if metric_key.startswith('phone_lte_') else 'NR'
        age, fix_age, offset = (context.get(k) for k in ('age_ms', 'fix_age_ms', 'location_after_modem_ms'))
        if (radio != expected_radio or context.get('companion_version') not in _SHARED_RECEIPT_VERSIONS or
            not isinstance(row.get('observation_id'), str) or not row['observation_id'] or
            not isinstance(row.get('received_utc'), str) or not row['received_utc'] or
            context.get('observation_id') != row.get('observation_id') or
            context.get('received_utc') != row.get('received_utc') or
            not _bounded_number(age, 0, 10_000) or not _bounded_number(fix_age, 0, 10_000) or
            not _bounded_number(offset, -2000, 2000) or abs((age - fix_age) - offset) > 1e-6 or
            row.get('fix_age_ms') != fix_age):
            continue
        identity = context.get('cell_identity')
        capture, subscription = row.get('mobile_capture_id'), context.get('subscription')
        if (not isinstance(identity, dict) or not isinstance(capture, str) or not capture or len(capture) > 128 or
            not isinstance(subscription, str) or not subscription or len(subscription) > 1000):
            continue
        mcc, mnc, cell = (identity.get(k) for k in ('mcc', 'mnc', 'cell_id'))
        channel_key = 'earfcn' if radio == 'LTE' else 'nrarfcn'
        channel = identity.get(channel_key)
        if (not isinstance(mcc, str) or len(mcc) != 3 or not mcc.isascii() or not mcc.isdigit() or
            not isinstance(mnc, str) or len(mnc) not in (2, 3) or not mnc.isascii() or not mnc.isdigit() or
            not isinstance(cell, str) or not cell.isascii() or not cell.isdigit() or len(cell) > 20 or
            type(channel) is not int or not 0 <= channel < 2147483647):
            continue
        tac, pci = identity.get('tac'), identity.get('pci')
        if any(value is not None and (type(value) is not int or not 0 <= value < 2147483647) for value in (tac, pci)):
            continue
        group = json.dumps([capture, radio, subscription, mcc, mnc, cell, channel, tac, pci], separators=(',', ':'))
        label = f'{radio} · {mcc}/{mnc} · cell {cell} · {channel_key.upper()} {channel} · {subscription} · capture {capture}'
        if tac is not None: label += f' · TAC {tac}'
        if pci is not None: label += f' · PCI {pci}'
        result.append((feature_id, metrics[metric_key], context, group, label))
    return result


def available_observation_metrics(model, run_id):
    """Offer only metrics with at least one groupable, positioned observation."""
    return [key for key in _KEYS if _candidates(model, run_id, key)]


def observation_cell_groups(model, run_id, metric_key):
    """Return selectable exact reported-cell groups within one capture."""
    groups = {}
    for _, _, _, key, label in _candidates(model, run_id, metric_key):
        groups.setdefault(key, label)
    return list(groups.items())


def observation_metric_series(model, run_id, metric_key, group, *, visible_ids=None):
    """Return a relative scale and feature-ID values for one explicitly selected group.

    ``visible_ids`` limits scale and values to the rendered set; manual pins and
    missing or ambiguous identity remain absent. No source data is mutated.
    """
    empty = {'scale': None, 'points': {}}
    if not isinstance(group, str) or not group or metric_key not in METRICS:
        return empty
    if visible_ids is not None:
        try: visible_ids = set(visible_ids)
        except TypeError: return empty
    selected = [(fid, value, context) for fid, value, context, candidate, _ in _candidates(model, run_id, metric_key)
                if candidate == group and (visible_ids is None or fid in visible_ids)]
    if not selected:
        return empty
    scoped = {'run_metrics': {fid: {metric_key: value} for fid, value, _ in selected}}
    scale = metric_scale(scoped, metric_key)
    points = {fid: dict(point_metric(scoped, fid, metric_key, scale), context=copy.deepcopy(context))
              for fid, _, context in selected}
    return {'scale': scale, 'points': points}
