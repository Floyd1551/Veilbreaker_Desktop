"""Derived reference context attachments; captured evidence remains immutable."""
import hashlib
import json
import uuid
from pathlib import Path
from .core import utcnow_iso
from .recovery import atomic_json
from .survey_imagery import asset_directory

MAX_CONTEXT=16*1024*1024


def _write_context(config,path,session,context,run_ids=None):
    raw=json.dumps(context,ensure_ascii=False,allow_nan=False).encode('utf-8')
    if len(raw)>MAX_CONTEXT: raise ValueError('Selected reference context exceeds 16 MiB; save fewer observations.')
    if len(context_html(context).encode('utf-8'))>6*1024*1024:raise ValueError('Reference report exceeds 6 MiB; keep fewer assessments.')
    asset_id=uuid.uuid4().hex
    folder=asset_directory(config,path,asset_id);folder.mkdir(parents=True)
    (folder/'cell-context.json').write_bytes(raw)
    session['cell_context']=dict(asset_id=asset_id,sha256=hashlib.sha256(raw).hexdigest(),
                                saved_utc=utcnow_iso(),run_ids=run_ids if run_ids is not None else [s['run_id'] for s in session['steps']])
    atomic_json(path,session)
    return session['cell_context']


def save_context(config,path,context):
    from .survey import _session_path,session_lock,_editable_session
    import copy
    path=_session_path(config,path)
    with session_lock(path):
        session=_editable_session(config,path)
        # A cell-reference dialog may have been opened before another window
        # attached a structure assessment. Preserve those independent results.
        context=copy.deepcopy(context)
        saved=load_context(config,path)
        physical=[]
        if saved:
            physical=[a for a in saved['context'].get('assessments',[]) if _physical_assessment(a)]
        if physical:
            assessments=context.setdefault('assessments',[])
            if not isinstance(assessments,list):raise ValueError('Invalid saved assessments.')
            for assessment in physical:
                if assessment not in assessments:assessments.append(assessment)
        pointer=session.get('cell_context')
        return _write_context(config,path,session,context,pointer.get('run_ids') if physical and pointer else None)


def _physical_assessment(assessment):
    if not isinstance(assessment,dict):return False
    context=assessment.get('endpoint_context')
    candidate=context.get('candidate') if isinstance(context,dict) else None
    return isinstance(candidate,dict) and candidate.get('reference_kind')=='physical structure'


def _matching_receiver(assessment, model):
    """Bind the assessment to exactly one current map observation."""
    from .map_data import finite
    if not isinstance(assessment,dict):return False
    context=assessment.get('endpoint_context')
    if not isinstance(context,dict):return False
    receiver=context.get('map_receiver')
    if not isinstance(receiver,dict) or type(receiver.get('manual')) is not bool:return False
    if not all(isinstance(receiver.get(k),str) and receiver[k] for k in ('run_id','observation_id')):return False
    lat,lon=receiver.get('latitude_deg'),receiver.get('longitude_deg')
    if not finite(lat) or not finite(lon) or abs(lat)>90 or abs(lon)>180:return False
    keys=('run_id','observation_id','latitude_deg','longitude_deg','placed_utc','source_kind',
          'mobile_capture_id','mobile_survey_sha256','source','provider','fix_utc','received_utc',
          'horizontal_accuracy_m','fix_age_ms','mock')
    rows=[row for row in model.get('rows',[]) if isinstance(row,dict)
          and all(row.get(k)==receiver.get(k) for k in keys)
          and (row.get('manual') is True)==receiver['manual']]
    if len(rows)!=1:return False
    row=rows[0]
    if receiver['manual']:
        if row.get('source')!='operator' or not receiver.get('placed_utc'):return False
        position_source='operator_map_placement'
    else:
        if row.get('quality',{}).get('qualified') is not True:return False
        position_source='qualified_location'
    observation=context.get('observation')
    if not isinstance(observation,dict):return False
    observed_source=observation.get('position_source')
    # Early builds used this label for any qualified recorded location.
    if position_source=='qualified_location' and observed_source=='qualified_gps':observed_source='qualified_location'
    if observed_source!=position_source:return False
    location=observation.get('location')
    if not isinstance(location,dict) or location.get('latitude_deg')!=lat or location.get('longitude_deg')!=lon:return False
    terrain=assessment.get('terrain')
    endpoints=terrain.get('endpoints') if isinstance(terrain,dict) else None
    candidate=context.get('candidate')
    return (isinstance(endpoints,list) and len(endpoints)==2 and endpoints[0]==[lon,lat]
            and isinstance(candidate,dict) and endpoints[1]==[candidate.get('lon'),candidate.get('lat')])


