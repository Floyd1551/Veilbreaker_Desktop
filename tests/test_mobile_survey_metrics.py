import copy
import json
import unittest
from pathlib import Path

from veilbreaker.mobile_survey_metrics import aligned_mobile_metrics


class MobileSurveyMetricsTests(unittest.TestCase):
    def setUp(self):
        self.capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        self.capture['device']['companion_version'] = '0.8.25-dev'
        obs = self.capture['observations'][0]
        obs['location'] = dict(status='available', source='phone', provider='gps', fix_utc=obs['received_utc'],
            latitude_deg=34.7, longitude_deg=-86.6, horizontal_accuracy_m=5, fix_age_ms=1000, mock=False)

    def test_only_same_observation_metrics_are_returned_with_provenance(self):
        result = aligned_mobile_metrics(self.capture)
        row = result['snapshot-1']
        self.assertEqual(row['metrics']['phone_lte_rsrp'], -95)
        self.assertEqual(row['context']['phone_lte_rsrp']['observation_id'], 'snapshot-1')
        self.assertEqual(row['context']['phone_lte_rsrp']['location_after_modem_ms'], 500)
        self.assertEqual(row['context']['phone_lte_rsrp']['cell_identity']['cell_id'], '1234')
        self.assertNotIn('phone_nr_rsrp', row['metrics'])

    def test_rejects_stale_ambiguous_and_unknown_evidence(self):
        for case in ('old_modem', 'unknown_age', 'offset', 'mock', 'unknown_mock', 'external_location', 'poor_accuracy', 'multiple', 'neighbor', 'unknown_role', 'unverified_version'):
            capture = copy.deepcopy(self.capture)
            obs = capture['observations'][0]; cell = obs['cells'][0]
            if case == 'old_modem': cell['age_ms'] = 10001
            if case == 'unknown_age': cell['age_ms'] = None
            if case == 'offset': cell['age_ms'] = 4000
            if case == 'mock': obs['location']['mock'] = True
            if case == 'unknown_mock': obs['location']['mock'] = None
            if case == 'external_location': obs['location']['source'] = 'external_receiver'
            if case == 'poor_accuracy': obs['location']['horizontal_accuracy_m'] = 26
            if case == 'multiple': obs['cells'].append(copy.deepcopy(cell))
            if case == 'neighbor': cell['registered'] = False
            if case == 'unknown_role': cell['connection_status'] = 'unknown'
            if case == 'unverified_version': capture['device']['companion_version'] = 'other'
            with self.subTest(case=case): self.assertEqual(aligned_mobile_metrics(capture), {})

    def test_repeated_modem_sample_not_reused_for_another_location(self):
        second = copy.deepcopy(self.capture['observations'][0])
        second['observation_id'] = 'snapshot-2'
        second['elapsed_realtime_ms'] += 1000
        second['cells'][0]['age_ms'] += 1000
        self.capture['observations'].append(second)
        self.assertEqual(list(aligned_mobile_metrics(self.capture)), ['snapshot-1'])

    def test_nr_values_and_offset_boundary(self):
        cell = self.capture['observations'][0]['cells'][0]
        cell['radio'] = 'NR'
        cell['age_ms'] = 3000
        cell['signal'] = {'ss_rsrp': {'value': -105, 'unit': 'dBm'},
                          'ss_sinr': {'value': 0, 'unit': 'dB'}}
        row = aligned_mobile_metrics(self.capture)['snapshot-1']
        self.assertEqual(row['metrics'], {'phone_nr_rsrp': -105, 'phone_nr_sinr': 0})
        self.assertEqual(row['context']['phone_nr_sinr']['location_after_modem_ms'], 2000)

    def test_bad_capture_is_rejected_instead_of_interpreted(self):
        self.capture['observations'][0]['cells'][0]['signal']['rsrp']['unit'] = 'W'
        with self.assertRaises(ValueError): aligned_mobile_metrics(self.capture)
