import copy
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from veilbreaker.map_data import export_geojson
from veilbreaker.mobile_survey_import import load_mobile_survey
from veilbreaker.mobile_survey_map import build_mobile_survey_map


class MobileSurveyMapTests(unittest.TestCase):
    def test_preserves_receiver_location_quality_and_operator_note_without_fabricating_metrics(self):
        capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        capture['observations'][0]['location'] = {'status': 'available', 'source': 'phone', 'provider': 'gps',
            'fix_utc': capture['created_utc'], 'latitude_deg': 0, 'longitude_deg': 0,
            'horizontal_accuracy_m': 5, 'fix_age_ms': 1000, 'mock': False}
        survey = {'format': 'veilbreaker.mobile.survey', 'schema_version': 1, 'survey_id': str(uuid.uuid4()),
                  'name': 'Site', 'created_utc': capture['created_utc'], 'lifecycle': 'open',
                  'points': [{'attached_utc': capture['created_utc'], 'capture': capture, 'operator_note': 'Concrete column'}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'survey.json'; path.write_text(json.dumps(survey), encoding='utf-8')
            loaded = load_mobile_survey(path); before = copy.deepcopy(loaded['survey'])
            model = build_mobile_survey_map(loaded)
            self.assertTrue(model['mobile_survey_preview'])
            self.assertEqual(model['counts']['mapped'], 1)
            row = model['rows'][0]
            self.assertEqual((row['latitude_deg'], row['longitude_deg']), (0, 0))
            self.assertEqual(row['mobile_capture_id'], capture['capture_id'])
            self.assertEqual(row['operator_note'], 'Concrete column')
            self.assertEqual(row['source'], 'phone')
            self.assertEqual(model['run_metrics'], {})
            self.assertEqual(loaded['survey'], before)
            exported = json.loads(export_geojson(model, [row['id']]))
            self.assertEqual(exported['features'][0]['properties']['mobile_capture_id'], capture['capture_id'])
            loaded['survey']['points'][0]['capture']['observations'][0]['location']['latitude_deg'] = 20
            self.assertEqual(build_mobile_survey_map(loaded)['rows'][0]['latitude_deg'], 0)
            with self.assertRaises(ValueError): build_mobile_survey_map(dict(loaded, sha256='incorrect'))

    def test_missing_and_mock_location_are_not_qualified(self):
        capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        capture['observations'][0]['location'] = {'status': 'available', 'source': 'phone', 'provider': 'gps',
            'fix_utc': capture['created_utc'], 'latitude_deg': 35, 'longitude_deg': -86,
            'horizontal_accuracy_m': 5, 'fix_age_ms': 1000, 'mock': True}
        other = copy.deepcopy(capture); other['capture_id'] = str(uuid.uuid4()); other['observations'][0].pop('location')
        survey = {'format': 'veilbreaker.mobile.survey', 'schema_version': 1, 'survey_id': str(uuid.uuid4()),
                  'name': 'Site', 'created_utc': capture['created_utc'], 'lifecycle': 'open',
                  'points': [{'attached_utc': capture['created_utc'], 'capture': value} for value in (capture, other)]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'survey.json'; path.write_text(json.dumps(survey), encoding='utf-8')
            model = build_mobile_survey_map(load_mobile_survey(path))
            self.assertEqual(model['counts']['mapped'], 0)
            self.assertEqual(model['counts']['questionable'], 1)
            self.assertEqual(model['counts']['unpositioned_runs'], 2)
