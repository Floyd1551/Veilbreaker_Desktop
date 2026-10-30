import copy
import unittest

from test_android_capture import fixture
from veilbreaker.cellular_report import build_report
from veilbreaker.survey_live_cellular import reduce_live_cell_report, live_cell_groups


class LiveCellSurveyTests(unittest.TestCase):
    def test_explicit_groups_keep_full_identity_and_samples_separate(self):
        capture=fixture();capture['collection']['mode']='session'
        first=capture['observations'][0]['cells'][0];first['identity']['tac']=42
        second=copy.deepcopy(first);second['identity']['cell_id']='5678'
        second['signal']['rsrp']['value']=-110
        capture['observations'][0]['cells'].append(second)
        groups=live_cell_groups(build_report(capture))
        self.assertEqual(len(groups),2)
        self.assertNotEqual(groups[0]['key'],groups[1]['key'])
        self.assertEqual({g['metrics']['live_phone_lte_rsrp'] for g in groups},{-95,-110})
        self.assertEqual({g['context']['live_phone_lte_rsrp']['cell_identity']['cell_id'] for g in groups},{'1234','5678'})

    def test_incomplete_identity_is_not_a_comparable_group(self):
        capture=fixture();capture['collection']['mode']='session'
        self.assertEqual(live_cell_groups(build_report(capture)),[])

    def test_group_identity_does_not_merge_different_receiver_models(self):
        capture=fixture();capture['collection']['mode']='session';capture['observations'][0]['cells'][0]['identity']['tac']=42
        first=live_cell_groups(build_report(capture))[0]
        capture['device']['model']='Different receiver'
        second=live_cell_groups(build_report(capture))[0]
        self.assertNotEqual(first['key'],second['key'])

    def test_invalid_full_identity_is_not_offered(self):
        capture=fixture();capture['collection']['mode']='session'
        identity=capture['observations'][0]['cells'][0]['identity']
        identity['tac']=70000
        self.assertEqual(live_cell_groups(build_report(capture)),[])

    def test_channel_changes_are_separate_and_visible_in_labels(self):
        capture=fixture();capture['collection']['mode']='session'
        first=capture['observations'][0]['cells'][0];first['identity']['tac']=42
        second=copy.deepcopy(first);second['identity']['earfcn']=200
        capture['observations'][0]['cells'].append(second)
        groups=live_cell_groups(build_report(capture))
        self.assertEqual(len(groups),2)
        self.assertNotEqual(groups[0]['key'],groups[1]['key'])
        self.assertNotEqual(groups[0]['label'],groups[1]['label'])

    def test_omitted_entries_disable_automatic_reduction_but_keep_explicit_groups(self):
        capture=fixture();capture['collection']['mode']='session';capture['observations'][0]['cells'][0]['identity']['tac']=42
        report=build_report(capture);report['omitted']=3
        automatic=reduce_live_cell_report(report)
        self.assertEqual(automatic['metrics'],{})
        self.assertIn('omitted 3',automatic['warning'])
        self.assertEqual(len(live_cell_groups(report)),1)

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
