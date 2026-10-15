import copy
import unittest
from test_android_capture import fixture
from veilbreaker.cellular_report import build_report, report_html

class CellularReportTests(unittest.TestCase):
    def test_null_bands_and_later_exposed_metadata(self):
        data = fixture()
        data['observations'][0]['cells'][0]['identity']['bands'] = None
        self.assertEqual(build_report(data)['cells'][0]['band'], 'Not exposed')
        later = copy.deepcopy(data['observations'][0])
        later['observation_id'] = 'later'
        later['elapsed_realtime_ms'] += 5000
        later['cells'][0]['identity']['bands'] = [1]
        data['observations'].append(later)
        report = build_report(data)
        self.assertEqual(len(report['cells']), 1)
        self.assertEqual(report['cells'][0]['band'], 'LTE 1 (reported)')
        self.assertIsNone(data['observations'][0]['cells'][0]['identity']['bands'])

    def test_readable_identity_missing_values_and_escaping(self):
        data = fixture()
        data['subscriptions'][0]['network_operator'] = '<Carrier>'
        report = build_report(data)
        cell = report['cells'][0]
        self.assertEqual(cell['carrier'], '<Carrier>')
        self.assertEqual(cell['band'], 'LTE 1 (reported)')
        html = report_html(report)
        self.assertIn('&lt;Carrier&gt;', html)
        self.assertIn('Not exposed', html)
        self.assertIn('RSRP', html)
        self.assertIn('1234', html)
        self.assertNotIn('<Carrier>', html)

    def test_trends_keep_cells_and_rat_metrics_separate(self):
        data = fixture()
        other = copy.deepcopy(data['observations'][0]); other['observation_id'] = 'two'
        other['elapsed_realtime_ms'] += 5000
        other['cells'][0]['signal']['rsrp']['value'] = -105
        data['observations'].append(other)
        report = build_report(data)
        self.assertEqual(report['cells'][0]['signals']['rsrp']['median'], -100)
        self.assertIn('data:image/png;base64,', report_html(report))
        self.assertNotIn('sinr', report['cells'][0]['signals'])
