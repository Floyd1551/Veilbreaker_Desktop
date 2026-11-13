import json
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path

from veilbreaker import core
from veilbreaker.survey import create_survey, export_session, read_session, set_lifecycle
from veilbreaker.survey_mobile_evidence import attach_mobile_survey, read_attached_mobile_surveys
from veilbreaker.map_sources import load_survey_map_data
from veilbreaker.evidence import verify_bundle


class SurveyMobileEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = core.AppConfig(data_dir=str(self.root))
        self.path = create_survey(self.config, 'Test', [{}])['survey_path']
        capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        self.source = self.root / 'mobile.json'
        self.source.write_text(json.dumps(dict(format='veilbreaker.mobile.survey', schema_version=1,
            survey_id=str(uuid.uuid4()), name='Mobile site', created_utc=capture['created_utc'],
            lifecycle='open', points=[dict(attached_utc=capture['created_utc'], capture=capture,
                                         operator_note='Near pillar')])), encoding='utf-8')

    def test_attach_reopen_and_export_original_without_creating_runs(self):
        original = self.source.read_bytes()
        session = attach_mobile_survey(self.config, self.path, self.source)
        self.assertEqual(len(session['steps']), 1)
        self.assertEqual(len(session['mobile_sources']), 1)
        self.source.unlink()
        reopened = read_session(self.config, self.path)
        loaded = read_attached_mobile_surveys(self.config, self.path, reopened)
        self.assertEqual(loaded[0]['raw_bytes'], original)
        self.assertEqual(loaded[0]['survey']['points'][0]['operator_note'], 'Near pillar')
        bundle = export_session(self.config, self.path)
        self.assertEqual(verify_bundle(bundle)['status'], 'verified')
        with zipfile.ZipFile(bundle) as archive:
            name = 'mobile-survey-' + loaded[0]['sha256'] + '.json'
            self.assertEqual(archive.read(name), original)
            self.assertIn('Mobile site', archive.read('survey_report.html').decode('utf-8'))
            self.assertIn('Near pillar', archive.read('survey_report.html').decode('utf-8'))

    def test_duplicates_completed_and_corrupt_copy_are_rejected(self):
        session = attach_mobile_survey(self.config, self.path, self.source)
        with self.assertRaisesRegex(ValueError, 'already'):
            attach_mobile_survey(self.config, self.path, self.source)
        saved = read_attached_mobile_surveys(self.config, self.path, session)[0]
        Path(saved['path']).write_text('{}')
        with self.assertRaises(ValueError): export_session(self.config, self.path)
        set_lifecycle(self.config, self.path, True)
        with self.assertRaisesRegex(ValueError, 'Reopen'):
            attach_mobile_survey(self.config, self.path, self.source)

    def test_map_identifies_mobile_capture_and_never_fabricates_metrics(self):
        survey = json.loads(self.source.read_text(encoding='utf-8'))
        capture = survey['points'][0]['capture']
        capture['observations'][0]['location'] = dict(status='available', source='phone', provider='gps',
            fix_utc=capture['created_utc'], latitude_deg=35, longitude_deg=-86,
            horizontal_accuracy_m=5, fix_age_ms=1000, mock=False)
        self.source.write_text(json.dumps(survey), encoding='utf-8')
        attach_mobile_survey(self.config, self.path, self.source)
        model = load_survey_map_data(self.config, self.path)
        row = next(r for r in model['rows'] if r.get('mobile_capture_id'))
        self.assertEqual(row['mobile_capture_id'], capture['capture_id'])
        self.assertEqual(row['operator_note'], 'Near pillar')
        self.assertEqual(row['source_kind'], 'mobile_survey_capture')
        self.assertNotIn(row['run_id'], model['run_metrics'])

    def test_map_includes_operator_mobile_position_without_calling_it_gps(self):
        session = attach_mobile_survey(self.config, self.path, self.source)
        digest = session['mobile_sources'][0]['sha256']
        key = 'mobile-' + digest + '-1'
        folder = Path(self.path).parent / 'spatial' / Path(self.path).stem
        folder.mkdir(parents=True)
        (folder / 'spatial.json').write_text(json.dumps(dict(schema_version=1, floors={}, history=[],
            placements={key: dict(kind='geographic', latitude=34.7, longitude=-86.6,
                                  source='operator', placed_utc='2026-11-12T12:00:00Z')})), encoding='utf-8')
        model = load_survey_map_data(self.config, self.path)
        row = next(r for r in model['rows'] if r.get('manual'))
        self.assertEqual(row['source_kind'], 'mobile_survey_capture')
        self.assertEqual(row['source'], 'operator')
        self.assertFalse(row['quality']['qualified'])
        self.assertEqual(row['operator_note'], 'Near pillar')
        self.assertNotIn(key, model['run_metrics'])

    def test_retry_reuses_verified_orphan_without_overwriting(self):
        from veilbreaker.mobile_survey_import import load_mobile_survey
        loaded = load_mobile_survey(self.source)
        folder = Path(self.path).parent / 'mobile-evidence' / Path(self.path).stem
        folder.mkdir(parents=True)
        saved = folder / (loaded['sha256'] + '.json')
        saved.write_bytes(loaded['raw_bytes'])
        attach_mobile_survey(self.config, self.path, self.source)
        self.assertEqual(saved.read_bytes(), loaded['raw_bytes'])

    def test_retry_preserves_corrupt_orphan(self):
        from veilbreaker.mobile_survey_import import load_mobile_survey
        loaded = load_mobile_survey(self.source)
        folder = Path(self.path).parent / 'mobile-evidence' / Path(self.path).stem
        folder.mkdir(parents=True)
        saved = folder / (loaded['sha256'] + '.json')
        saved.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            attach_mobile_survey(self.config, self.path, self.source)
        self.assertEqual(saved.read_bytes(), b'corrupt')
        self.assertFalse(read_session(self.config, self.path).get('mobile_sources'))

    def test_map_preserves_healthy_sources_when_one_mobile_copy_is_damaged(self):
        import copy
        first = attach_mobile_survey(self.config, self.path, self.source)
        damaged_digest = first['mobile_sources'][0]['sha256']
        second = copy.deepcopy(json.loads(self.source.read_text(encoding='utf-8')))
        second['survey_id'] = str(uuid.uuid4())
        second['name'] = 'Healthy source'
        second['points'][0]['capture']['capture_id'] = str(uuid.uuid4())
        second['points'][0]['operator_note'] = 'Valid observation'
        self.source.write_text(json.dumps(second), encoding='utf-8')
        session = attach_mobile_survey(self.config, self.path, self.source)
        healthy_digest = session['mobile_sources'][1]['sha256']
        folder = Path(self.path).parent / 'mobile-evidence' / Path(self.path).stem
        bad = folder / (damaged_digest + '.json')
        good = folder / (healthy_digest + '.json')
        good_original = good.read_bytes()
        bad.write_bytes(b'corrupt')
        spatial = Path(self.path).parent / 'spatial' / Path(self.path).stem
        spatial.mkdir(parents=True)
        key = 'mobile-' + healthy_digest + '-1'
        (spatial / 'spatial.json').write_text(json.dumps(dict(schema_version=1, floors={}, history=[],
            placements={key: dict(kind='geographic', latitude=34.7, longitude=-86.6,
                                  source='operator', placed_utc='2026-11-12T12:00:00Z')})), encoding='utf-8')
        model = load_survey_map_data(self.config, self.path)
        self.assertTrue(any('unavailable' in warning.lower() and damaged_digest[:12] in warning
                            for warning in model['warnings']))
        self.assertTrue(any(row.get('manual') and row.get('mobile_survey_sha256') == healthy_digest
                            and row.get('operator_note') == 'Valid observation' for row in model['rows']))
        self.assertTrue(any(row['run_id'] == session['steps'][0]['run_id'] for row in model['rows']))
        self.assertFalse(any(row.get('mobile_survey_sha256') == damaged_digest for row in model['rows']))
        self.assertEqual(bad.read_bytes(), b'corrupt')
        self.assertEqual(good.read_bytes(), good_original)
        with self.assertRaises(ValueError):
            export_session(self.config, self.path)
        with self.assertRaises(ValueError):
            attach_mobile_survey(self.config, self.path, self.source)

    def test_missing_and_invalid_mobile_records_warn_without_revealing_paths(self):
        from veilbreaker.survey_mobile_evidence import read_attached_mobile_surveys_for_map
        session = attach_mobile_survey(self.config, self.path, self.source)
        digest = session['mobile_sources'][0]['sha256']
        stored = Path(self.path).parent / 'mobile-evidence' / Path(self.path).stem / (digest + '.json')
        stored.unlink()
        result, warnings = read_attached_mobile_surveys_for_map(self.config, self.path, session)
        self.assertEqual(result, [])
        self.assertIn(digest[:12], warnings[0])
        self.assertNotIn(str(self.root), warnings[0])
        model = load_survey_map_data(self.config, self.path)
        self.assertEqual(model['mobile_evidence_warnings'], warnings)
        self.assertTrue(any(r['run_id'] == session['steps'][0]['run_id'] for r in model['rows']))
        with self.assertRaises(ValueError): export_session(self.config, self.path)
        invalid, errors = read_attached_mobile_surveys_for_map(self.config, self.path, {'mobile_sources': [{'sha256': '../../outside'}]})
        self.assertEqual(invalid, [])
        self.assertIn('record 1', errors[0])
        self.assertNotIn('../../outside', errors[0])

    def test_ambiguous_duplicate_records_never_produce_mobile_map_points(self):
        from veilbreaker.survey_mobile_evidence import read_attached_mobile_surveys_for_map
        session = attach_mobile_survey(self.config, self.path, self.source)
        session['mobile_sources'].append(dict(session['mobile_sources'][0]))
        sources, warnings = read_attached_mobile_surveys_for_map(self.config, self.path, session)
        self.assertEqual(sources, [])
        self.assertTrue(any('duplicat' in warning.lower() for warning in warnings))
        with self.assertRaises(ValueError): read_attached_mobile_surveys(self.config, self.path, session)

    def test_aligned_mobile_value_is_scoped_to_its_observation(self):
        import copy
        survey = json.loads(self.source.read_text(encoding='utf-8'))
        capture = survey['points'][0]['capture']
        capture['device']['companion_version'] = '0.8.25-dev'
        observation = capture['observations'][0]
        observation['location'] = dict(status='available', source='phone', provider='gps',
            fix_utc=capture['created_utc'], latitude_deg=35, longitude_deg=-86,
            horizontal_accuracy_m=5, fix_age_ms=1000, mock=False)
        second = copy.deepcopy(observation)
        second['observation_id'] = 'another-fix'
        second['location']['fix_age_ms'] = 9000
        capture['observations'].append(second)
        self.source.write_text(json.dumps(survey), encoding='utf-8')
        attach_mobile_survey(self.config, self.path, self.source)
        model = load_survey_map_data(self.config, self.path)
        rows = {row['observation_id']: row for row in model['rows'] if row.get('mobile_capture_id')}
        self.assertEqual(rows['snapshot-1']['mobile_aligned']['metrics']['phone_lte_rsrp'], -95)
        self.assertNotIn('mobile_aligned', rows['another-fix'])
        self.assertNotIn(rows['snapshot-1']['run_id'], model['run_metrics'])
