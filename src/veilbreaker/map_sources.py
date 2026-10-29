"""Read-only adapters from active diagnostic records to map evidence."""
import json
from pathlib import Path
from . import core
from .map_data import build_map_data
from .android_capture import load_capture
from .location_report import location_rows
from .survey_metrics import clean_metrics, metric_provenance

def _run(config,store,run_id,label=None):
    result=dict(run_id=run_id,label=label or run_id,locations=[],metrics={},context={})
    row=store.get_run(run_id)
    if row is None:return result
    try:
        result['metrics']=clean_metrics(json.loads(row['metrics_json'] or '{}')) if 'metrics_json' in row.keys() else {}
    except (ValueError, TypeError):
        pass
    collection = {}
    try:
        folder = Path(row['artifact_dir'] or config.artifacts_dir / run_id)
        source = folder / 'collection.json'
        if source.is_file() and source.stat().st_size <= 4 * 1024 * 1024:
            collection = json.loads(source.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        pass
    result['context'] = {key: metric_provenance(key, collection) for key in result['metrics']}
    phone = collection.get('android') if isinstance(collection, dict) else None
    if isinstance(phone, dict) and phone.get('source_kind') == 'live_android_usb' and not any(key.startswith('phone_') for key in result['metrics']):
        result['warning'] = 'Live Android per-cell series were not reduced to one survey signal; review the Cellular report.'
    try:
        report=json.loads(row['report_json'])
        locations=report.get('normalized_metrics',{}).get('location_report')
        if locations is None:
            path=Path(row['artifact_dir'] or config.artifacts_dir/run_id)/'android-capture.json'
            if path.is_file():locations=location_rows(load_capture(path)['envelope'])
        result['locations']=locations or []
    except (OSError,ValueError,TypeError,AttributeError,KeyError):
        result['warning']=result.get('warning', '')+' Location evidence could not be read for '+run_id
    return result

def _build(runs):
    model=build_map_data(runs)
    model['run_metrics']={run['run_id']:run['metrics'] for run in runs if run['metrics']}
    model['run_context']={run['run_id']:run['context'] for run in runs if run['context']}
    model['warnings'].extend(r['warning'] for r in runs if r.get('warning'))
    return model

def load_run_map_data(config,run_id):
    store=core.VeilbreakerStore(config.db_path)
    try:return _build([_run(config,store,run_id)])
    finally:store.close()

def load_survey_map_data(config,survey_path):
    path=Path(survey_path)
    if path.stat().st_size>4*1024*1024:raise ValueError('Survey file is too large.')
    session=json.loads(path.read_text(encoding='utf-8'));steps=session.get('steps')
    if not isinstance(steps,list) or len(steps)>20:raise ValueError('Invalid survey steps.')
    store=core.VeilbreakerStore(config.db_path)
    try:
        model=_build([_run(config,store,str(s['run_id']),s.get('label')) for s in steps])
        from .survey_spatial import load_spatial, add_manual_features
        if path.resolve().parent == (config.root / 'surveys').resolve():
            add_manual_features(model, load_spatial(config, path), steps)
        model['survey_path']=str(path)
        return model
    finally:store.close()
