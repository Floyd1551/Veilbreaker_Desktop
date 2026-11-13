import json
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch

from veilbreaker import core
from veilbreaker.survey import create_survey
from veilbreaker.survey_mobile_evidence import attach_mobile_survey, read_attached_mobile_surveys
from veilbreaker.survey_mobile_recovery import restore_missing_mobile_source
from veilbreaker.survey_mobile_recovery import recover_mobile_source


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

    def test_unified_restores_missing_without_journal_change(self):
        journal = Path(self.path).read_bytes()
        self.saved.unlink()
        result = recover_mobile_source(self.cfg, self.path, self.source)
        self.assertEqual(result['status'], 'missing_restored')
        self.assertEqual(Path(self.path).read_bytes(), journal)
        self.assertEqual(self.saved.read_bytes(), self.source.read_bytes())

    def test_damaged_source_is_preserved_and_recovered_with_provenance(self):
        self.saved.write_bytes(b'damaged original')
        result = recover_mobile_source(self.cfg, self.path, self.source)
        self.assertEqual(result['status'], 'damaged_recovered')
        self.assertEqual(self.saved.read_bytes(), b'damaged original')
        journal = json.loads(Path(self.path).read_text(encoding='utf-8'))
        recovery = journal['mobile_sources'][0]['recovery']
        self.assertEqual(recovery['sha256'], result['sha256'])
        self.assertEqual(recovery['filename'], 'recovered-' + result['sha256'] + '.json')
        self.assertEqual(journal['edit_history'][-1]['action'], 'recover damaged mobile evidence')
        loaded = read_attached_mobile_surveys(self.cfg, self.path, journal)[0]
        self.assertEqual(loaded['recovery'], recovery)
        self.assertEqual(loaded['raw_bytes'], self.source.read_bytes())
        self.assertNotEqual(Path(loaded['path']), self.saved)
        Path(loaded['path']).write_bytes(b'changed recovery')
        with self.assertRaises(ValueError):
            read_attached_mobile_surveys(self.cfg, self.path, journal)
        with self.assertRaisesRegex(ValueError, 'already has a recovery record'):
            recover_mobile_source(self.cfg, self.path, self.source)
        self.assertEqual(Path(loaded['path']).read_bytes(), b'changed recovery')
        self.assertEqual(self.saved.read_bytes(), b'damaged original')

    def test_rejects_intact_wrong_and_duplicate_sources(self):
        with self.assertRaisesRegex(ValueError, 'intact'):
            recover_mobile_source(self.cfg, self.path, self.source)
        self.saved.write_bytes(b'damaged')
        self.source.write_bytes(self.source.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'does not match'):
            recover_mobile_source(self.cfg, self.path, self.source)
        self.source.write_bytes(self.source.read_bytes()[:-1])
        journal = json.loads(Path(self.path).read_text(encoding='utf-8'))
        journal['mobile_sources'].append(dict(journal['mobile_sources'][0]))
        Path(self.path).write_text(json.dumps(journal), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'unique'):
            recover_mobile_source(self.cfg, self.path, self.source)
        self.assertEqual(self.saved.read_bytes(), b'damaged')

    def test_refuses_unsafe_or_modified_existing_recovery_asset(self):
        self.saved.write_bytes(b'damaged')
        digest = self.session['mobile_sources'][0]['sha256']
        orphan = self.saved.with_name('recovered-' + digest + '.json')
        orphan.write_bytes(b'do not overwrite')
        with self.assertRaises(ValueError):
            recover_mobile_source(self.cfg, self.path, self.source)
        self.assertEqual(orphan.read_bytes(), b'do not overwrite')
        orphan.write_bytes(self.source.read_bytes())
        with patch('veilbreaker.survey_mobile_recovery._link_or_reparse', side_effect=lambda p: p == orphan):
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                recover_mobile_source(self.cfg, self.path, self.source)
        self.assertEqual(orphan.read_bytes(), self.source.read_bytes())

    def test_reuses_verified_orphan_and_does_not_delete_it_on_failure(self):
        self.saved.write_bytes(b'damaged')
        digest = self.session['mobile_sources'][0]['sha256']
        orphan = self.saved.with_name('recovered-' + digest + '.json')
        orphan.write_bytes(self.source.read_bytes())
        with patch('veilbreaker.survey_mobile_recovery.atomic_json', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                recover_mobile_source(self.cfg, self.path, self.source)
        self.assertEqual(orphan.read_bytes(), self.source.read_bytes())
        self.assertEqual(recover_mobile_source(self.cfg, self.path, self.source)['status'], 'damaged_recovered')

    def test_new_asset_preserved_if_journal_commit_fails(self):
        self.saved.write_bytes(b'damaged')
        digest = self.session['mobile_sources'][0]['sha256']
        recovery = self.saved.with_name('recovered-' + digest + '.json')
        journal = Path(self.path).read_bytes()
        with patch('veilbreaker.survey_mobile_recovery.atomic_json', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                recover_mobile_source(self.cfg, self.path, self.source)
        self.assertEqual(recovery.read_bytes(), self.source.read_bytes())
        self.assertEqual(Path(self.path).read_bytes(), journal)
        self.assertEqual(self.saved.read_bytes(), b'damaged')
        self.assertEqual(recover_mobile_source(self.cfg, self.path, self.source)['status'], 'damaged_recovered')

    def test_commit_that_raises_after_replacing_journal_preserves_recovery(self):
        self.saved.write_bytes(b'damaged')
        from veilbreaker.recovery import atomic_json
        def commit_then_raise(path, journal):
            atomic_json(path, journal)
            raise OSError('late failure')
        with patch('veilbreaker.survey_mobile_recovery.atomic_json', side_effect=commit_then_raise):
            with self.assertRaises(OSError):
                recover_mobile_source(self.cfg, self.path, self.source)
        journal = json.loads(Path(self.path).read_text(encoding='utf-8'))
        self.assertEqual(read_attached_mobile_surveys(self.cfg, self.path, journal)[0]['raw_bytes'], self.source.read_bytes())

    def test_reader_rejects_manipulated_recovery_pointer(self):
        self.saved.write_bytes(b'damaged')
        recover_mobile_source(self.cfg, self.path, self.source)
        journal = json.loads(Path(self.path).read_text(encoding='utf-8'))
        for field, value in [('filename', '../outside.json'), ('sha256', '0' * 64), ('restored_utc', 'invalid')]:
            altered = json.loads(json.dumps(journal))
            altered['mobile_sources'][0]['recovery'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                read_attached_mobile_surveys(self.cfg, self.path, altered)

    def test_recovered_source_survives_reopen_and_export(self):
        from veilbreaker.survey import export_session, read_session
        from veilbreaker.evidence import verify_bundle
        from veilbreaker.survey_mobile_evidence import read_attached_mobile_surveys_for_map
        self.saved.write_bytes(b'damaged')
        digest = recover_mobile_source(self.cfg, self.path, self.source)['sha256']
        reopened = read_session(self.cfg, self.path)
        points, warnings = read_attached_mobile_surveys_for_map(self.cfg, self.path, reopened)
        self.assertEqual(len(points), 1)
        self.assertEqual(warnings, [])
        bundle = export_session(self.cfg, self.path)
        self.assertEqual(verify_bundle(bundle)['status'], 'verified')
        with zipfile.ZipFile(bundle) as archive:
            self.assertEqual(archive.read('mobile-survey-' + digest + '.json'), self.source.read_bytes())
            exported = json.loads(archive.read('survey.json'))
            self.assertEqual(exported['mobile_sources'][0]['recovery']['sha256'], digest)

    def test_recovery_respects_survey_lock(self):
        from veilbreaker.survey import session_lock
        self.saved.write_bytes(b'damaged')
        with session_lock(Path(self.path)):
            with self.assertRaisesRegex(ValueError, 'already being modified'):
                recover_mobile_source(self.cfg, self.path, self.source)
        self.assertEqual(self.saved.read_bytes(), b'damaged')

    def test_recovered_asset_remains_with_survey_after_trash_and_restore(self):
        from veilbreaker.library import trash_survey, restore_entry
        from veilbreaker.survey import read_session
        self.saved.write_bytes(b'damaged')
        recover_mobile_source(self.cfg, self.path, self.source)
        entry = trash_survey(self.cfg, self.path)
        restore_entry(self.cfg, entry)
        loaded = read_attached_mobile_surveys(self.cfg, self.path, read_session(self.cfg, self.path))
        self.assertEqual(loaded[0]['raw_bytes'], self.source.read_bytes())
        self.assertEqual(self.saved.read_bytes(), b'damaged')
