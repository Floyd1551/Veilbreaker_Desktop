"""Conservative, read-only survey summaries of one live phone cell group."""
import math
import statistics
import hashlib
import json


SIGNALS = {
    'LTE': {'rsrp': 'live_phone_lte_rsrp', 'rsrq': 'live_phone_lte_rsrq', 'rssi': 'live_phone_lte_rssi'},
    'NR': {'ss_rsrp': 'live_phone_nr_rsrp', 'ss_rsrq': 'live_phone_nr_rsrq', 'ss_sinr': 'live_phone_nr_sinr'},
}
MAX_SAMPLE_AGE_MS = 10_000


def live_cell_groups(report):
    """Expose separately selectable groups with complete reported cell identity."""
    if not isinstance(report,dict) or report.get('mode') != 'session' or not isinstance(report.get('cells'),list):
        return []
    device=report.get('device')
    if not isinstance(device,dict) or not all(isinstance(device.get(k),str) and device[k].strip() for k in ('manufacturer','model')):
        return []
    receiver=f"{device['manufacturer']} {device['model']}"
    groups=[]
    for cell in report['cells'][:32]:
        if not isinstance(cell,dict) or cell.get('radio') not in SIGNALS:
            continue
        ident=cell.get('identity')
        sub=cell.get('subscription')
        if not isinstance(ident,dict) or not isinstance(sub,str) or not sub.strip():
            continue
        if any(not isinstance(ident.get(k),str) or not ident[k].isdigit() for k in ('mcc','mnc','cell_id')):
            continue
        tac_max=65535 if cell['radio']=='LTE' else 16777215
        cell_max=268435455 if cell['radio']=='LTE' else 68719476735
        if not (100 <= int(ident['mcc']) <= 999 and 0 <= int(ident['mnc']) <= 999 and 0 <= int(ident['cell_id']) <= cell_max):
            continue
        if type(ident.get('tac')) is not int or not 0 <= ident['tac'] <= tac_max:
            continue
        identity={k:ident.get(k) for k in ('mcc','mnc','tac','cell_id','pci','earfcn','nrarfcn')}
        canonical=json.dumps([cell['radio'],sub,identity,receiver],sort_keys=True,separators=(',',':'))
        key=hashlib.sha256(canonical.encode('utf-8')).hexdigest()
        reduced=reduce_live_cell_report(dict(report,cells=[cell],omitted=0))
        if not reduced['metrics']:
            continue
        for value in reduced['context'].values():
            value['subscription']=sub
            value['receiver_reported']=receiver
        channel_key='earfcn' if cell['radio']=='LTE' else 'nrarfcn'
        label=(f"{cell['radio']} · {ident['mcc']}/{ident['mnc']} · TAC {ident['tac']} · "
               f"cell {ident['cell_id']} · {sub} · PCI {ident.get('pci') if ident.get('pci') is not None else 'unknown'} · "
               f"{channel_key.upper()} {ident.get(channel_key) if ident.get(channel_key) is not None else 'unknown'} · reported model {receiver}")
        groups.append(dict(key=key,label=label,metrics=reduced['metrics'],context=reduced['context']))
    return groups


def reduce_live_cell_report(report):
    """Median fresh non-cached values; never merge distinct registered groups."""
    empty = {'metrics': {}, 'context': {}}
    if not isinstance(report, dict) or report.get('mode') != 'session':
        return dict(empty, warning='Live cellular session details are unavailable.')
    cells = report.get('cells')
    if type(report.get('omitted')) is int and report['omitted'] > 0:
        return dict(empty, warning=f"Live Android report omitted {report['omitted']} registered-cell entries; select an available cell group and review the Cellular report.")
    if not isinstance(cells, list) or len(cells) != 1:
        reason = 'multiple registered cell groups; select a cell group for a survey value' if isinstance(cells, list) and len(cells) > 1 else 'no registered cell group'
        return dict(empty, warning=f'Live Android {reason}. Review the Cellular report.')
    cell = cells[0]
    if not isinstance(cell, dict) or cell.get('radio') not in SIGNALS or not isinstance(cell.get('samples'), list):
        return dict(empty, warning='Live Android serving-cell evidence is incomplete; no survey signal was inferred.')
    identity = cell.get('identity') if isinstance(cell.get('identity'), dict) else {}
    identity = {key: identity[key] for key in ('mcc', 'mnc', 'tac', 'cell_id', 'pci', 'earfcn', 'nrarfcn')
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
