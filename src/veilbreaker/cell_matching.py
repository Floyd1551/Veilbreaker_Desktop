"""Observation-specific serving-cell matching, independent of network assessment."""
import math
from pathlib import Path
from .cell_reference import identity_key, active_reference, lookup_reference
from .location_report import qualify_location
from .android_capture import validate_capture, load_capture
from .core import VeilbreakerStore


def distance_bearing(lon1,lat1,lon2,lat2):
    p1,p2=math.radians(lat1),math.radians(lat2); dl=math.radians(lon2-lon1)
    h=math.sin((p2-p1)/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    distance=2*6371008.8*math.asin(math.sqrt(min(1,max(0,h))))
    bearing=(math.degrees(math.atan2(math.sin(dl)*math.cos(p2),math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl)))+360)%360
    return distance, bearing if distance>0.001 else None


def match_capture(envelope,reference_root):
    validate_capture(envelope)
    manifest=active_reference(reference_root)
    rows=[]; omitted=0
    subscriptions={s['key']:s for s in envelope['subscriptions']}
    cache={}
    for obs in envelope['observations']:
        for index,cell in enumerate(obs['cells']):
            if cell.get('registered') is not True: continue
            if len(rows)>=1000: omitted+=1;continue
            location=obs.get('location') or {}
            quality=qualify_location(location)
            row=dict(observation_id=obs['observation_id'],subscription=obs['subscription_key'],cell_index=index,
                     received_utc=obs['received_utc'],radio=cell['radio'],identity=dict(cell['identity']),signal=cell['signal'],
                     carrier=subscriptions[obs['subscription_key']].get('network_operator') or cell['identity'].get('operator_alpha_long'),
                     location=location,location_quality=quality,modem_age_ms=cell.get('age_ms'),candidates=[])
            a,b=cell.get('age_ms'),location.get('fix_age_ms')
            row['location_after_modem_ms']=a-b if type(a) in (int,float) and type(b) in (int,float) else None
            if cell['radio'] not in ('LTE','NR') or (cell['radio']=='NR' and manifest and manifest['format']!='operator'):
                row['status']='unsupported technology'
            else:
                try: key=identity_key(dict(cell['identity'],radio=cell['radio']))
                except ValueError: row['status']='incomplete identity'
                else:
                    if manifest is None: row['status']='reference unavailable'
                    else:
                        if key not in cache: cache[key]=lookup_reference(reference_root,key)
                        candidates=cache[key]
                        # Duplicate rows with identical coordinates do not create a false conflict.
                        coords={(c['lon'],c['lat']) for c in candidates}
                        row['status']='conflicting references' if len(coords)>1 else 'reference match' if candidates else 'not found'
                        row['candidate_limit_reached']=len(candidates)>200
                        for candidate in candidates[:200]:
                            distance=bearing=None
                            if quality['qualified']:
                                distance,bearing=distance_bearing(location['longitude_deg'],location['latitude_deg'],candidate['lon'],candidate['lat'])
                            row['candidates'].append(dict(candidate,distance_m=distance,bearing_deg=bearing))
            rows.append(row)
    return dict(schema_version=1,matcher_version=1,capture_id=envelope['capture_id'],dataset=manifest,rows=rows,omitted=omitted)


def load_run_matches(config,run_id):
    store=VeilbreakerStore(config.db_path)
    try: row=store.get_run(run_id)
    finally: store.close()
    if row is None: raise ValueError('Diagnostic record is unavailable.')
    path=Path(row['artifact_dir'] or config.artifacts_dir/run_id)/'android-capture.json'
    if not path.is_file(): raise ValueError('This test has no saved Android cellular capture.')
    capture=load_capture(path)
    result=match_capture(capture['envelope'],config.root/'cell-references')
    import hashlib
    result.update(run_id=run_id,capture_sha256=hashlib.sha256(capture['raw_bytes']).hexdigest())
    return result
