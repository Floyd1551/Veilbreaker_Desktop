"""Reported serving/neighbor inventory; no claims of exhaustive modem scanning."""
from functools import lru_cache
from importlib.resources import files
from html import escape
import json


@lru_cache(maxsize=1)
def channel_plan():
    return json.loads(files('veilbreaker').joinpath('assets/cellular/channel-bands.json').read_text(encoding='utf-8'))


def band_details(radio, identity):
    reported = sorted(set(identity.get('bands') or []))
    channel = identity.get('earfcn' if radio == 'LTE' else 'nrarfcn')
    candidates = []
    if radio in ('LTE', 'NR') and type(channel) is int and channel >= 0:
        candidates = sorted({r['band'] for r in channel_plan()['ranges']
                             if r['radio'] == radio and r['min'] <= channel <= r['max']})
    bands = reported or candidates
    source = 'modem reported' if reported else ('channel-derived candidates' if candidates else 'not exposed')
    prefix = 'n' if radio == 'NR' else 'B'
    return dict(bands=bands, source=source, channel=channel,
                label=(', '.join(prefix+str(b) for b in bands) + ' ('+source+')') if bands else 'Not exposed')


def cell_role(cell):
    role = cell['connection_status']
    if cell.get('registered') is True:
        return {'primary':'Primary serving', 'secondary':'Secondary serving'}.get(role, 'Registered; role not exposed')
    if role in ('primary', 'secondary'):
        return 'Conflicting serving flags'
    return 'Neighbor' if cell.get('registered') is False else 'Role not exposed'


def build_visibility(envelope):
    from .android_capture import validate_capture
    validate_capture(envelope)
    observations = envelope['observations']
    latest = {}
    for obs in observations:
        sub = obs['subscription_key']
        if sub not in latest or obs['elapsed_realtime_ms'] >= latest[sub]['elapsed_realtime_ms']:
            latest[sub] = obs
    subscriptions = {s['key']:s for s in envelope['subscriptions']}
    groups, inventory, stamps = {}, {}, set()
    omitted = 0
    for obs in observations:
        sub = obs['subscription_key']
        for index, cell in enumerate(obs['cells']):
            identity = cell['identity']; role = cell_role(cell); radio = cell['radio']
            signature = [identity.get(k) for k in ('mcc','mnc','cell_id','pci','earfcn','nrarfcn')]
            full_id = all(identity.get(k) is not None for k in ('mcc','mnc','cell_id'))
            channel_id = identity.get('pci') is not None and (identity.get('earfcn') is not None or identity.get('nrarfcn') is not None)
            if not full_id and not channel_id: signature += [obs['observation_id'], index]
            key = json.dumps([sub, radio, signature, role])
            current = obs['observation_id'] == latest[sub]['observation_id']
            if key not in groups and len(groups) >= 1024:
                victim = next((k for k,r in groups.items() if current and not r['latest']), None)
                if victim is None and current and cell.get('registered') is True:
                    victim = next((k for k,r in groups.items() if r['role'] in ('Neighbor','Role not exposed','Conflicting serving flags')), None)
                if victim is None:
                    omitted += 1; continue
                omitted += groups.pop(victim)['observations']
            band = band_details(radio, identity)
            age = cell.get('age_ms'); stamp = (sub, radio, json.dumps(signature), obs['elapsed_realtime_ms']-age) if age is not None else None
            cached = stamp in stamps if stamp else False
            if stamp: stamps.add(stamp)
            freshness = 'unknown age' if age is None else ('old sample' if age > 10000 else ('cached sample' if cached else 'recent sample'))
            carrier = identity.get('operator_alpha_long')
            if not carrier and cell.get('registered') is True:
                carrier = subscriptions[sub].get('network_operator')
            row = dict(subscription=sub, radio=radio, role=role, identity=dict(identity), band=band,
                carrier=carrier or 'Not exposed', signal=cell['signal'], age_ms=age, freshness=freshness,
                last_seen=obs['received_utc'], latest=current, elapsed_ms=obs['elapsed_realtime_ms'])
            old = groups.get(key)
            row['observations'] = (old['observations'] if old else 0) + 1
            if not old or row['elapsed_ms'] >= old['elapsed_ms']: groups[key] = row
            else: old['observations'] += 1
            for number in band['bands']:
                band_key = (sub, radio, number, band['source'])
                entry = inventory.setdefault(band_key, dict(subscription=sub, radio=radio, band=number,
                    source=band['source'], roles=[], latest=False, last_seen=obs['received_utc'], elapsed_ms=-1))
                if role not in entry['roles']: entry['roles'].append(role)
                entry['latest'] |= current
                if obs['elapsed_realtime_ms'] >= entry['elapsed_ms']:
                    entry['last_seen'] = obs['received_utc']; entry['elapsed_ms'] = obs['elapsed_realtime_ms']
    rows = list(groups.values())
    serving = {'Primary serving','Secondary serving','Registered; role not exposed'}
    return dict(connected=[r for r in rows if r['latest'] and r['role'] in serving],
        neighbors=[r for r in rows if r['role']=='Neighbor'],
        unknown=[r for r in rows if r['role'] not in serving and r['role']!='Neighbor'],
        bands=list(inventory.values()), omitted=omitted,
        latest_observations=[dict(subscription=k, received_utc=v['received_utc'], outcome=v['outcome']) for k,v in latest.items()])


