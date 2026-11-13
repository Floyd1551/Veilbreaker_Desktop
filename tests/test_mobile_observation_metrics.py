import copy
import json
import unittest
import uuid
from pathlib import Path

from veilbreaker.mobile_observation_metrics import (
    available_observation_metrics, observation_cell_groups, observation_metric_series,
)


def row(identifier, run='capture-a', capture='id-a', value=-95, cell='123', **changes):
    context = dict(observation_id=identifier, companion_version='0.8.25-dev',
        radio='LTE', subscription='sim-1', age_ms=1500, fix_age_ms=1000,
        location_after_modem_ms=500, received_utc='2026-11-13T12:00:00Z',
        cell_identity=dict(mcc='311', mnc='480', cell_id=cell, earfcn=5230, pci=2))
    item = dict(id=identifier, run_id=run, source_kind='mobile_survey_capture',
        mobile_capture_id=capture, observation_id=identifier, manual=False,
        renderable=True, mock=False, latitude_deg=34.7, longitude_deg=-86.6,
        fix_age_ms=1000, received_utc='2026-11-13T12:00:00Z', quality={'qualified': True},
        mobile_aligned={'metrics': {'phone_lte_rsrp': value},
                        'context': {'phone_lte_rsrp': context}})
    item.update(changes)
    return item


def model(*rows):
    return {'rows': list(rows), 'features': {'features': [dict(type='Feature', id=r['id'],
        geometry=dict(type='Point', coordinates=[r['longitude_deg'], r['latitude_deg']]), properties=copy.deepcopy(r)) for r in rows]}}


