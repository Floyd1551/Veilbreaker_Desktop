import unittest
from veilbreaker.survey_report import report_html


class SurveyReportTests(unittest.TestCase):
    def test_missing_partial_and_untrusted_text(self):
        session = {'name': '<script>bad</script>', 'steps': [
            {'label': 'Lobby', 'status': 'complete', 'metrics': {'latency_ms': 0}, 'notes': 'café & antenna'},
            {'label': 'Roof', 'status': 'partial', 'metrics': {'latency_ms': 100}},
            {'label': 'Garage', 'status': 'not_run', 'metrics': {}},
        ]}
        html = report_html(session)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('café &amp; antenna', html)
        self.assertIn('Not observed', html)
        self.assertIn('partial', html)
        self.assertIn('1 / 3', html)
        self.assertNotIn('50.0', html)  # Partial measurements excluded from complete-point statistics.
        self.assertIn('100', html)  # Still retained in point detail.

    def test_empty_session(self):
        self.assertIn('No numeric measurements from complete tests', report_html({'steps': []}))
