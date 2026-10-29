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

    def test_observations_report_original_and_edited_timestamps(self):
        html=report_html({'steps': [], 'observations': [{'id':'one','source':'operator',
            'recorded_utc':'2026-10-29T09:00:00Z','updated_utc':'2026-10-29T10:00:00Z',
            'category':'Obstruction','material':'Concrete','description':'Pillar','author':'Tech'}]})
        self.assertIn('Recorded UTC',html)
        self.assertIn('Last edited UTC',html)
        self.assertIn('2026-10-29T09:00:00Z',html)
        self.assertIn('2026-10-29T10:00:00Z',html)

    def test_embedded_imagery_and_stale_warning(self):
        html = report_html({'steps': []}, dict(image=b'png', source='<source>',
            attribution='A & B', imagery_date=None, prepared_utc='2026-10-20',
            bounds=[-97,32,-96,33], crs='EPSG:4326', points=[], missing_points=2,
            imagery_type='aerial', manual_area=True, warning='Positions changed'))
        self.assertIn('data:image/png;base64,cG5n', html)
        self.assertIn('&lt;source&gt;', html)
        self.assertIn('A &amp; B', html)
        self.assertIn('Positions changed', html)
        self.assertIn('Manually selected area', html)
        self.assertIn('Unknown', html)
        self.assertIn('Survey imagery unavailable', report_html({'steps': []},
            dict(image=None, warning='Survey imagery unavailable')))
