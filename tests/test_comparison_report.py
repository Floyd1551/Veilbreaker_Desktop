import tempfile
import unittest
from pathlib import Path
from veilbreaker.comparison_report import report_html, save_notes, load_notes


class ComparisonReportTests(unittest.TestCase):
    def test_notes_are_directional_and_preserve_unicode(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            save_notes(root, 'a', 'b', 'Moved antenna — café')
            self.assertEqual(load_notes(root, 'a', 'b')['notes'], 'Moved antenna — café')
            self.assertEqual(load_notes(root, 'b', 'a')['notes'], '')
            with self.assertRaises(ValueError):
                save_notes(root, 'a', 'b', 'x' * 2001)

    def test_html_distinguishes_zero_delta_and_withheld(self):
        result = {'site_id': '<site>', 'baseline': {'survey_id': 'a'}, 'current': {'survey_id': 'b'},
                  'settings_match': False, 'rows': [
                      {'point': 'Roof', 'metric': 'latency_ms', 'baseline': 0, 'current': 0, 'delta': 0, 'notes': '', 'baseline_run': 'a1', 'current_run': 'b1'},
                      {'point': 'Lobby', 'metric': 'latency_ms', 'baseline': None, 'current': 2, 'delta': None, 'notes': 'Incomplete collection'}]}
        html = report_html(result, '<script>antenna</script>')
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('Unavailable comparisons', html)
        self.assertIn('Incomplete collection', html)
        self.assertIn('a1', html)
        self.assertIn('b1', html)
        self.assertIn('Not observed', html)
