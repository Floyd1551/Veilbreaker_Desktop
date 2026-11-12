import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from veilbreaker.core import AppConfig
from veilbreaker.mobile_survey_import import load_mobile_survey
from veilbreaker.mobile_survey_library import (_link_or_reparse, import_mobile_survey, list_mobile_surveys,
    read_mobile_survey, trash_mobile_survey, restore_mobile_survey, delete_trashed_mobile_survey)


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

    def test_trash_and_restore_preserve_original_and_require_explicit_restore(self):
        saved = import_mobile_survey(self.config, self.source, self.preview['sha256'])
        original = Path(saved['path']).read_bytes()
        trash_mobile_survey(self.config, self.preview['sha256'])
        self.assertEqual(list_mobile_surveys(self.config), ([], 0))
        trash, unavailable = list_mobile_surveys(self.config, trashed=True)
        self.assertEqual(unavailable, 0); self.assertEqual(trash[0]['sha256'], self.preview['sha256'])
        with self.assertRaisesRegex(ValueError, 'Trash'): read_mobile_survey(self.config, self.preview['sha256'])
        with self.assertRaisesRegex(ValueError, 'Trash'): import_mobile_survey(self.config, self.source, self.preview['sha256'])
        self.assertEqual(Path(saved['path']).read_bytes(), original)
        restore_mobile_survey(self.config, self.preview['sha256'])
        self.assertEqual(len(list_mobile_surveys(self.config)[0]), 1)
        self.assertEqual(Path(saved['path']).read_bytes(), original)

    def test_changed_copy_cannot_be_restored_or_silently_replaced(self):
        saved = import_mobile_survey(self.config, self.source, self.preview['sha256'])
        trash_mobile_survey(self.config, self.preview['sha256'])
        path = Path(saved['path']); path.write_text('damaged', encoding='utf-8')
        with self.assertRaises(ValueError): restore_mobile_survey(self.config, self.preview['sha256'])
        self.assertEqual(path.read_text(), 'damaged')
        self.assertTrue((path.parent / 'trash.json').is_file())

    def test_failed_trash_write_leaves_the_original_active(self):
        saved = import_mobile_survey(self.config, self.source, self.preview['sha256'])
        before = Path(saved['path']).read_bytes()
        with patch('veilbreaker.mobile_survey_library.os.fsync', side_effect=OSError('disk error')):
            with self.assertRaises(OSError): trash_mobile_survey(self.config, self.preview['sha256'])
        self.assertEqual(Path(saved['path']).read_bytes(), before)
        self.assertEqual(len(list_mobile_surveys(self.config)[0]), 1)

    def test_trashed_copies_still_count_toward_storage_limit(self):
        import_mobile_survey(self.config, self.source, self.preview['sha256'])
        trash_mobile_survey(self.config, self.preview['sha256'])
        self.source.write_text(self.source.read_text() + ' ', encoding='utf-8')
        changed = load_mobile_survey(self.source)
        with patch('veilbreaker.mobile_survey_library.MAX_SURVEYS', 1):
            with self.assertRaisesRegex(ValueError, 'full'): import_mobile_survey(self.config, self.source, changed['sha256'])

    def test_damaged_trash_marker_is_preserved_and_not_treated_as_empty(self):
        saved = import_mobile_survey(self.config, self.source, self.preview['sha256'])
        path = Path(saved['path']); before = path.read_bytes()
        marker = path.parent / 'trash.json'; marker.write_text('{broken', encoding='utf-8')
        self.assertEqual(list_mobile_surveys(self.config), ([], 1))
        self.assertEqual(list_mobile_surveys(self.config, trashed=True), ([], 1))
        with self.assertRaises(ValueError): restore_mobile_survey(self.config, self.preview['sha256'])
        self.assertEqual(marker.read_text(), '{broken'); self.assertEqual(path.read_bytes(), before)

    def test_permanent_delete_requires_trash_and_preserves_original_source(self):
        saved = import_mobile_survey(self.config, self.source, self.preview['sha256'])
        original = self.source.read_bytes(); local = Path(saved['path'])
        with self.assertRaises(ValueError): delete_trashed_mobile_survey(self.config, self.preview['sha256'])
        self.assertTrue(local.exists())
        trash_mobile_survey(self.config, self.preview['sha256'])
        delete_trashed_mobile_survey(self.config, self.preview['sha256'])
        self.assertFalse(local.parent.exists()); self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(list_mobile_surveys(self.config, trashed=True), ([], 0))
        self.assertTrue(import_mobile_survey(self.config, self.source, self.preview['sha256'])['imported'])

    def test_delete_refuses_unexpected_files_or_changed_evidence(self):
        saved = import_mobile_survey(self.config, self.source, self.preview['sha256'])
        local = Path(saved['path']); trash_mobile_survey(self.config, self.preview['sha256'])
        extra = local.parent / 'operator-data.txt'; extra.write_text('keep', encoding='utf-8')
        with self.assertRaises(ValueError): delete_trashed_mobile_survey(self.config, self.preview['sha256'])
        self.assertEqual(extra.read_text(), 'keep'); self.assertTrue(local.exists())
        extra.unlink(); local.write_text('changed', encoding='utf-8')
        with self.assertRaises(ValueError): delete_trashed_mobile_survey(self.config, self.preview['sha256'])
        self.assertEqual(local.read_text(), 'changed'); self.assertTrue((local.parent / 'trash.json').exists())

    def test_delete_failure_reports_incomplete_removal_without_touching_original(self):
        saved = import_mobile_survey(self.config, self.source, self.preview['sha256'])
        local = Path(saved['path']); original = self.source.read_bytes()
        trash_mobile_survey(self.config, self.preview['sha256'])
        unlink = Path.unlink
        def fail_marker(path, *args, **kwargs):
            if path.name == 'trash.json': raise OSError('denied')
            return unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail_marker):
            with self.assertRaisesRegex(OSError, 'could not finish'): delete_trashed_mobile_survey(self.config, self.preview['sha256'])
        self.assertEqual(self.source.read_bytes(), original)
        self.assertTrue((local.parent / 'trash.json').exists())

    def test_delete_refuses_reparse_marked_evidence(self):
        saved = import_mobile_survey(self.config, self.source, self.preview['sha256'])
        local = Path(saved['path']); before = local.read_bytes()
        trash_mobile_survey(self.config, self.preview['sha256'])
        original_check = _link_or_reparse
        with patch('veilbreaker.mobile_survey_library._link_or_reparse', side_effect=lambda path: path == local or original_check(path)):
            with self.assertRaises(ValueError): delete_trashed_mobile_survey(self.config, self.preview['sha256'])
        self.assertEqual(local.read_bytes(), before)
