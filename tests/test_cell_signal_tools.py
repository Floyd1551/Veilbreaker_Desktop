import json
import unittest

from veilbreaker.cell_signal_tools import interpret_signal


class CellSignalToolsTests(unittest.TestCase):
    def test_missing_values_remain_missing_and_zero_is_valid(self):
        result = interpret_signal('LTE', {'rsrp': '-85', 'rsrq': '', 'sinr': '0'})
        self.assertEqual(result['metrics']['rsrq'], None)
        self.assertEqual(result['metrics']['sinr'], 0)
        self.assertIn('rsrq', result['missing'])
        self.assertEqual(result['pattern']['code'], 'strong_power_weak_quality')
        self.assertEqual(result['kind'], 'operator-entered interpretation')
        json.dumps(result, allow_nan=False)

    def test_weak_but_clean_pattern_and_radio_names(self):
        nr = interpret_signal('NR', {'rsrp': -112, 'rsrq': -10, 'sinr': 16})
        self.assertEqual(nr['pattern']['code'], 'weak_power_clean_quality')
        self.assertEqual([row['label'] for row in nr['rows']], ['SS-RSRP', 'SS-RSRQ', 'SS-SINR'])
        self.assertIn('NR', nr['limitations'])
        lte = interpret_signal('LTE', {'rsrp': -95, 'rsrq': -9, 'sinr': 15})
        self.assertEqual(lte['pattern']['code'], 'no_specific_pattern')

    def test_partial_input_does_not_invent_correlation(self):
        result = interpret_signal('LTE', {'rsrp': -85, 'rsrq': None, 'sinr': None})
        self.assertEqual(result['pattern']['code'], 'insufficient_pair')
        self.assertEqual(len(result['rows']), 1)

    def test_rsrq_is_part_of_the_interpretation_without_claiming_a_cause(self):
        limited = interpret_signal('LTE', {'rsrq': -18})
        self.assertEqual(limited['pattern']['code'], 'rsrq_limited_context')
        self.assertIn('cannot identify', limited['pattern']['explanation'])
        disagree = interpret_signal('NR', {'rsrp': -94, 'rsrq': -18, 'sinr': 18})
        self.assertEqual(disagree['pattern']['code'], 'quality_metrics_differ')
        both = interpret_signal('LTE', {'rsrp': -94, 'rsrq': -18, 'sinr': 2})
        self.assertEqual(both['pattern']['code'], 'quality_metrics_low')

    def test_invalid_and_empty_inputs(self):
        with self.assertRaises(ValueError):
            interpret_signal('LTE', {})
        for radio, values in (('GSM', {'rsrp': -90}), ('LTE', {'rsrp': float('nan')}),
                              ('NR', {'sinr': True}), ('LTE', {'rsrq': -100}),
                              ('NR', {'rsrp': -200})):
            with self.subTest(radio=radio, values=values), self.assertRaises(ValueError):
                interpret_signal(radio, values)


if __name__ == '__main__':
    unittest.main()