class MobileObservationMetricTests(unittest.TestCase):
    def test_complete_cell_group_scopes_values_and_relative_scale_to_exact_features(self):
        data = model(row('one', value=-100), row('two', value=-80), row('other-cell', cell='456', value=-50),
                     row('other-capture', run='capture-b', capture='id-b', value=-60), row('manual', manual=True))
        before = copy.deepcopy(data)
        self.assertEqual(available_observation_metrics(data, 'capture-a'), ['phone_lte_rsrp'])
        groups = observation_cell_groups(data, 'capture-a', 'phone_lte_rsrp')
        self.assertEqual(len(groups), 2)
        group = next(key for key, label in groups if 'cell 123' in label)
        result = observation_metric_series(data, 'capture-a', 'phone_lte_rsrp', group)
        self.assertEqual(set(result['points']), {'one', 'two'})
        self.assertEqual((result['scale']['minimum'], result['scale']['maximum'], result['scale']['count']), (-100, -80, 2))
        self.assertEqual(result['points']['one']['context']['observation_id'], 'one')
        self.assertNotEqual(result['points']['one']['color'], result['points']['two']['color'])
        self.assertEqual(data, before)

    def test_missing_identity_old_or_unknown_provenance_never_forms_a_series(self):
        entries = [row('valid'), row('missing-cell'), row('missing-channel'), row('wrong-time'),
                   row('different-observation'), row('mock-unknown', mock=None), row('unqualified', quality={'qualified': False})]
        del entries[1]['mobile_aligned']['context']['phone_lte_rsrp']['cell_identity']['cell_id']
        del entries[2]['mobile_aligned']['context']['phone_lte_rsrp']['cell_identity']['earfcn']
        entries[3]['mobile_aligned']['context']['phone_lte_rsrp']['age_ms'] = 11000
        entries[4]['mobile_aligned']['context']['phone_lte_rsrp']['observation_id'] = 'elsewhere'
        data = model(*entries)
        groups = observation_cell_groups(data, 'capture-a', 'phone_lte_rsrp')
        self.assertEqual(len(groups), 1)
        self.assertEqual(set(observation_metric_series(data, 'capture-a', 'phone_lte_rsrp', groups[0][0])['points']), {'valid'})

    def test_explicit_group_and_visible_feature_ids_are_required(self):
        data = model(row('one'), row('two', value=-80))
        group = observation_cell_groups(data, 'capture-a', 'phone_lte_rsrp')[0][0]
        self.assertEqual(observation_metric_series(data, 'capture-a', 'phone_lte_rsrp', None)['points'], {})
        filtered = observation_metric_series(data, 'capture-a', 'phone_lte_rsrp', group, visible_ids={'two'})
        self.assertEqual(set(filtered['points']), {'two'})
        self.assertEqual(filtered['scale']['count'], 1)
        self.assertEqual(filtered['points']['two']['color'], '#52b7ca')
        self.assertEqual(observation_metric_series(data, None, 'phone_lte_rsrp', group)['points'], {})
        self.assertEqual(observation_metric_series(data, 'capture-b', 'phone_lte_rsrp', group)['points'], {})

    def test_absent_feature_or_unsupported_metric_are_not_offered(self):
        data = model(row('one'))
        data['features']['features'] = []
        self.assertEqual(available_observation_metrics(data, 'capture-a'), [])
        self.assertEqual(observation_cell_groups(data, 'capture-a', 'latency_ms'), [])

    def test_inconsistent_feature_identity_geometry_or_value_is_never_colored(self):
        for change in ('capture', 'observation', 'run', 'coordinates', 'measurement'):
            data = model(row('one'))
            feature = data['features']['features'][0]
            if change == 'capture': feature['properties']['mobile_capture_id'] = 'id-b'
            if change == 'observation': feature['properties']['observation_id'] = 'different'
            if change == 'run': feature['properties']['run_id'] = 'capture-b'
            if change == 'coordinates': feature['geometry']['coordinates'][0] += 1
            if change == 'measurement': feature['properties']['mobile_aligned']['metrics']['phone_lte_rsrp'] = -30
            with self.subTest(change=change):
                self.assertEqual(available_observation_metrics(data, 'capture-a'), [])

    def test_actual_mobile_preview_is_observation_scoped_and_preserves_evidence(self):
        from veilbreaker.mobile_survey_import import parse_mobile_survey_bytes
        from veilbreaker.mobile_survey_map import build_mobile_survey_map
        capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        capture['device']['companion_version'] = '0.8.25-dev'
        first = capture['observations'][0]
        first['location'] = dict(status='available', source='phone', provider='gps',
            fix_utc=first['received_utc'], latitude_deg=34.7, longitude_deg=-86.6,
            horizontal_accuracy_m=5, fix_age_ms=1000, mock=False)
        second = copy.deepcopy(first)
        second['observation_id'] = 'second'
        second['received_utc'] = '2026-10-10T12:00:11Z'
        second['elapsed_realtime_ms'] += 10000
        second['location']['fix_utc'] = second['received_utc']
        second['location']['latitude_deg'] = 34.71
        second['cells'][0]['signal']['rsrp']['value'] = -80
        capture['observations'].append(second)
        source = dict(format='veilbreaker.mobile.survey', schema_version=1, survey_id=str(uuid.uuid4()),
            name='Fixture', created_utc=capture['created_utc'], lifecycle='open',
            points=[dict(attached_utc=capture['created_utc'], capture=capture)])
        loaded = parse_mobile_survey_bytes(json.dumps(source).encode('utf-8'))
        preview = build_mobile_survey_map(loaded)
        group = observation_cell_groups(preview, 'mobile-point-1', 'phone_lte_rsrp')[0][0]
        result = observation_metric_series(preview, 'mobile-point-1', 'phone_lte_rsrp', group)
        self.assertEqual({p['value'] for p in result['points'].values()}, {-95, -80})
        self.assertEqual(preview['run_metrics'], {})
        first_result = next(iter(result['points'].values()))
        first_result['context']['cell_identity']['cell_id'] = 'modified'
        self.assertEqual(preview['rows'][0]['mobile_aligned']['context']['phone_lte_rsrp']['cell_identity']['cell_id'], '1234')
