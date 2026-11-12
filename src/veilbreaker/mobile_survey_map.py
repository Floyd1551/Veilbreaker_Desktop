"""Read-only location preview of already validated mobile survey evidence."""
from .location_report import location_rows
from .map_data import build_map_data
from .android_capture import require
from .mobile_survey_import import parse_mobile_survey_bytes
from .mobile_survey_metrics import aligned_mobile_metrics


def build_mobile_survey_map(loaded):
    checked = parse_mobile_survey_bytes(loaded.get('raw_bytes'))
    require(checked['sha256'] == loaded.get('sha256'), 'Mobile survey source hash does not match the reviewed bytes.')
    survey = checked['survey']
    runs = []
    metadata = {}
    aligned = {}
    for index, point in enumerate(survey['points'], 1):
        capture = point['capture']
        key = f'mobile-point-{index}'
        aligned[key] = aligned_mobile_metrics(capture)
        runs.append({'run_id': key, 'label': f"Mobile point {index} · {capture['created_utc']}",
                     'locations': location_rows(capture)})
        metadata[key] = {'source_kind': 'mobile_survey_capture', 'mobile_capture_id': capture['capture_id'],
                         'mobile_survey_id': survey['survey_id'], 'mobile_survey_sha256': loaded['sha256'],
                         'attached_utc': point['attached_utc'], 'operator_note': point.get('operator_note')}
    model = build_map_data(runs)
    for row in model['rows']:
        row.update(metadata[row['run_id']])
        match = aligned[row['run_id']].get(row['observation_id'])
        if match: row['mobile_aligned'] = match
    for feature in model['features']['features']:
        feature['properties'].update(metadata[feature['properties']['run_id']])
        props = feature['properties']
        match = aligned[props['run_id']].get(props['observation_id'])
        if match: props['mobile_aligned'] = match
    model.update(mobile_survey_preview=True, run_metrics={}, run_context={}, cell_groups={})
    model['warnings'].append('Mobile survey preview only: no Desktop diagnostic runs were created. GPS and cellular samples can have different times; cellular metrics are not mapped here.')
    return model
