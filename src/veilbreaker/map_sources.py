"""Read-only adapters from active diagnostic records to map evidence."""
import json
from pathlib import Path
from . import core
from .map_data import build_map_data
from .android_capture import load_capture
from .location_report import location_rows
from .survey_metrics import clean_metrics, metric_provenance
from .survey_live_cellular import reduce_live_cell_report, live_cell_groups

def _run(config,store,run_id,label=None):
    result=dict(run_id=run_id,label=label or run_id,locations=[],metrics={},context={},cell_groups=[])
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
    try:
        report=json.loads(row['report_json'])
        if isinstance(phone, dict) and phone.get('source_kind') == 'live_android_usb':
            cellular = report.get('normalized_metrics', {}).get('android_cellular_report')
            reduced = reduce_live_cell_report(cellular)
            result['cell_groups'] = live_cell_groups(cellular)
            result['metrics'].update(clean_metrics(reduced['metrics']))
            result['context'].update(reduced['context'])
            if reduced.get('warning'):
                result['warning'] = reduced['warning']
            cells=cellular.get('cells') if isinstance(cellular,dict) else None
            if isinstance(cells,list) and len(cells)>1 and len(result['cell_groups']) < len(cells):
                result['warning'] = (result.get('warning','') + ' Some cell groups lack a complete identity or fresh uncached readings and cannot be selected.')
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
    groups={}
    for run in runs:
        entries=run.get('cell_groups',[])
        counts={entry['key']:sum(1 for other in entries if other['key']==entry['key']) for entry in entries}
        if any(count != 1 for count in counts.values()):
            model['warnings'].append('Ambiguous duplicate cell groups in '+run['run_id']+' were excluded from selection.')
        for entry in entries:
            if counts[entry['key']] != 1:
                continue
            scoped=json.dumps([run['run_id'],entry['key']],separators=(',',':'))
            group=groups.setdefault(scoped,{'label':f"{run.get('label') or run['run_id']} · Run {run['run_id']} · {entry['label']}",'runs':{}})
            group['runs'][run['run_id']]={'metrics':entry['metrics'],'context':entry['context']}
    model['cell_groups']=groups
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
        runs=[_run(config,store,str(s['run_id']),s.get('label')) for s in steps]
        metadata={}; aligned={}
        if path.resolve().parent == (config.root / 'surveys').resolve():
            from .survey_mobile_evidence import read_attached_mobile_surveys
            from .mobile_survey_metrics import aligned_mobile_metrics
            for source in read_attached_mobile_surveys(config, path, session):
                for index, point in enumerate(source['survey']['points'], 1):
                    capture=point['capture']
                    key='mobile-'+source['sha256']+'-'+str(index)
                    aligned[key]=aligned_mobile_metrics(capture)
                    runs.append(dict(run_id=key, label=source['survey']['name']+' · Mobile point '+str(index),
                                     locations=location_rows(capture), metrics={}, context={}, cell_groups=[]))
                    metadata[key]=dict(source_kind='mobile_survey_capture', mobile_capture_id=capture['capture_id'],
                        mobile_survey_id=source['survey']['survey_id'], mobile_survey_sha256=source['sha256'],
                        attached_utc=point['attached_utc'], operator_note=point.get('operator_note'))
        model=_build(runs)
        for row in model['rows']:
            row.update(metadata.get(row['run_id'], {}))
            match=aligned.get(row['run_id'], {}).get(row['observation_id'])
            if match: row['mobile_aligned']=match
        for feature in model['features']['features']:
            feature['properties'].update(metadata.get(feature['properties']['run_id'], {}))
            props=feature['properties']
            match=aligned.get(props['run_id'], {}).get(props['observation_id'])
            if match: props['mobile_aligned']=match
        if metadata:
            model['warnings'].append('Mobile locations and cellular readings can have different timestamps; mobile cellular metrics are not assigned to locations.')
        from .survey_spatial import load_spatial, add_manual_features
        if path.resolve().parent == (config.root / 'surveys').resolve():
            mobile_steps=[dict(run_id=r['run_id'], label=r['label'], **metadata[r['run_id']])
                          for r in runs if r['run_id'] in metadata]
            add_manual_features(model, load_spatial(config, path), steps + mobile_steps)
        model['survey_path']=str(path)
        return model
    finally:store.close()
