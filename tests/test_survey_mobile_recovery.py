import json
import tempfile
import unittest
import uuid
from pathlib import Path

from veilbreaker import core
from veilbreaker.survey import create_survey
from veilbreaker.survey_mobile_evidence import attach_mobile_survey, read_attached_mobile_surveys
from veilbreaker.survey_mobile_recovery import restore_missing_mobile_source


class SurveyMobileRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.cfg = core.AppConfig(data_dir=str(root))
        self.path = create_survey(self.cfg, 'Site', [{}])['survey_path']
        capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        self.source = root / 'original.json'
        self.source.write_text(json.dumps(dict(format='veilbreaker.mobile.survey', schema_version=1,
            survey_id=str(uuid.uuid4()), name='Mobile', created_utc=capture['created_utc'], lifecycle='open',
            points=[dict(attached_utc=capture['created_utc'], capture=capture)])), encoding='utf-8')
        self.session = attach_mobile_survey(self.cfg, self.path, self.source)
        self.saved = Path(read_attached_mobile_surveys(self.cfg, self.path, self.session)[0]['path'])

    def test_restore_missing_exact_original_without_changing_journal(self):
        journal = Path(self.path).read_bytes(); raw = self.source.read_bytes()
        self.saved.unlink()
        restore_missing_mobile_source(self.cfg, self.path, self.source)
        self.assertEqual(self.saved.read_bytes(), raw)
        self.assertEqual(Path(self.path).read_bytes(), journal)
        self.assertEqual(len(read_attached_mobile_surveys(self.cfg, self.path, self.session)), 1)

    def test_rejects_nonmatching_or_existing_source_without_overwrite(self):
        self.saved.write_bytes(b'damaged')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            restore_missing_mobile_source(self.cfg, self.path, self.source)
        self.assertEqual(self.saved.read_bytes(), b'damaged')
        self.saved.unlink()
        self.source.write_bytes(self.source.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'does not match'):
            restore_missing_mobile_source(self.cfg, self.path, self.source)
        self.assertFalse(self.saved.exists())
