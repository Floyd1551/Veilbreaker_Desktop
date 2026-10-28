import unittest

from veilbreaker.survey_metrics import available_metrics, metric_scale, clean_metrics, point_metric


class SurveyMetricTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
