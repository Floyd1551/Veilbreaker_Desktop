import copy
import unittest
from test_android_capture import fixture
from veilbreaker.receiver_assessment import build_phone_assessments, apply_phone_assessments
from veilbreaker import core

class ReceiverTests(unittest.TestCase):
    def test_phone_findings_reach_main_report_without_overwriting_desktop(self):
        capture = fixture()
        capture['observations'][0]['cells'][0]['signal']['rsrp']['value'] = -125
        assessments = build_phone_assessments(capture)
        report = core.ProfessionalVeilbreakerEngine().analyze({'rsrp': -80})
        apply_phone_assessments(report, assessments)
        self.assertEqual(report.normalized_metrics['rsrp'], -80)
        self.assertTrue(any('Phone' in f.title for f in report.findings))
        self.assertEqual(len(assessments), 1)

    def test_later_missing_is_not_current_and_cells_remain_separate(self):
        capture = fixture()
        later = copy.deepcopy(capture['observations'][0])
        later['observation_id'] = 'later'
        later['elapsed_realtime_ms'] += 5000
        later['cells'][0]['signal']['rsrp'] = {'value': None, 'unit':'dBm', 'reason':'not_reported'}
        capture['observations'].append(later)
        result = build_phone_assessments(capture)
        self.assertFalse(result[0]['measurements']['rsrp']['current'])
        self.assertEqual(result[0]['measurements']['rsrp']['value'], -95)

    def test_old_cached_sample_is_not_current(self):
        data=fixture()
        data['observations'][0]['cells'][0]['age_ms']=120000
        data['observations'][0]['cells'][0]['signal']['rsrp']['value']=-125
        result=build_phone_assessments(data)
        self.assertFalse(result[0]['measurements']['rsrp']['current'])
        self.assertTrue(result[0]['measurements']['rsrp']['latest_exposed'])
        report=core.ProfessionalVeilbreakerEngine().analyze({})
        apply_phone_assessments(report,result)
        self.assertTrue(any('older than 10 seconds' in f.title for f in report.findings))

    def test_disappeared_cell_is_historical_in_all_surfaces(self):
        data=fixture()
        data['observations'][0]['cells'][0]['signal']['rsrp']['value']=-125
        later=copy.deepcopy(data['observations'][0]);later['observation_id']='later';later['elapsed_realtime_ms']+=5000;later['cells']=[]
        data['observations'].append(later)
        report=core.ProfessionalVeilbreakerEngine().analyze({})
        apply_phone_assessments(report,build_phone_assessments(data))
        self.assertTrue(any('sample freshness: historical' in line for line in report.summary))
        self.assertTrue(all('historical' in h.title for h in report.hypotheses if h.hypothesis_id.startswith('PHONE-')))
