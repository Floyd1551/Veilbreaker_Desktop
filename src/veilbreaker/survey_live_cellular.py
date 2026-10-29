"""Conservative, read-only survey summaries of one live phone cell group."""
import math
import statistics


SIGNALS = {
    'LTE': {'rsrp': 'live_phone_lte_rsrp', 'rsrq': 'live_phone_lte_rsrq', 'rssi': 'live_phone_lte_rssi'},
    'NR': {'ss_rsrp': 'live_phone_nr_rsrp', 'ss_rsrq': 'live_phone_nr_rsrq', 'ss_sinr': 'live_phone_nr_sinr'},
}
MAX_SAMPLE_AGE_MS = 10_000


def reduce_live_cell_report(report):
    """Median fresh non-cached values; never merge distinct registered groups."""
    empty = {'metrics': {}, 'context': {}}
    if not isinstance(report, dict) or report.get('mode') != 'session':
        return dict(empty, warning='Live cellular session details are unavailable.')
    cells = report.get('cells')
    if not isinstance(cells, list) or len(cells) != 1:
        reason = 'multiple registered cell groups' if isinstance(cells, list) and len(cells) > 1 else 'no registered cell group'
        return dict(empty, warning=f'Live Android {reason}; no single survey signal was inferred. Review the Cellular report.')
    cell = cells[0]
    if not isinstance(cell, dict) or cell.get('radio') not in SIGNALS or not isinstance(cell.get('samples'), list):
        return dict(empty, warning='Live Android serving-cell evidence is incomplete; no survey signal was inferred.')
    identity = cell.get('identity') if isinstance(cell.get('identity'), dict) else {}
    identity = {key: identity[key] for key in ('mcc', 'mnc', 'cell_id', 'pci', 'earfcn', 'nrarfcn')
                if identity.get(key) is not None}
    metrics, context = {}, {}
    for signal, metric_key in SIGNALS[cell['radio']].items():
        retained = []
        for sample in cell['samples'][:1000]:
            if not isinstance(sample, dict) or sample.get('cached') is True:
                continue
            age = sample.get('age_ms')
            if type(age) not in (int, float) or not math.isfinite(age) or age < 0 or age > MAX_SAMPLE_AGE_MS:
                continue
            quantity = sample.get('signal', {}).get(signal, {}) if isinstance(sample.get('signal'), dict) else {}
            value = quantity.get('value') if isinstance(quantity, dict) else None
            if type(value) not in (int, float) or not math.isfinite(value) or not isinstance(sample.get('received_utc'), str):
                continue
            retained.append((value, sample['received_utc'], age))
        if not retained:
            continue
        metrics[metric_key] = statistics.median(row[0] for row in retained)
        context[metric_key] = {
            'sources': ['android_usb'], 'statistic': 'median' if len(retained) > 1 else 'single fresh sample',
            'sample_count': len(retained), 'window_start_utc': retained[0][1],
            'window_end_utc': retained[-1][1], 'max_sample_age_ms': max(row[2] for row in retained),
            'cell_identity': identity, 'radio': cell['radio'],
            'carrier_reported': cell.get('carrier'), 'band_reported': cell.get('band'),
            'collection_outcome': report.get('outcome'),
        }
    if not metrics:
        return dict(empty, warning='Live Android has no fresh uncached serving-cell signal samples for a survey value.')
    return {'metrics': metrics, 'context': context}
