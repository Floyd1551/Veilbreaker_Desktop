"""Readable, offline cellular evidence with separate receiver/cell series."""
import html
import json
import statistics
from .android_capture import validate_capture, SIGNALS

LABELS = {'rsrp':'RSRP', 'rsrq':'RSRQ', 'rssi':'RSSI', 'rssnr':'LTE RSSNR (reported)',
          'ss_rsrp':'NR SS-RSRP', 'ss_rsrq':'NR SS-RSRQ', 'ss_sinr':'NR SS-SINR',
          'csi_rsrp':'NR CSI-RSRP', 'csi_rsrq':'NR CSI-RSRQ', 'csi_sinr':'NR CSI-SINR',
          'cqi':'CQI', 'timing_advance':'Timing advance'}
MISSING = 'Not exposed'


def build_report(envelope):
    from .capture_reasoning import cellular_patterns
    from .cell_visibility import build_visibility
    validate_capture(envelope)
    subscriptions = {s['key']: s for s in envelope['subscriptions']}
    groups, previous, seen = {}, {}, set()
    changes = []
    repeated = unknown = neighbors = omitted = 0
    observations = envelope['observations']
    start = observations[0]['elapsed_realtime_ms'] if observations else 0
    for obs in observations:
        registered = set()
        for cell in obs['cells']:
            if cell.get('registered') is not True:
                neighbors += 1; continue
            identity = cell['identity']
            # Bandwidth/band metadata availability can vary without changing the cell.
            key = json.dumps([obs['subscription_key'], cell['radio'], {k:identity.get(k) for k in ('cell_id','pci','tac','earfcn','nrarfcn','mcc','mnc')}], sort_keys=True)
            registered.add(key)
            if key not in groups and len(groups) >= 32:
                omitted += 1; continue
            sub = subscriptions[obs['subscription_key']]
            carrier = sub.get('network_operator') or identity.get('operator_alpha_long') or MISSING
            band = ', '.join(str(b) for b in (identity.get('bands') or []))
            group = groups.setdefault(key, dict(radio=cell['radio'], subscription=obs['subscription_key'],
                carrier=str(carrier), sim_carrier=str(sub.get('sim_carrier') or MISSING),
                band=(cell['radio'] + ' ' + band + ' (reported)') if band else MISSING,
                identity=dict(identity), roles=[], samples=[], signals={}))
            # Keep the latest exposed metadata without losing earlier evidence to nulls.
            group['identity'].update({k:v for k,v in identity.items() if v is not None and v != [] and v != ''})
            if band:
                group['band'] = cell['radio'] + ' ' + band + ' (reported)'
            if carrier != MISSING:
                group['carrier'] = str(carrier)
            role = cell['connection_status']
            if role not in group['roles']: group['roles'].append(role)
            age = cell.get('age_ms')
            cached = False
            if age is None: unknown += 1
            else:
                stamp = (key, obs['elapsed_realtime_ms'] - age)
                cached = stamp in seen; repeated += int(cached); seen.add(stamp)
            group['samples'].append(dict(seconds=(obs['elapsed_realtime_ms']-start)/1000,
                received_utc=obs['received_utc'], age_ms=age, cached=cached,
                signal={k:v for k,v in cell['signal'].items() if k in SIGNALS}))
        subkey = obs['subscription_key']
        if subkey in previous and registered != previous[subkey]:
            changes.append(dict(received_utc=obs['received_utc'], subscription=subkey,
                                detail='Registered-cell set changed (not proof of a handover).'))
        previous[subkey] = registered
    for group in groups.values():
        for name in SIGNALS:
            values = [sample['signal'][name]['value'] for sample in group['samples'] if sample['signal'].get(name, {}).get('value') is not None]
            if values:
                group['signals'][name] = dict(last=values[-1], min=min(values), median=statistics.median(values), max=max(values),
                    change=values[-1]-values[0], unit=SIGNALS[name][0], count=len(values))
    return dict(device=envelope['device'], mode=envelope['collection']['mode'], outcome=envelope['collection']['outcome'],
                started_utc=envelope['collection']['started_utc'], ended_utc=envelope['collection']['ended_utc'],
                observations=len(observations), cells=list(groups.values()), changes=changes,
                repeated_samples=repeated, unknown_age_samples=unknown, neighbor_observations=neighbors, omitted=omitted,
                capture_diagnostics=cellular_patterns(envelope), visibility=build_visibility(envelope))


def interpretation(name, value):
    if value is None: return MISSING
    if 'rsrp' in name: return 'Strong' if value >= -90 else 'Moderate' if value >= -100 else 'Weak' if value >= -110 else 'Very weak'
    if 'rsrq' in name: return 'Good' if value >= -10 else 'Moderate' if value >= -15 else 'Poor'
    if 'sinr' in name or name == 'rssnr': return 'Good' if value >= 13 else 'Marginal' if value >= 0 else 'Poor'
    return 'Reported value; context dependent'


