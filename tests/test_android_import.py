from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from veilbreaker import core
from veilbreaker.android_capture import load_capture
from veilbreaker.android_import import import_capture
from veilbreaker.evidence import verify_bundle


class ImportTests(unittest.TestCase):
    def test_preserves_original_and_requires_explicit_repeat(self):
        source = Path('examples/android-cellular-v1.json')
        capture = load_capture(source)
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            with patch.object(core.VeilbreakerApplication, 'collect_passive', side_effect=AssertionError('No acquisition')):
                result = import_capture(cfg, str(source), capture['sha256'], 'snapshot-1', 0)
            self.assertEqual(verify_bundle(result['evidence_zip'])['status'], 'verified')
            with zipfile.ZipFile(result['evidence_zip']) as bundle:
                self.assertEqual(bundle.read('android-capture.json'), capture['raw_bytes'])
                self.assertIn('android-selection.json', bundle.namelist())
            with self.assertRaisesRegex(ValueError, 'already imported'):
                import_capture(cfg, str(source), capture['sha256'], 'snapshot-1', 0)
            repeated = import_capture(cfg, str(source), capture['sha256'], 'snapshot-1', 0, True)
            self.assertNotEqual(result['run_id'], repeated['run_id'])
            store = core.VeilbreakerStore(cfg.db_path)
            try:
                self.assertEqual(store.baseline(cfg.site_id, cfg.scenario, min_samples=1), {})
            finally:
                store.close()

    def test_changed_source_creates_no_database(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            with self.assertRaisesRegex(ValueError, 'changed'):
                import_capture(cfg, 'examples/android-cellular-v1.json', 'bad', 'snapshot-1', 0)
            self.assertFalse(cfg.db_path.exists())
