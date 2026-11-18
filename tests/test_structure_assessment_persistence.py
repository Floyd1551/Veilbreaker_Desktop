import json
import os
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from veilbreaker.core import AppConfig
from veilbreaker import cell_context
from veilbreaker.map_sources import load_survey_map_data
from veilbreaker.survey import create_survey, export_session
from veilbreaker.survey_mobile_evidence import attach_mobile_survey, read_attached_mobile_surveys
from veilbreaker.survey_spatial import save_placement, clear_placement
from veilbreaker.terrain_profile import assess_profile


class StructureAssessmentPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cfg = AppConfig(data_dir=self.temp.name)
        self.path = create_survey(self.cfg, 'Test', [{}])['survey_path']
        capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        capture['observations'][0]['location'] = dict(status='available', source='phone', provider='gps',
            fix_utc=capture['created_utc'], latitude_deg=35, longitude_deg=-86,
            horizontal_accuracy_m=5, fix_age_ms=1000, mock=False)
        source = Path(self.temp.name) / 'mobile.json'
        source.write_text(json.dumps(dict(format='veilbreaker.mobile.survey', schema_version=1,
            survey_id=str(uuid.uuid4()), name='Mobile', created_utc=capture['created_utc'],
            lifecycle='open', points=[dict(attached_utc=capture['created_utc'], capture=capture)])), encoding='utf-8')
        self.session = attach_mobile_survey(self.cfg, self.path, source)
        self.key = 'mobile-' + self.session['mobile_sources'][0]['sha256'] + '-1'

    def assessment(self, row):
        keys = ('run_id', 'observation_id', 'latitude_deg', 'longitude_deg', 'manual',
                'placed_utc', 'source_kind', 'mobile_capture_id', 'mobile_survey_sha256',
                'source', 'provider', 'fix_utc', 'received_utc', 'horizontal_accuracy_m', 'fix_age_ms', 'mock')
        receiver = {k: row.get(k) for k in keys if k in row}
        receiver['manual'] = bool(row.get('manual'))
        return dict(profile=assess_profile([0, 10, 20], [100, 100, 100], 2, 10),
            terrain=dict(dem=dict(source='fixture', vertical_datum='NAVD88', units='m',
                crs='EPSG:4326', sha256='abc', sample_spacing_m=10),
                endpoints=[[row['longitude_deg'], row['latitude_deg']], [-86.5, 34.8]]),
            endpoint_context=dict(map_receiver=receiver, observation=dict(position_source=
                'operator_map_placement' if receiver['manual'] else 'qualified_gps',
                location=dict(latitude_deg=row['latitude_deg'], longitude_deg=row['longitude_deg'])),
                candidate=dict(reference_kind='physical structure', structure_id='42', selection_method='operator_selected',
                               lat=34.8, lon=-86.5)))

    def row(self, manual=False):
        return next(row for row in load_survey_map_data(self.cfg, self.path)['rows']
                    if row.get('mobile_capture_id') and bool(row.get('manual')) == manual)

    def test_append_preserves_legacy_context_reopens_and_exports(self):
        cell_context.save_context(self.cfg, self.path, dict(rows=[], dataset=dict(attribution='Existing credit')))
        cell_context.append_structure_assessment(self.cfg, self.path, self.assessment(self.row()))
        loaded = cell_context.load_context(self.cfg, self.path)
        self.assertFalse(loaded['stale'])
        self.assertEqual(loaded['context']['dataset']['attribution'], 'Existing credit')
        self.assertEqual(len(loaded['context']['assessments']), 1)
        with zipfile.ZipFile(export_session(self.cfg, self.path)) as archive:
            self.assertIn('Existing credit', archive.read('survey_report.html').decode())
            self.assertEqual(len(json.loads(archive.read('cell-context.json'))['assessments']), 1)

    def test_manual_mobile_placement_stays_manual_and_becomes_stale_when_removed(self):
        save_placement(self.cfg, self.path, self.key, dict(kind='geographic', latitude=34.7, longitude=-86.6))
        assessment = self.assessment(self.row(manual=True))
        cell_context.append_structure_assessment(self.cfg, self.path, assessment)
        saved = cell_context.load_context(self.cfg, self.path)
        self.assertFalse(saved['stale'])
        self.assertEqual(saved['context']['assessments'][0]['endpoint_context']['observation']['position_source'], 'operator_map_placement')
        clear_placement(self.cfg, self.path, self.key)
        self.assertTrue(cell_context.load_context(self.cfg, self.path)['stale'])
        with self.assertRaisesRegex(ValueError, 'receiver'):
            cell_context.append_structure_assessment(self.cfg, self.path, assessment)

    def test_cell_reference_resave_preserves_newer_structure_assessments(self):
        assessment = self.assessment(self.row())
        cell_context.append_structure_assessment(self.cfg, self.path, assessment)
        # Simulate a cell-reference dialog opened before the map assessment was saved.
        cell_context.save_context(self.cfg, self.path, dict(runs=[], assessments=[]))
        saved = cell_context.load_context(self.cfg, self.path)['context']
        self.assertEqual(saved['assessments'], [assessment])
        # A dialog that already contains it must not duplicate it.
        cell_context.save_context(self.cfg, self.path, saved)
        self.assertEqual(cell_context.load_context(self.cfg, self.path)['context']['assessments'], [assessment])

    def test_changed_mobile_evidence_or_snapshot_rejected(self):
        assessment = self.assessment(self.row())
        altered = self.assessment(self.row())
        altered['endpoint_context']['map_receiver']['latitude_deg'] += .1
        with self.assertRaisesRegex(ValueError, 'receiver'):
            cell_context.append_structure_assessment(self.cfg, self.path, altered)
        altered = self.assessment(self.row())
        altered['terrain']['endpoints'][1][0] += .1
        with self.assertRaisesRegex(ValueError, 'receiver'):
            cell_context.append_structure_assessment(self.cfg, self.path, altered)
        cell_context.append_structure_assessment(self.cfg, self.path, assessment)
        source = read_attached_mobile_surveys(self.cfg, self.path, self.session)[0]
        Path(source['path']).write_text('{}')
        self.assertTrue(cell_context.load_context(self.cfg, self.path)['stale'])
        with self.assertRaisesRegex(ValueError, 'receiver'):
            cell_context.append_structure_assessment(self.cfg, self.path, assessment)

    def test_changed_fix_with_identical_coordinates_is_stale(self):
        assessment = self.assessment(self.row())
        cell_context.append_structure_assessment(self.cfg, self.path, assessment)
        changed = load_survey_map_data(self.cfg, self.path)
        row = next(row for row in changed['rows'] if row.get('mobile_capture_id'))
        row['fix_utc'] = '2026-11-18T22:00:00Z'
        with patch('veilbreaker.map_sources.load_survey_map_data', return_value=changed):
            self.assertTrue(cell_context.load_context(self.cfg, self.path)['stale'])
            with self.assertRaisesRegex(ValueError, 'receiver'):
                cell_context.append_structure_assessment(self.cfg, self.path, assessment)

    def test_new_and_legacy_qualified_location_labels_reopen(self):
        legacy = self.assessment(self.row())
        cell_context.append_structure_assessment(self.cfg, self.path, legacy)
        current = self.assessment(self.row())
        current['endpoint_context']['observation']['position_source'] = 'qualified_location'
        cell_context.append_structure_assessment(self.cfg, self.path, current)
        loaded = cell_context.load_context(self.cfg, self.path)
        self.assertFalse(loaded['stale'])
        self.assertEqual(len(loaded['context']['assessments']), 2)


if __name__ == '__main__':
    unittest.main()
