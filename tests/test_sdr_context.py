import json
from pathlib import Path
import tempfile
import unittest

from veilbreaker.bandplan import load_plan, bands_at, default_plan
from veilbreaker.scenarios import scenario_help
from veilbreaker.sdr_report import build_sdr_report, report_html


class ContextTests(unittest.TestCase):
    def test_scenarios_explain_actual_behavior(self):
        self.assertIn('same', scenario_help('private_apn'))
        self.assertIn('80', scenario_help('realtime_voice'))
        self.assertIn('does not', scenario_help('field_validation'))

    def test_default_reference_boundaries(self):
        plan = default_plan()
        self.assertEqual(plan['region'], 'US')
        self.assertEqual(len(plan['bands']), 154)
        self.assertTrue(bands_at(plan, 2402))
        self.assertNotIn('Wi-Fi 2.4 GHz Channel 1 (center 2412 MHz)', [b['label'] for b in bands_at(plan, 2422)])

    def test_external_formats_and_frequency_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = {'min_mhz': 1575.42, 'max_mhz': 1575.42, 'band': 'GNSS reference', 'expected_use': 'Center frequency only', 'source': 'Supplied reference'}
            (root / 'plan.json').write_text(json.dumps([row]), encoding='utf-8')
            (root / 'plan.csv').write_text('min_mhz,max_mhz,band,expected_use,source\n1575.42,1575.42,GNSS reference,Center frequency only,Supplied reference\n', encoding='utf-8')
            plans = [load_plan(root / f'plan.{extension}') for extension in ('json', 'csv')]
            self.assertEqual(plans[0], plans[1])
            self.assertEqual(plans[0]['bands'][0]['kind'], 'marker')
            self.assertEqual(len(bands_at(plans[0], 1575.42)), 1)
            self.assertFalse(bands_at(plans[0], 1575.43))

    def test_import_overlap_and_invalid_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.csv'
            path.write_text('min_mhz,max_mhz,label\n100,200,A\n150,250,B\n', encoding='utf-8')
            self.assertEqual(len(bands_at(load_plan(path), 175)), 2)
            for low, high in [('nan', '200'), ('200', '100'), ('0', 'inf')]:
                path.write_text(f'min_mhz,max_mhz,label\n{low},{high},A\n', encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_plan(path)
            path = Path(directory) / 'huge.json'
            path.write_text(json.dumps({'bands': [{'min_mhz': 0, 'max_mhz': 10**400, 'label': 'Huge'}]}), encoding='utf-8')
            with self.assertRaises(ValueError):
                load_plan(path)

    def test_report_retains_unknown_capture_and_escapes_html(self):
        report = build_sdr_report([{'label': '<script>', 'csv_path': 'missing.csv',
                                  'min_mhz': 2400, 'max_mhz': 2500, 'bin_width_hz': 1000000}], {'site_id': '<site>'})
        self.assertEqual(report['ranges'][0]['status'], 'unavailable')
        self.assertIsNone(report['ranges'][0]['peak'])
        self.assertNotIn('<script>', report_html(report))
        self.assertIn('&lt;site&gt;', report_html(report))

    def test_report_partial_range_and_recorded_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sweep.csv'
            path.write_text('d,t,2400000000,2404000000,1000000,4,-70,-60,-50,-40\n', encoding='utf-8')
            path.with_suffix('.capture.json').write_text(json.dumps({'returncode': 1, 'settings': {'lna_gain_db': 16}}), encoding='utf-8')
            report = build_sdr_report([{'label': 'test', 'csv_path': str(path), 'min_mhz': 2400,
                                       'max_mhz': 2410, 'bin_width_hz': 1000000}], {})
            row = report['ranges'][0]
            self.assertEqual(row['status'], 'partial')
            self.assertEqual(row['bin_count'], 4)
            self.assertEqual(row['capture']['settings']['lna_gain_db'], 16)
            self.assertEqual(row['peak']['maximum_db'], -40)
            self.assertLess(row['coverage_pct'], 100)

    def test_missing_bins_do_not_inflate_coverage(self):
        from veilbreaker import core
        from dataclasses import asdict
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sweep.csv'
            path.write_text('d,t,2400000000,2401000000,1000000,1,-60\nd,t,2403000000,2404000000,1000000,1,-50\n', encoding='utf-8')
            path.with_suffix('.capture.json').write_text('{"returncode":0}', encoding='utf-8')
            summary = core.HackRFCollector.summarize('gaps', core.SDRRange('gaps',2400,2404), core.HackRFCollector.parse_sweep_csv(path), path)
            row = build_sdr_report([asdict(summary)], {})['ranges'][0]
            self.assertEqual(row['coverage_pct'], 50)
            self.assertEqual(row['status'], 'partial')

if __name__ == '__main__':
    unittest.main()
