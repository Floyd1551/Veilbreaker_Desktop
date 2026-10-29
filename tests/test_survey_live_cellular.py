import copy
import unittest

from test_android_capture import fixture
from veilbreaker.cellular_report import build_report
from veilbreaker.survey_live_cellular import reduce_live_cell_report


class LiveCellSurveyTests(unittest.TestCase):
    def test_one_stable_cell_uses_fresh_uncached_median_and_receipt_window(self):
        capture = fixture()
        capture['collection']['mode'] = 'session'
        second = copy.deepcopy(capture['observations'][0])
        second['observation_id'] = 'second'
        second['received_utc'] = '2026-10-10T12:00:05Z'
        second['elapsed_realtime_ms'] = 15000
        second['cells'][0]['signal']['rsrp']['value'] = -105
        capture['observations'].append(second)
        cached = copy.deepcopy(second)
        cached['observation_id'] = 'cached'
        cached['received_utc'] = '2026-10-10T12:00:06Z'
        cached['elapsed_realtime_ms'] = 16000
        cached['cells'][0]['age_ms'] = 2500
        cached['cells'][0]['signal']['rsrp']['value'] = -120
        capture['observations'].append(cached)
        reduced = reduce_live_cell_report(build_report(capture))
        self.assertEqual(reduced['metrics']['live_phone_lte_rsrp'], -100)
        detail = reduced['context']['live_phone_lte_rsrp']
        self.assertEqual(detail['sample_count'], 2)
        self.assertEqual(detail['statistic'], 'median')
        self.assertEqual(detail['window_start_utc'], '2026-10-10T12:00:01Z')
        self.assertEqual(detail['window_end_utc'], '2026-10-10T12:00:05Z')
        self.assertEqual(detail['cell_identity']['cell_id'], '1234')
        self.assertEqual(detail['sources'], ['android_usb'])

    def test_multiple_registered_groups_never_blend_into_one_scalar(self):
        capture = fixture()
        capture['collection']['mode'] = 'session'
        extra = copy.deepcopy(capture['observations'][0]['cells'][0])
        extra['identity']['cell_id'] = 'different'
        capture['observations'][0]['cells'].append(extra)
        reduced = reduce_live_cell_report(build_report(capture))
        self.assertEqual(reduced['metrics'], {})
        self.assertIn('multiple', reduced['warning'].lower())

    def test_unknown_age_or_missing_signal_does_not_become_a_value(self):
        capture = fixture()
        capture['collection']['mode'] = 'session'
        capture['observations'][0]['cells'][0]['age_ms'] = None
        reduced = reduce_live_cell_report(build_report(capture))
        self.assertEqual(reduced['metrics'], {})
        self.assertIn('fresh', reduced['warning'].lower())


if __name__ == '__main__':
    unittest.main()
