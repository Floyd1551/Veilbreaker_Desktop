import json
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path

from veilbreaker import core
from veilbreaker.survey import create_survey, export_session, read_session
from veilbreaker.survey_mobile_evidence import attach_mobile_survey, read_attached_mobile_surveys
from veilbreaker.survey_mobile_recovery import recover_mobile_source
from veilbreaker.survey_report import mobile_sources_html


class RecoveryReportTests(unittest.TestCase):
    def test_recovered_source_is_disclosed_with_timestamp(self):
        digest = 'a' * 64
        session = {'mobile_sources': [{'name': 'Field survey', 'point_count': 0,
                                       'attached_utc': '2026-11-13T12:00:00Z', 'sha256': digest}]}
        mobile = {'sha256': digest, 'survey': {'name': 'Field survey', 'points': []},
                  'recovery': {'filename': 'recovered-' + digest + '.json', 'sha256': digest,
                               'restored_utc': '2026-11-13T13:00:00Z'}}
        report = mobile_sources_html(session, [mobile])
        self.assertIn('Recovered verified copy', report)
        self.assertIn('2026-11-13T13:00:00Z', report)
        self.assertIn('damaged original', report)
        self.assertNotIn('recovered-' + digest + '.json', report)

    def test_recovery_claim_requires_verified_mobile_data(self):
        session = {'mobile_sources': [{'name': 'Field survey', 'point_count': 0,
                                       'sha256': 'a' * 64, 'recovery': {'restored_utc': 'forged'}}]}
        self.assertNotIn('Recovered verified copy', mobile_sources_html(session))

    def test_export_contains_verified_source_and_discloses_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cfg = core.AppConfig(data_dir=str(root))
            path = create_survey(cfg, 'Site', [{}])['survey_path']
            capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
            source = root / 'mobile.json'
            source.write_text(json.dumps(dict(format='veilbreaker.mobile.survey', schema_version=1,
                survey_id=str(uuid.uuid4()), name='Field', created_utc=capture['created_utc'], lifecycle='open',
                points=[dict(attached_utc=capture['created_utc'], capture=capture)])), encoding='utf-8')
            session = attach_mobile_survey(cfg, path, source)
            saved = Path(read_attached_mobile_surveys(cfg, path, session)[0]['path'])
            saved.write_bytes(b'damaged')
            recovery = recover_mobile_source(cfg, path, source)
            bundle = export_session(cfg, path, root / 'survey.zip')
            with zipfile.ZipFile(bundle) as archive:
                self.assertEqual(archive.read('mobile-survey-' + recovery['sha256'] + '.json'), source.read_bytes())
                self.assertIn('Recovered verified copy', archive.read('survey_report.html').decode('utf-8'))
                self.assertIn('damaged copy was preserved', archive.read('README.txt').decode('utf-8'))
                journal = json.loads(archive.read('survey.json'))
                self.assertEqual(journal['mobile_sources'][0]['recovery']['sha256'], recovery['sha256'])
                self.assertNotIn(str(source), json.dumps(journal))
            self.assertEqual(saved.read_bytes(), b'damaged')
            restored = read_attached_mobile_surveys(cfg, path, read_session(cfg, path))[0]
            Path(restored['path']).write_bytes(b'altered')
            with self.assertRaises(ValueError):
                export_session(cfg, path, root / 'invalid.zip')


if __name__ == '__main__':
    unittest.main()
