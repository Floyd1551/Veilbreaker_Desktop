import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from veilbreaker.core import AppConfig
from veilbreaker.mobile_survey_import import load_mobile_survey
from veilbreaker.mobile_survey_library import _link_or_reparse, import_mobile_survey, list_mobile_surveys, read_mobile_survey


class MobileSurveyLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.config = AppConfig(data_dir=str(self.root / 'workspace'))
        capture = json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))
        self.survey = {'format': 'veilbreaker.mobile.survey', 'schema_version': 1, 'survey_id': str(uuid.uuid4()),
                       'name': 'Test site', 'created_utc': capture['created_utc'], 'lifecycle': 'open',
                       'points': [{'attached_utc': capture['created_utc'], 'capture': capture, 'operator_note': 'Metal wall'}]}
        self.source = self.root / 'source.json'; self.source.write_text(json.dumps(self.survey), encoding='utf-8')
        self.preview = load_mobile_survey(self.source)

    def test_import_keeps_exact_original_and_reopens_without_source(self):
        original = self.source.read_bytes()
        result = import_mobile_survey(self.config, self.source, self.preview['sha256'])
        self.assertTrue(result['imported']); self.assertEqual(Path(result['path']).read_bytes(), original)
        self.source.unlink()
        reopened = read_mobile_survey(self.config, self.preview['sha256'])
        self.assertEqual(reopened['survey'], self.survey)
        rows, unavailable = list_mobile_surveys(self.config)
        self.assertEqual(len(rows), 1); self.assertEqual(unavailable, 0)
        self.assertEqual(rows[0]['sha256'], self.preview['sha256'])

    def test_duplicate_is_idempotent_and_changed_source_rejected(self):
        first = import_mobile_survey(self.config, self.source, self.preview['sha256'])
        self.assertFalse(import_mobile_survey(self.config, self.source, self.preview['sha256'])['imported'])
        self.source.write_text(self.source.read_text() + ' ', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'changed'): import_mobile_survey(self.config, self.source, self.preview['sha256'])
        self.assertEqual(read_mobile_survey(self.config, self.preview['sha256'])['path'], first['path'])

    def test_corrupted_import_is_preserved_and_never_overwritten(self):
        first = import_mobile_survey(self.config, self.source, self.preview['sha256'])
        path = Path(first['path']); path.write_text('damaged', encoding='utf-8')
        rows, unavailable = list_mobile_surveys(self.config)
        self.assertEqual(rows, []); self.assertEqual(unavailable, 1)
        with self.assertRaises(ValueError): read_mobile_survey(self.config, self.preview['sha256'])
        with self.assertRaises(ValueError): import_mobile_survey(self.config, self.source, self.preview['sha256'])
        self.assertEqual(path.read_text(), 'damaged')

    def test_invalid_identifiers_are_rejected(self):
        for token in ('../outside', 'f' * 63, 'F' * 64):
            with self.assertRaises(ValueError): read_mobile_survey(self.config, token)

    def test_windows_reparse_points_are_not_treated_as_normal_files(self):
        class FakePath:
            def is_symlink(self): return False
            def lstat(self): return SimpleNamespace(st_file_attributes=0x400)
        self.assertTrue(_link_or_reparse(FakePath()))

    def test_failed_write_does_not_replace_source_or_leave_a_valid_copy(self):
        before = self.source.read_bytes()
        with patch('veilbreaker.mobile_survey_library.os.fsync', side_effect=OSError('disk error')):
            with self.assertRaises(OSError): import_mobile_survey(self.config, self.source, self.preview['sha256'])
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(list_mobile_surveys(self.config), ([], 0))