def visibility_html(result):
    esc = lambda value: escape(str(value if value is not None else 'Not exposed'))
    parts = ['<h3>Connected / registered at latest observation</h3>',
        '<p>Latest captured state per SIM, not a guarantee of the phone\'s present connection. Android may omit cells or bands; this is not an exhaustive RF scan.</p>']
    for obs in result['latest_observations']:
        parts.append('<p>'+esc(obs['subscription'])+' | '+esc(obs['received_utc'])+' | '+esc(obs['outcome'])+'</p>')
    def table(rows):
        if not rows: return '<p>No cells reported in this category.</p>'
        out = ['<table border="1" cellspacing="0" cellpadding="5"><tr><th>SIM / role</th><th>Radio / band</th><th>Carrier / identity</th><th>Signal</th><th>Last seen / freshness</th></tr>']
        for row in rows:
            ident = row['identity']
            values = []
            for name in ('rsrp','rsrq','rssnr','ss_rsrp','ss_rsrq','ss_sinr','csi_rsrp','csi_rsrq','csi_sinr'):
                q = row['signal'].get(name,{})
                if q.get('value') is not None: values.append(name.upper().replace('_','-')+': '+str(q['value'])+' '+q['unit'])
            identity_text = row['carrier']+' | MCC/MNC '+str(ident.get('mcc') or '?')+'/'+str(ident.get('mnc') or '?')+' | Cell '+str(ident.get('cell_id') or '?')+' | PCI '+str(ident.get('pci') if ident.get('pci') is not None else '?')
            fields = [row['subscription']+' / '+row['role'], row['radio']+' '+row['band']['label']+' | channel '+str(row['band']['channel'] if row['band']['channel'] is not None else '?'), identity_text,
                      '; '.join(values) or 'Not exposed', row['last_seen']+' | '+('latest observation' if row['latest'] else 'earlier observation')+' | '+row['freshness']+' | age '+str(row['age_ms'])+' ms']
            out.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in fields)+'</tr>')
        return ''.join(out)+'</table>'
    parts.append(table(result['connected']))
    parts.extend(['<h3>Neighboring cells observed</h3>', table(result['neighbors'])])
    if result['unknown']: parts.extend(['<h3>Unclassified observations</h3>', table(result['unknown'])])
    parts.append('<h3>Bands observed during capture</h3><p>Channel-derived candidates are possible band assignments, not confirmed bands or detected carriers. Overlapping NR bands remain unresolved.</p>')
    parts.append('<table border="1" cellspacing="0" cellpadding="5"><tr><th>SIM / band</th><th>Evidence</th><th>Observed roles</th><th>Last seen</th></tr>')
    for band in result['bands']:
        fields = [band['subscription']+' / '+band['radio']+' '+('n' if band['radio']=='NR' else 'B')+str(band['band']), band['source'], ', '.join(band['roles']), band['last_seen']+' | '+('latest observation' if band['latest'] else 'earlier observation')]
        parts.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in fields)+'</tr>')
    parts.append('</table>')
    if result['omitted']: parts.append(f"<p>Display limited to 1024 cell/role groups; {result['omitted']} entries omitted. Complete captured observations remain in raw evidence.</p>")
    return ''.join(parts)
