import os
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QLabel
from veilbreaker.core import AppConfig
from veilbreaker.path_assessment_report import assessment_html
from veilbreaker.path_assessment_ui import PathAssessmentDialog
from veilbreaker.terrain_profile import assess_profile


class PhysicalStructureAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def assessment(self, candidate):
        return dict(
            profile=assess_profile([0, 10, 20], [100, 100, 100], 2, 10),
            terrain=dict(dem=dict(source='Terrain fixture', vertical_datum='NAVD88', units='m',
                                  crs='EPSG:4326', sha256='abc', sample_spacing_m=10),
                         endpoints=[[-86.6, 34.7], [-86.5, 34.8]]),
            endpoint_context=dict(candidate=candidate),
        )

    def test_structure_report_discloses_source_and_escapes_fields(self):
        candidate = dict(reference_kind='physical structure', structure_id='ASR <42>', owner='A & B',
                         verification='Operator-selected physical structure; serving relationship unverified',
                         selection_method='operator_selected',
                         source='FCC ASR <script>', source_date='2026-10-25', license='Public & source terms',
                         pack_name='Region', pack_id='pack-1', sha256='a' * 64,
                         bounds_wgs84=[-87, 34, -86, 35], coverage_note='Incomplete & stale')
        report = assessment_html(self.assessment(candidate))
        for expected in ('Physical structure reference', 'ASR &lt;42&gt;', 'A &amp; B',
                         'FCC ASR &lt;script&gt;', '2026-10-25', 'Public &amp; source terms',
                         'pack-1', 'a' * 64, 'Incomplete &amp; stale', 'Operator selected'):
            self.assertIn(expected, report)
        self.assertIn('does not establish a serving cell', report)
        self.assertIn('NAD83', report)
        self.assertNotIn('FCC ASR <script>', report)

    def test_existing_cell_candidate_keeps_legacy_report(self):
        report = assessment_html(self.assessment(dict(verification='Estimated reference')))
        self.assertIn('Estimated reference', report)
        self.assertNotIn('Physical structure reference', report)

    def test_structure_report_shows_receiver_location_provenance(self):
        assessment = self.assessment(dict(reference_kind='physical structure', structure_id='42'))
        assessment['endpoint_context'].update(
            map_receiver=dict(run_id='run<1>', observation_id='Operator placement', manual=True,
                              placed_utc='2026-11-18T12:00:00Z', source_kind='mobile_survey_capture'),
            observation=dict(position_source='operator_map_placement',
                             location=dict(latitude_deg=34.7, longitude_deg=-86.6)))
        report = assessment_html(assessment)
        self.assertIn('Operator map placement', report)
        self.assertIn('run&lt;1&gt;', report)
        self.assertIn('Operator placement', report)
        self.assertIn('2026-11-18T12:00:00Z', report)
        self.assertIn('not GPS evidence', report)

    def test_report_does_not_call_network_provider_gps(self):
        assessment = self.assessment(dict(reference_kind='physical structure', structure_id='42'))
        assessment['endpoint_context'].update(
            map_receiver=dict(run_id='run-1', observation_id='1', manual=False),
            observation=dict(position_source='qualified_gps', location=dict(latitude_deg=34.7,
                longitude_deg=-86.6, source='phone', provider='network')))
        report = assessment_html(assessment)
        self.assertIn('Qualified recorded location', report)
        self.assertIn('network', report)
        self.assertIn('phone', report)
        self.assertNotIn('Qualified recorded GPS fix', report)
        self.assertNotIn('GPS fix time', report)

    def test_structure_without_selection_provenance_does_not_claim_operator_selected(self):
        report = assessment_html(self.assessment(dict(reference_kind='physical structure', structure_id='ASR-42')))
        self.assertIn('Not recorded', report)
        self.assertNotIn('Operator selected', report)

    def test_physical_structure_height_never_prefills_antenna_height(self):
        with tempfile.TemporaryDirectory() as folder:
            context = dict(observation=dict(location=dict(longitude_deg=-86.6, latitude_deg=34.7)),
                           candidate=dict(reference_kind='physical structure', lon=-86.5, lat=34.8,
                                          height_agl_m=100, structure_id='ASR-42'))
            dialog = PathAssessmentDialog(None, AppConfig(data_dir=folder), context)
            try:
                self.assertEqual(dialog.site.value(), -1)
                self.assertEqual(dialog.receiver.value(), -1)
                labels = ' '.join(label.text() for label in dialog.findChildren(QLabel))
                self.assertIn('physical structure', labels.lower())
                self.assertIn('serving', labels.lower())
                self.assertIn('mast height', labels.lower())
                dialog.resize(900, 650)
                dialog.show()
                self.app.processEvents()
                self.assertLessEqual(dialog.width(), 900)
            finally:
                dialog.close()


if __name__ == '__main__':
    unittest.main()