def append_structure_assessment(config,path,assessment):
    from .survey import _session_path,session_lock,_editable_session
    from .map_sources import load_survey_map_data
    path=_session_path(config,path)
    with session_lock(path):
        session=_editable_session(config,path)
        context=assessment.get('endpoint_context') if isinstance(assessment,dict) else None
        candidate=context.get('candidate') if isinstance(context,dict) else None
        if not isinstance(candidate,dict) or candidate.get('reference_kind')!='physical structure' or candidate.get('selection_method')!='operator_selected':
            raise ValueError('Select a physical structure before saving the assessment.')
        try:valid=_matching_receiver(assessment,load_survey_map_data(config,path))
        except (OSError,ValueError,KeyError,TypeError):valid=False
        if not valid:raise ValueError('The selected receiver changed or is no longer available. Select it again on the survey map.')
        saved=load_context(config,path)
        value=saved['context'] if saved else dict(runs=[])
        if not isinstance(value,dict):raise ValueError('Invalid saved reference context.')
        assessments=value.setdefault('assessments',[])
        if not isinstance(assessments,list):raise ValueError('Invalid saved assessments.')
        assessments.append(assessment)
        old_pointer=session.get('cell_context')
        return _write_context(config,path,session,value,old_pointer.get('run_ids') if old_pointer else None)


def load_context(config,path):
    session=json.loads(Path(path).read_text(encoding='utf-8')); pointer=session.get('cell_context')
    if not pointer:return None
    file=asset_directory(config,path,pointer['asset_id'])/'cell-context.json'
    if file.stat().st_size>MAX_CONTEXT:raise ValueError('Saved reference context exceeds size limit.')
    raw=file.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=pointer['sha256']:raise ValueError('Saved reference context integrity check failed.')
    value=json.loads(raw)
    stale=pointer['run_ids']!=[s['run_id'] for s in session['steps']]
    # Validate capture identities without opening a reference database or making network calls.
    from .core import VeilbreakerStore
    store=VeilbreakerStore(config.db_path)
    try:
        for run in value.get('runs',[]):
            record=store.get_run(run['run_id'])
            if record is None:stale=True;continue
            capture=Path(record['artifact_dir'] or config.artifacts_dir/run['run_id'])/'android-capture.json'
            if not capture.is_file() or capture.stat().st_size>16*1024*1024:stale=True;continue
            if hashlib.sha256(capture.read_bytes()).hexdigest()!=run.get('capture_sha256'):stale=True
    finally:store.close()
    physical=[a for a in value.get('assessments',[]) if _physical_assessment(a)]
    if physical:
        try:
            from .map_sources import load_survey_map_data
            model=load_survey_map_data(config,path)
            if any(not _matching_receiver(a,model) for a in physical):stale=True
        except (OSError,ValueError,KeyError,TypeError):stale=True
    return dict(context=value,stale=stale,path=file,saved_utc=pointer['saved_utc'])


def context_html(context):
    from .survey_report import text,table
    parts=['<h2>Cell and structure reference context</h2><p>Reference positions are not verified serving towers. Lines represent bearing, not line of sight.</p>']
    runs=context.get('runs',[context])
    for run in runs:
        parts.append('<h3>'+text(run.get('run_id','Selected capture'))+'</h3>')
        dataset=run.get('dataset') or {}
        parts.append('<p>'+text(dataset.get('attribution','No active reference dataset'))+'<br>Source date: '+text(dataset.get('date'))+'; dataset SHA-256: '+text(dataset.get('sha256'))+'</p>')
        for row in run.get('rows',[]):
            parts.append(table(['Observation','Network / radio','Full identity','Match status'],[[row.get('observation_id'),str(row.get('carrier') or 'Not exposed')+' / '+row.get('radio',''),row.get('identity'),row.get('status')]]))
            signals={k:f"{v.get('value')} {v.get('unit','')}" for k,v in row.get('signal',{}).items() if isinstance(v,dict) and v.get('value') is not None}
            parts.append('<p>Measurements: '+text(signals)+'<br>GPS/modem offset (ms): '+text(row.get('location_after_modem_ms'))+'</p>')
            parts.append(table(['Reference','Latitude / longitude','Distance (m)','Bearing (°)','Samples / updated'],[[c.get('verification'),f"{c['lat']}, {c['lon']}",round(c['distance_m'],1) if c.get('distance_m') is not None else None,round(c['bearing_deg'],1) if c.get('bearing_deg') is not None else None,f"{c.get('samples','Unknown')} / {c.get('updated','Unknown')} (Unix seconds)"] for c in row.get('candidates',[])]))
        if run.get('omitted'):parts.append('<p>Additional observations omitted: '+text(run['omitted'])+'</p>')
    for assessment in context.get('assessments',[]):
        from .path_assessment_report import assessment_html
        parts.append(assessment_html(assessment))
    return '\n'.join(parts)


def saved_context_html(config,path):
    from .survey_report import text
    try:
        saved=load_context(config,path)
        if not saved:return ''
        return ('<p><b>Saved reference context is out of date; regenerate it.</b></p>' if saved['stale'] else '')+context_html(saved['context'])
    except (OSError,ValueError,KeyError,TypeError) as exc:
        return '<p>Reference context unavailable: '+text(exc)+'</p>'
