import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from veilbreaker.cell_reference import active_reference, import_reference
from veilbreaker.deployment_data import bundled_map, seed_reference, install_bundled_structures
from test_cell_reference import HEADER, ROW, META


class DeploymentDataTests(unittest.TestCase):
    def test_install_bundled_structure_packs_verified_and_idempotent(self):
        from veilbreaker.core import AppConfig
        from veilbreaker.regional_packs import RegionalPackStore
        from tests.test_regional_packs import structures
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder); bundled=base/'offline-data'; source=base/'fixture.geojson'; structures(source)
            source_store=RegionalPackStore(bundled/'regional-structures')
            row=source_store.install_local('structures',source,dict(name='FCC fixture',source='FCC fixture',license='test',source_date='2026-10-25',bounds_wgs84=[-97.1,32.8,-96.8,33.1]),lambda:False)
            manifest_path=source_store.root/row['pack_id']/'manifest.json'
            (bundled/'manifest.json').write_text(json.dumps({'structure_packs':[{'pack_id':row['pack_id'],'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest()}]}))
            cfg=AppConfig(data_dir=base/'user')
            result=install_bundled_structures(cfg,bundled)
            self.assertEqual((result['installed'],result['records']), (1,1))
            self.assertEqual(install_bundled_structures(cfg,bundled)['skipped'],1)
            target=RegionalPackStore(cfg.root/'regional-packs')
            self.assertTrue(target.verify(row['pack_id']))
            # A later build can assign a different pack ID to identical, attributed data.
            newer=base/'new-bundle'; newer_store=RegionalPackStore(newer/'regional-structures')
            later=newer_store.install_local('structures',source,dict(name='FCC fixture',source='FCC fixture',license='test',source_date='2026-10-25',bounds_wgs84=[-97.1,32.8,-96.8,33.1]),lambda:False)
            m=newer_store.root/later['pack_id']/'manifest.json'
            (newer/'manifest.json').write_text(json.dumps({'structure_packs':[{'pack_id':later['pack_id'],'manifest_sha256':hashlib.sha256(m.read_bytes()).hexdigest()}]}))
            self.assertEqual(install_bundled_structures(cfg,newer)['skipped'],1)
            self.assertEqual(len(target.list_packs()),1)
            (source_store.root/row['pack_id']/'structures.geojson').write_text('corrupt')
            with self.assertRaisesRegex(ValueError,'checksum'):
                install_bundled_structures(AppConfig(data_dir=base/'other'),bundled)

    def test_missing_bundled_structures_returns_none(self):
        from veilbreaker.core import AppConfig
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(install_bundled_structures(AppConfig(data_dir=folder),Path(folder)/'absent'))
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
