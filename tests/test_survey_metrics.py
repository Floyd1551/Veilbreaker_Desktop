import unittest

from veilbreaker.survey_metrics import (available_metrics, metric_scale, clean_metrics,
                                        point_metric, floor_measurements, metric_provenance,
                                        source_options, source_matches, provenance_label, select_cell_group)


class SurveyMetricTests(unittest.TestCase):
    def test_automatic_live_values_do_not_compare_multiple_unverified_receivers(self):
        model={'run_metrics':{'a':{'live_phone_lte_rsrp':-95,'rsrp':-80},'b':{'live_phone_lte_rsrp':-110}},
               'run_context':{},'cell_groups':{'one':{'runs':{'a':{'metrics':{'live_phone_lte_rsrp':-95},'context':{}}}}}}
        automatic=select_cell_group(model,None)
        self.assertNotIn('live_phone_lte_rsrp',automatic['run_metrics']['a'])
        self.assertNotIn('live_phone_lte_rsrp',automatic['run_metrics']['b'])
        self.assertEqual(automatic['run_metrics']['a']['rsrp'],-80)
        self.assertEqual(select_cell_group(model,'one')['run_metrics']['a']['live_phone_lte_rsrp'],-95)
        self.assertEqual(model['run_metrics']['b']['live_phone_lte_rsrp'],-110)
    def test_only_supported_finite_measurements_are_retained(self):
        values = clean_metrics({'rsrp': -91, 'sinr': float('nan'), 'wifi_rssi_dbm': True,
                                'latency_ms': 0, 'operator_note': 17, 'download_mbps': '42'})
        self.assertEqual(values, {'rsrp': -91, 'latency_ms': 0})

    def test_scale_is_relative_to_saved_run_values_and_missing_stays_missing(self):
        model = {'run_metrics': {'a': {'rsrp': -112}, 'b': {'rsrp': -82}, 'c': {}}}
        self.assertEqual(available_metrics(model), ['rsrp'])
        scale = metric_scale(model, 'rsrp')
        self.assertEqual((scale['minimum'], scale['maximum'], scale['count']), (-112, -82, 2))
        self.assertEqual(point_metric(model, 'c', 'rsrp', scale), None)
        self.assertEqual(point_metric(model, 'a', 'rsrp', scale)['value'], -112)
        self.assertNotEqual(point_metric(model, 'a', 'rsrp', scale)['color'],
                            point_metric(model, 'b', 'rsrp', scale)['color'])

    def test_single_value_has_neutral_color_without_quality_verdict(self):
        model = {'run_metrics': {'a': {'sinr': 7}}}
        scale = metric_scale(model, 'sinr')
        self.assertEqual(scale['minimum'], scale['maximum'])
        self.assertEqual(point_metric(model, 'a', 'sinr', scale)['color'], '#52b7ca')

    def test_invalid_values_never_offer_a_metric_choice(self):
        model = {'run_metrics': {'a': {'rsrp': True, 'sinr': float('inf')}}}
        self.assertEqual(available_metrics(model), [])

    def test_floor_scale_uses_only_placed_scans_on_selected_floor(self):
        steps = [
            {'run_id': 'a', 'label': 'Lobby', 'metrics': {'rsrp': -110}},
            {'run_id': 'b', 'label': 'Hall', 'metrics': {'rsrp': -80}},
            {'run_id': 'c', 'label': 'Roof', 'metrics': {'rsrp': -30}},
            {'run_id': 'd', 'label': 'No RSRP', 'metrics': {'sinr': 4}},
        ]
        placements = {key: {'kind': 'floor', 'floor_id': floor, 'x': .2, 'y': .4,
                            'placed_utc': '2026-10-28T00:00:00Z'}
                      for key, floor in [('a', 'f1'), ('b', 'f1'), ('c', 'roof'), ('d', 'f1')]}
        markers, scale = floor_measurements(steps, placements, 'f1', 'rsrp')
        self.assertEqual((scale['minimum'], scale['maximum'], scale['count']), (-110, -80, 2))
        self.assertEqual([m['run_id'] for m in markers], ['a', 'b', 'd'])
        self.assertEqual(markers[0]['placed_utc'], '2026-10-28T00:00:00Z')
        self.assertIsNone(markers[-1]['metric'])
        self.assertNotEqual(markers[0]['metric']['color'], markers[1]['metric']['color'])

    def test_phone_metrics_remain_distinct_from_desktop_modem(self):
        values = clean_metrics({'rsrp': -80, 'phone_lte_rsrp': -95, 'phone_nr_sinr': 7})
        self.assertEqual(values, {'rsrp': -80, 'phone_lte_rsrp': -95, 'phone_nr_sinr': 7})

    def test_provenance_uses_recorded_collector_and_phone_receipt(self):
        collection = {'metric_sources': {'rsrp': ['cellular_modem'], 'phone_lte_rsrp': ['android_input']},
                      'collectors': [{'source': 'cellular_modem', 'started_utc': '2026-10-28T10:00:00Z', 'duration_s': 1.4}],
                      'android': {'received_utc': '2026-10-28T09:59:58Z', 'age_ms': 800}}
        desktop = metric_provenance('rsrp', collection)
        phone = metric_provenance('phone_lte_rsrp', collection)
        self.assertEqual(desktop['sources'], ['cellular_modem'])
        self.assertEqual(desktop['started_utc'], '2026-10-28T10:00:00Z')
        self.assertEqual(phone['sources'], ['android_input'])
        self.assertEqual(phone['received_utc'], '2026-10-28T09:59:58Z')
        self.assertEqual(phone['age_ms'], 800)
        self.assertEqual(metric_provenance('rsrp', {})['sources'], [])
        self.assertIn('Phone observation received', provenance_label(phone))
        self.assertIn('Cellular modem', provenance_label(desktop))

    def test_source_filter_keeps_unknown_separate_and_never_merges_phone(self):
        model = {'run_metrics': {'a': {'rsrp': -80}, 'b': {'rsrp': -95}, 'c': {'rsrp': -100}},
                 'run_context': {'a': {'rsrp': {'sources': ['cellular_modem']}},
                                 'b': {'rsrp': {'sources': ['android_import']}},
                                 'c': {'rsrp': {'sources': []}}}}
        self.assertEqual(source_options(model, 'rsrp'), ['cellular_modem', 'android_import', '__unattributed__'])
        self.assertTrue(source_matches(model, 'a', 'rsrp', 'cellular_modem'))
        self.assertFalse(source_matches(model, 'b', 'rsrp', 'cellular_modem'))
        self.assertTrue(source_matches(model, 'c', 'rsrp', '__unattributed__'))

    def test_floor_source_filter_scopes_color_range_to_matching_runs(self):
        steps = [{'run_id': 'a', 'metrics': {'rsrp': -80}}, {'run_id': 'b', 'metrics': {'rsrp': -100}}]
        places = {key: {'kind': 'floor', 'floor_id': 'f1', 'x': .2, 'y': .2} for key in ('a', 'b')}
        context = {'a': {'rsrp': {'sources': ['cellular_modem']}},
                   'b': {'rsrp': {'sources': ['android_import']}}}
        markers, scale = floor_measurements(steps, places, 'f1', 'rsrp',
                                             source_filter='android_import', run_context=context)
        self.assertEqual([m['run_id'] for m in markers], ['b'])
        self.assertEqual((scale['minimum'], scale['maximum']), (-100, -100))


if __name__ == '__main__':
    unittest.main()
