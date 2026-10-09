import base64
from pathlib import Path
import tempfile
import unittest
from veilbreaker.sdr_visuals import build_visuals, visuals_html


class VisualTests(unittest.TestCase):
    def test_partial_records_and_bounded_waterfall(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sweep.csv'
            path.write_text('d,t,2400000000,2402000000,1000000,2,-70,nan\n' * 130, encoding='utf-8')
            result = build_visuals(path, [(2400.5, -70, -65)], 2400, 2404)
            self.assertEqual(result['record_count'], 128)
            self.assertTrue(result['truncated'])
            for key in ('spectrum_png', 'waterfall_png'):
                self.assertTrue(base64.b64decode(result[key].split(',')[1]).startswith(b'\x89PNG'))
            self.assertIn('Not a calibrated time axis', visuals_html(result))
            self.assertIn('first 128', visuals_html(result))

    def test_blank_power_keeps_its_frequency_gap(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sweep.csv'
            path.write_text('d,t,2400000000,2403000000,1000000,3,-70,,-40\n', encoding='utf-8')
            result = build_visuals(path, [(2400.5, -70, -70), (2402.5, -40, -40)], 2400, 2403)
            self.assertEqual(result['record_count'], 1)
            self.assertFalse(result['truncated'])
            self.assertEqual(result['ceiling_db'], -38)
