"""Derived reference context attachments; captured evidence remains immutable."""
import hashlib
import json
import uuid
from pathlib import Path
from .core import utcnow_iso
from .recovery import atomic_json
from .survey_imagery import asset_directory

MAX_CONTEXT=16*1024*1024


def save_context(config,path,context):
    from .survey import _session_path,session_lock,_editable_session
    path=_session_path(config,path)
    raw=json.dumps(context,ensure_ascii=False,allow_nan=False).encode('utf-8')
    if len(raw)>MAX_CONTEXT: raise ValueError('Selected reference context exceeds 16 MiB; save fewer observations.')
    if len(context_html(context).encode('utf-8'))>6*1024*1024:raise ValueError('Reference report exceeds 6 MiB; keep fewer assessments.')
    with session_lock(path):
        session=_editable_session(config,path)
        asset_id=uuid.uuid4().hex
        folder=asset_directory(config,path,asset_id);folder.mkdir(parents=True)
        (folder/'cell-context.json').write_bytes(raw)
        session['cell_context']=dict(asset_id=asset_id,sha256=hashlib.sha256(raw).hexdigest(),
                                    saved_utc=utcnow_iso(),run_ids=[s['run_id'] for s in session['steps']])
        atomic_json(path,session)
    return session['cell_context']


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
    return dict(context=value,stale=stale,path=file,saved_utc=pointer['saved_utc'])


def context_html(context):
    from .survey_report import text,table
    parts=['<h2>Cell-reference context</h2><p>Reference positions are not verified serving towers. Lines represent bearing, not line of sight.</p>']
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
