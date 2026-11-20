import hashlib
import json
import shutil
import tempfile
import threading
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from veilbreaker import deployment_data
from veilbreaker.cell_reference import activate_reference, active_reference, import_reference, verify_reference_database
from test_cell_reference import HEADER, ROW, META


class BundledCellInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'cells.csv'
        self.source.write_text(HEADER + ROW, encoding='utf-8')
        self.bundle = self.root / 'bundle'
        self.manifest = import_reference(self.bundle / 'cell-reference', self.source, META, lambda: False, lambda _: None)
        self.bundle_db = self.bundle / 'cell-reference' / self.manifest['dataset_id'] / 'cells.sqlite'
        (self.bundle / 'manifest.json').write_text(json.dumps({'cell_database_sha256': self.manifest['database_sha256']}), encoding='utf-8')
        self.user = self.root / 'user'

    def test_install_is_explicit_verified_and_preserves_active_selection(self):
        legacy = import_reference(self.user, self.source, dict(META, date='older'), lambda: False, lambda _: None)
        activate_reference(self.user, legacy['dataset_id'])
        result = deployment_data.install_bundled_reference(self.user, self.bundle)
        self.assertEqual(result['status'], 'installed')
        self.assertEqual(result['dataset_id'], self.manifest['dataset_id'])
        self.assertEqual(active_reference(self.user)['dataset_id'], legacy['dataset_id'])
        self.assertEqual(verify_reference_database(self.user, result['dataset_id'])['status'], 'verified')
        self.assertEqual(deployment_data.install_bundled_reference(self.user, self.bundle)['status'], 'existing')
        self.assertTrue((self.user / legacy['dataset_id'] / 'cells.sqlite').is_file())

    def test_missing_bundle_and_explicit_deactivation_are_preserved(self):
        self.assertEqual(deployment_data.install_bundled_reference(self.user, self.root / 'none'),
                         {'status': 'unavailable', 'dataset_id': None})
        self.assertFalse(self.user.exists())
        self.user.mkdir()
        activate_reference(self.user, None)
        before = (self.user / 'active.json').read_bytes()
        deployment_data.install_bundled_reference(self.user, self.bundle)
        self.assertEqual((self.user / 'active.json').read_bytes(), before)
        self.assertIsNone(active_reference(self.user))

    def test_bad_bundle_checksum_or_manifest_never_creates_user_copy(self):
        index = self.bundle / 'manifest.json'
        index.write_text(json.dumps({'cell_database_sha256': '0'*64}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            deployment_data.install_bundled_reference(self.user, self.bundle)
        self.assertFalse(self.user.exists())
        index.write_text(json.dumps({'cell_database_sha256': self.manifest['database_sha256']}), encoding='utf-8')
        manifest_path = self.bundle / 'cell-reference' / self.manifest['dataset_id'] / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest.pop('database_sha256')
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            deployment_data.install_bundled_reference(self.user, self.bundle)
        self.assertFalse(self.user.exists())

    def test_index_provenance_conflict_is_rejected(self):
        index = self.bundle / 'manifest.json'
        value = {'cell_database_sha256': self.manifest['database_sha256'],
                 'cell_dataset_id': self.manifest['dataset_id'],
                 'cell_source_sha256': self.manifest['sha256'],
                 'cell_source': 'Different provider', 'cell_license': self.manifest['license']}
        index.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'provenance|metadata'):
            deployment_data.install_bundled_reference(self.user, self.bundle)
        self.assertFalse(self.user.exists())

    def test_non_object_bundle_index_is_reported_as_invalid(self):
        (self.bundle / 'manifest.json').write_text('null', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'index'):
            deployment_data.install_bundled_reference(self.user, self.bundle)
        self.assertFalse(self.user.exists())

    def test_same_id_collision_is_never_overwritten(self):
        target = self.user / self.manifest['dataset_id']
        target.mkdir(parents=True)
        (target / 'cells.sqlite').write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError, 'existing|collision'):
            deployment_data.install_bundled_reference(self.user, self.bundle)
        self.assertEqual((target / 'cells.sqlite').read_bytes(), b'preserve')

    def test_cancellation_and_copy_corruption_do_not_publish_staging(self):
        with self.assertRaisesRegex(ValueError, 'cancel'):
            deployment_data.install_bundled_reference(self.user, self.bundle, cancelled=lambda: True)
        self.assertFalse(self.user.exists())
        original = deployment_data._copy_bundled_database
        def corrupt(*args, **kwargs):
            original(*args, **kwargs)
            destination = args[1]
            data = bytearray(destination.read_bytes()); data[-1] ^= 1; destination.write_bytes(data)
        with patch.object(deployment_data, '_copy_bundled_database', side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, 'checksum|changed'):
                deployment_data.install_bundled_reference(self.user, self.bundle)
        self.assertFalse((self.user / self.manifest['dataset_id']).exists())
        self.assertEqual(list(self.user.iterdir()), [])

    def test_cancel_during_copy_preserves_active_and_removes_staging(self):
        legacy = import_reference(self.user, self.source, dict(META, date='older'), lambda: False, lambda _: None)
        activate_reference(self.user, legacy['dataset_id'])
        stop = threading.Event()
        with self.assertRaisesRegex(ValueError, 'cancel'):
            deployment_data.install_bundled_reference(self.user, self.bundle, stop.is_set,
                                                      lambda message: stop.set() if message.startswith('Copying') else None)
        self.assertEqual(active_reference(self.user)['dataset_id'], legacy['dataset_id'])
        self.assertFalse((self.user / self.manifest['dataset_id']).exists())
        self.assertFalse(any(p.name.startswith('.staging-') for p in self.user.iterdir()))

    def test_manifest_change_during_copy_is_rejected(self):
        original = deployment_data._copy_bundled_database
        def change_index(*args, **kwargs):
            original(*args, **kwargs)
            (self.bundle / 'manifest.json').write_text(json.dumps({'cell_database_sha256': '0'*64}), encoding='utf-8')
        with patch.object(deployment_data, '_copy_bundled_database', side_effect=change_index):
            with self.assertRaisesRegex(ValueError, 'changed|checksum'):
                deployment_data.install_bundled_reference(self.user, self.bundle)
        self.assertFalse((self.user / self.manifest['dataset_id']).exists())
        self.assertFalse(any(p.name.startswith('.staging-') for p in self.user.iterdir()))

    def test_existing_equivalent_snapshot_can_be_reused(self):
        prior = import_reference(self.user, self.source, META, lambda: False, lambda _: None)
        result = deployment_data.install_bundled_reference(self.user, self.bundle)
        self.assertEqual(result, {'status': 'existing', 'dataset_id': prior['dataset_id']})
        self.assertEqual(len([p for p in self.user.iterdir() if p.is_dir()]), 1)

    def test_cancellation_after_copy_verification_does_not_publish(self):
        stop = threading.Event()
        original = deployment_data._verify_copied_database
        def finish_then_cancel(*args, **kwargs):
            result = original(*args, **kwargs)
            stop.set()
            return result
        with patch.object(deployment_data, '_verify_copied_database', side_effect=finish_then_cancel):
            with self.assertRaisesRegex(ValueError, 'cancel'):
                deployment_data.install_bundled_reference(self.user, self.bundle, cancelled=stop.is_set)
        self.assertFalse((self.user / self.manifest['dataset_id']).exists())
        self.assertFalse((self.user / 'active.json').exists())
        self.assertEqual(list(self.user.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