def trend(samples, metric):
    from .sdr_visuals import png
    values = [s['signal'].get(metric, {}).get('value') for s in samples]
    present = [v for v in values if v is not None]
    if len(present) < 2: return ''
    width, height = 720, 160
    pixels = bytearray([239,244,248] * width * height)
    low, high = min(present)-2, max(present)+2
    t0, t1 = samples[0]['seconds'], samples[-1]['seconds']
    def dot(x,y,color):
        if 0 <= x < width and 0 <= y < height: pixels[(y*width+x)*3:(y*width+x)*3+3] = bytes(color)
    for y in (12,80,147):
        for x in range(12,708): dot(x,y,(201,211,221))
    prior = None
    for sample, value in zip(samples, values):
        if value is None: prior = None; continue
        x = int(12 + 695*(sample['seconds']-t0)/max(t1-t0,.001))
        y = int(147 - 135*(value-low)/(high-low))
        color = (117,126,137) if sample['cached'] else (0,124,110)
        if prior:
            px,py = prior; steps=max(abs(x-px),abs(y-py),1)
            for i in range(steps+1): dot(round(px+(x-px)*i/steps),round(py+(y-py)*i/steps),color)
        for dx in range(-2,3):
            for dy in range(-2,3): dot(x+dx,y+dy,color)
        prior=(x,y)
    label = html.escape(LABELS.get(metric,metric))
    return f'<p><b>{label}</b> · scale {low:g} to {high:g} {SIGNALS[metric][0]}</p><img width="720" height="160" alt="{label} over receipt time" src="{png(pixels,width,height)}"><p>{t0:g} to {t1:g} seconds from first receipt. Gray marks repeated samples; gaps mean unavailable readings.</p>'


def report_html(report, fragment=False):
    esc = lambda value: html.escape(str(value if value is not None else MISSING))
    parts = [] if fragment else ['<!doctype html><html><head><meta charset="utf-8"></head><body>']
    parts += ['<h2>Cellular field measurements</h2>',
              f"<p><b>{esc(report['device']['manufacturer'])} {esc(report['device']['model'])}</b> · {esc(report['mode'])} · {esc(report['outcome'])}<br>{esc(report['started_utc'])} to {esc(report['ended_utc'])}</p>",
              f"<p>{report['observations']} observations · {report['repeated_samples']} repeated registered-cell samples · {report['unknown_age_samples']} unknown sample ages · {report['neighbor_observations']} neighbor/reference entries.</p>",
              '<p>Cell IDs identify reported cells, not physical tower locations. Carrier is the reported network name; SIM provider may differ. Modem-reported bands and channel-derived candidates are labelled separately. Signal labels are broad RF guidance, not a throughput diagnosis.</p>']
    if report.get('visibility'):
        from .cell_visibility import visibility_html
        parts.append(visibility_html(report['visibility']))
    if report.get('capture_diagnostics'):
        from .capture_reasoning import patterns_html
        parts.append(patterns_html(report['capture_diagnostics']))
    if not report['cells']: parts.append('<p>No registered cells were exposed.</p>')
    for index, cell in enumerate(report['cells'],1):
        ident = cell['identity']
        rows = [('Network / carrier',cell['carrier']), ('SIM provider',cell['sim_carrier']), ('Subscription',cell['subscription']),
                ('Radio / band',cell['band'] if cell['band'] != MISSING else cell['radio']+' / '+MISSING),
                ('MCC / MNC',str(ident.get('mcc') or MISSING)+' / '+str(ident.get('mnc') or MISSING)),
                ('Cell ID',ident.get('cell_id')), ('PCI',ident.get('pci')), ('TAC',ident.get('tac')),
                ('EARFCN' if cell['radio']=='LTE' else 'NR-ARFCN',ident.get('earfcn' if cell['radio']=='LTE' else 'nrarfcn')),
                ('Registered role',', '.join(cell['roles'])), ('Samples',len(cell['samples'])),
                ('Latest sample age at receipt', str(cell['samples'][-1]['age_ms'])+' ms' if cell['samples'][-1]['age_ms'] is not None else MISSING)]
        parts.append(f'<h3>Serving cell {index} — {esc(cell["radio"])}</h3><table border="1" cellspacing="0" cellpadding="7">')
        parts.extend('<tr><th>'+esc(k)+'</th><td>'+esc(v)+'</td></tr>' for k,v in rows); parts.append('</table>')
        parts.append('<h4>Signal quality</h4><table border="1" cellspacing="0" cellpadding="7"><tr><th>Measurement</th><th>Latest</th><th>Min / median / max</th><th>First-to-last change</th><th>Interpretation</th></tr>')
        names = ['rsrp','rsrq','rssi','rssnr','cqi','timing_advance'] if cell['radio']=='LTE' else ['ss_rsrp','ss_rsrq','ss_sinr','csi_rsrp','csi_rsrq','csi_sinr']
        for name in names:
            stats = cell['signals'].get(name)
            latest = cell['samples'][-1]['signal'].get(name,{}).get('value')
            last = f"{latest:g} {SIGNALS[name][0]}" if latest is not None else MISSING
            spread = f"{stats['min']:g} / {stats['median']:g} / {stats['max']:g} {stats['unit']}" if stats else MISSING
            change = f"{stats['change']:+g} {stats['unit']}" if stats and stats['count'] > 1 else 'Single sample / unavailable'
            parts.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in (LABELS[name],last,spread,change,interpretation(name,latest)))+'</tr>')
        parts.append('</table>')
        if index <= 8:
            parts.extend(trend(cell['samples'], name) for name in names if name not in ('cqi','timing_advance'))
        parts.append('<p>Field follow-up: repeat the same position and orientation; compare per-cell signal quality and sample freshness before attributing changes to coverage. Weak RSRQ/SINR warrants checking interference or load; RF alone cannot establish the cause.</p>')
    parts.append('<h3>Registered-cell changes</h3>')
    parts.extend('<p>'+esc(c['received_utc'])+' · '+esc(c['subscription'])+': '+esc(c['detail'])+'</p>' for c in report['changes'])
    if not report['changes']: parts.append('<p>No registered-cell set change observed.</p>')
    if report['omitted']: parts.append('<p>Display limited to 32 cell identities; complete observations remain in raw evidence.</p>')
    if len(report['cells'])>8: parts.append('<p>Trend graphs limited to the first eight cell identities; tables cover all displayed cells.</p>')
    if not fragment: parts.append('</body></html>')
    return ''.join(parts)
