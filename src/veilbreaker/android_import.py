"""Analyze selected phone observations without acquiring desktop measurements."""
import json
import uuid
from . import core
from .android_capture import load_capture, normalize_selection, require
from .acquisition import Acquisition


def import_capture(config, path, expected_sha256, observation_id, cell_index, allow_repeat=False):
    capture = load_capture(path)
    require(capture['sha256'] == expected_sha256, 'Capture changed since preview; reopen it before importing.')
    require(type(allow_repeat) is bool, 'Invalid repeat-import option')
    selected = normalize_selection(capture['envelope'], observation_id, cell_index)
    metrics, notes, provenance = (selected[k] for k in ('metrics','notes','provenance'))
    provenance['source_sha256'] = capture['sha256']
    metrics['android_source_sha256'] = capture['sha256']
    metrics['android_cell_index'] = cell_index
    app = core.VeilbreakerApplication(config)
    try:
        for row in app.store.db.execute('SELECT run_id, metrics_json FROM runs WHERE run_id LIKE ?', ('android-%',)):
            saved = json.loads(row['metrics_json'])
            if saved.get('android_capture_id') == provenance['capture_id'] and not allow_repeat:
                raise ValueError(f"Capture already imported in {row['run_id']}. Review history or explicitly allow another import in the preview.")
        run_id = 'android-' + uuid.uuid4().hex
        acquisition = Acquisition()
        complete = provenance['collection_outcome'] == 'complete' and provenance['observation_outcome'] == 'complete'
        acquisition.collect('android_import', lambda: (metrics, notes), complete=lambda _: complete)
        collection = acquisition.to_dict()
        collection['source_kind'] = 'android_import'
        collection['android'] = provenance
        # Receiver/source compatibility with historical baselines is not established.
        report = app.engine.analyze(metrics)
        report.summary.extend(notes)
        report.summary.append('Android import: historical baseline/case matching was not applied across potentially different receivers.')
        artifact_dir = config.artifacts_dir / run_id
        artifact_dir.mkdir(parents=True, exist_ok=False)
        (artifact_dir / 'android-capture.json').write_bytes(capture['raw_bytes'])
        (artifact_dir / 'android-selection.json').write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding='utf-8')
        pack = core.write_evidence_pack(config, run_id, metrics, report, notes, [], collection)
        app.store.save_run(run_id, config.site_id, config.scenario, metrics, report, artifact_dir=str(artifact_dir), note='Android public-API import')
        return {'run_id':run_id, 'site_id':config.site_id, 'report':report.to_dict(), 'metrics':metrics,
                'notes':notes, 'collection':collection, 'sweeps':[], 'artifact_dir':str(artifact_dir), 'evidence_zip':str(pack)}
    finally:
        app.close()


def prepare_input(selection):
    """Validate an attached capture before starting any diagnostic collectors."""
    capture = load_capture(selection['path'])
    require(capture['sha256'] == selection['expected_sha256'], 'Android input changed since selection; attach it again.')
    selected = normalize_selection(capture['envelope'], selection['observation_id'], selection['cell_index'])
    selected['provenance']['source_sha256'] = capture['sha256']
    selected['provenance']['source_kind'] = 'saved_android_capture'
    selected['raw_bytes'] = capture['raw_bytes']
    from .receiver_assessment import build_phone_assessments
    selected['assessments'] = build_phone_assessments(capture['envelope'], (selection['observation_id'], selection['cell_index']))
    return selected


def prepare_live_input(envelope):
    from .android_usb import summarize_session
    from .android_capture import validate_capture
    from .receiver_assessment import build_phone_assessments
    validate_capture(envelope)
    summary = summarize_session(envelope)
    # Each cell is assessed independently; no strongest-cell selection or averaging.
    cells = {}
    for obs in envelope['observations']:
        for index, cell in enumerate(obs['cells']):
            if cell.get('registered') is True and cell['radio'] in {'LTE', 'NR'}:
                key = json.dumps([obs['subscription_key'], cell['radio'], cell['identity']], sort_keys=True)
                cells[key] = normalize_selection(envelope, obs['observation_id'], index)
    notes = ['Live USB session: ' + str(summary['observations']) + ' observations; ' + str(summary['repeated_samples']) + ' repeated registered-cell samples; ' + str(summary['unknown_age_samples']) + ' samples with unknown age.']
    for index, group in enumerate(summary['registered_cells'], 1):
        notes.append('Phone cell ' + str(index) + ' ' + group['radio'] + ' identity ' + json.dumps(group['identity'], sort_keys=True) + ': ' + str(group['samples']) + ' samples.')
        for name, stats in group['signals'].items():
            notes.append(f"Phone cell {index} {name}: {stats['min']} to {stats['max']} {stats['unit']}; first-to-last change {stats['change']}.")
    engine = core.ProfessionalVeilbreakerEngine()
    for index, selected in enumerate(cells.values(), 1):
        notes.extend('Phone cell ' + str(index) + ': ' + f.title + ' â€” ' + f.observation for f in engine.analyze(selected['metrics']).findings)
    if not cells: notes.append('No registered LTE/NR cell was available for RF assessment.')
    return {'metrics': {'android_source': 'usb_live', 'observation_count': summary['observations'], 'registered_cell_count': len(cells)},
            'assessments': build_phone_assessments(envelope),
            'notes': notes, 'raw_bytes': json.dumps(envelope, ensure_ascii=False).encode('utf-8'),
            'provenance': {'source_kind': 'live_android_usb', 'capture_id': envelope['capture_id'],
                           'received_utc': envelope['created_utc'], 'collection_outcome': envelope['collection']['outcome'],
                           'observation_outcome': 'complete' if cells else 'partial', 'session_summary': summary}}
