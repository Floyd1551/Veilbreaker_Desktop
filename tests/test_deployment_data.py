import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from veilbreaker.cell_reference import active_reference, import_reference
from veilbreaker.deployment_data import bundled_map, seed_reference
from test_cell_reference import HEADER, ROW, META


class DeploymentDataTests(unittest.TestCase):
    def test_bundled_map_is_discovered_without_copying(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            path = base / 'maps' / 'CONUS-overview.pmtiles'
            path.parent.mkdir()
            path.write_bytes(b'pack')
            self.assertEqual(bundled_map(base), path)
            self.assertIsNone(bundled_map(base / 'missing'))

    def test_seed_reference_verifies_database_and_preserves_existing_active(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            source = base / 'source.csv'
            source.write_text(HEADER + ROW, encoding='utf-8')
            included = base / 'offline-data'
            made = import_reference(included / 'cell-reference', source, META, lambda: False, lambda _: None)
            db = included / 'cell-reference' / made['dataset_id'] / 'cells.sqlite'
            (included / 'manifest.json').write_text(json.dumps({'cell_database_sha256': hashlib.sha256(db.read_bytes()).hexdigest()}))
            user = base / 'user-refs'
            self.assertEqual(seed_reference(user, included)['dataset_id'], made['dataset_id'])
            self.assertEqual(active_reference(user)['dataset_id'], made['dataset_id'])
            self.assertEqual(seed_reference(user, included)['dataset_id'], made['dataset_id'])
            db.write_bytes(b'corrupt')
            self.assertEqual(seed_reference(user, included)['dataset_id'], made['dataset_id'])
            other = base / 'other.csv'
            other.write_text(HEADER + ROW.replace('-96.8', '-96.9'), encoding='utf-8')
            alternative = import_reference(user, other, META, lambda: False, lambda _: None)
            from veilbreaker.cell_reference import activate_reference
            activate_reference(user, alternative['dataset_id'])
            self.assertEqual(seed_reference(user, included)['dataset_id'], alternative['dataset_id'])
            activate_reference(user, None)
            self.assertIsNone(seed_reference(user, included))
            self.assertIsNone(active_reference(user))

    def test_corrupt_bundled_reference_does_not_create_partial_user_data(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            source = base / 'source.csv'
            source.write_text(HEADER + ROW, encoding='utf-8')
            included = base / 'offline-data'
            made = import_reference(included / 'cell-reference', source, META, lambda: False, lambda _: None)
            (included / 'manifest.json').write_text(json.dumps({'cell_database_sha256': '0' * 64}))
            user = base / 'user-refs'
            with self.assertRaisesRegex(ValueError, 'checksum'):
                seed_reference(user, included)
            self.assertFalse(user.exists())


if __name__ == '__main__':
    unittest.main()
