import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from veilbreaker import cell_reference as ref
from test_cell_reference import HEADER, ROW, META


class CellReferenceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'refs'
        self.source = Path(self.tmp.name) / 'cells.csv'
        self.source.write_text(HEADER + ROW, encoding='utf-8')
        self.row = ref.import_reference(self.root, self.source, META, lambda: False, lambda _: None)
        self.folder = self.root / self.row['dataset_id']
        self.database = self.folder / 'cells.sqlite'

    def test_import_records_separate_database_hash_and_verified_signature(self):
        self.assertEqual(self.row['sha256'], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(self.row['database_sha256'], hashlib.sha256(self.database.read_bytes()).hexdigest())
        self.assertEqual(self.row['database_bytes'], self.database.stat().st_size)
        check = ref.verify_reference_database(self.root, self.row['dataset_id'])
        self.assertEqual(check['status'], 'verified')
        self.assertEqual(check['actual_sha256'], self.row['database_sha256'])
        self.assertEqual(check['file_signature'], ref.reference_database_signature(self.root, self.row['dataset_id']))

    def test_same_size_tamper_is_not_verified_or_silently_reused(self):
        ref.activate_reference(self.root, self.row['dataset_id'])
        data = bytearray(self.database.read_bytes())
        data[-1] ^= 1
        self.database.write_bytes(data)
        self.assertEqual(ref.verify_reference_database(self.root, self.row['dataset_id'])['status'], 'changed')
        fresh = ref.import_reference(self.root, self.source, META, lambda: False, lambda _: None)
        self.assertNotEqual(fresh['dataset_id'], self.row['dataset_id'])
        self.assertEqual(ref.active_reference(self.root)['dataset_id'], self.row['dataset_id'])
        self.assertEqual(ref.verify_reference_database(self.root, fresh['dataset_id'])['status'], 'verified')

    def test_verified_matching_import_reuses_snapshot(self):
        fresh = ref.import_reference(self.root, self.source, META, lambda: False, lambda _: None)
        self.assertEqual(fresh['dataset_id'], self.row['dataset_id'])

    def test_sidecars_prevent_verification_without_mutation(self):
        for suffix in ('-wal', '-shm', '-journal'):
            sidecar = self.folder / ('cells.sqlite' + suffix)
            sidecar.write_bytes(b'unverified data')
            self.assertEqual(ref.verify_reference_database(self.root, self.row['dataset_id'])['status'], 'invalid')
            with self.assertRaisesRegex(ValueError, 'sidecar'):
                ref.reference_database_signature(self.root, self.row['dataset_id'])
            self.assertEqual(sidecar.read_bytes(), b'unverified data')
            sidecar.unlink()

    def test_manifest_change_during_verification_is_not_verified(self):
        original = ref._json
        calls = []
        def changed(path):
            value = original(path)
            calls.append(path)
            if len(calls) == 2:
                value['source'] = 'changed while reading'
            return value
        with patch.object(ref, '_json', side_effect=changed):
            result = ref.verify_reference_database(self.root, self.row['dataset_id'])
        self.assertEqual(result['status'], 'changed')

    def test_one_shot_cancellation_during_hash_is_not_swallowed(self):
        calls = iter([False, True])
        with self.assertRaisesRegex(ValueError, 'cancel'):
            ref.verify_reference_database(self.root, self.row['dataset_id'], cancelled=lambda: next(calls, False))

    def test_invalid_identifier_cannot_escape_storage(self):
        self.assertEqual(ref.verify_reference_database(self.root, '../outside')['status'], 'invalid')
        with self.assertRaises(ValueError):
            ref.reference_database_signature(self.root, '../outside')

    def test_legacy_is_explicitly_unverified_and_reimport_creates_new_snapshot(self):
        manifest = self.folder / 'manifest.json'
        value = json.loads(manifest.read_text(encoding='utf-8'))
        value.pop('database_sha256'); value.pop('database_bytes')
        manifest.write_text(json.dumps(value), encoding='utf-8')
        self.assertEqual(ref.verify_reference_database(self.root, self.row['dataset_id'])['status'], 'legacy_unverified')
        fresh = ref.import_reference(self.root, self.source, META, lambda: False, lambda _: None)
        self.assertNotEqual(fresh['dataset_id'], self.row['dataset_id'])
        self.assertNotIn('database_sha256', json.loads(manifest.read_text(encoding='utf-8')))

    def test_missing_invalid_and_cancelled_never_mutate_reference(self):
        with self.assertRaisesRegex(ValueError, 'cancel'):
            ref.verify_reference_database(self.root, self.row['dataset_id'], cancelled=lambda: True)
        manifest = self.folder / 'manifest.json'
        value = json.loads(manifest.read_text(encoding='utf-8'))
        value['database_sha256'] = 'invalid'
        manifest.write_text(json.dumps(value), encoding='utf-8')
        self.assertEqual(ref.verify_reference_database(self.root, self.row['dataset_id'])['status'], 'invalid')
        self.database.unlink()
        self.assertEqual(ref.verify_reference_database(self.root, self.row['dataset_id'])['status'], 'missing')
        self.assertEqual(ref.verify_reference_database(self.root)['status'], 'no_active_reference')


if __name__ == '__main__':
    unittest.main()
