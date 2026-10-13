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

    def test_attached_input_shares_run_and_keeps_receiver_metrics_separate(self):
        source = Path('examples/android-cellular-v1.json')
        capture = load_capture(source)
        selection = dict(path=str(source), expected_sha256=capture['sha256'], observation_id='snapshot-1', cell_index=0)
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            app = core.VeilbreakerApplication(cfg)
            try:
                with patch.object(app, 'collect_passive', return_value=({'rsrp': -80}, [])):
                    result = app.run(android_input=selection)
                self.assertEqual(result.metrics['rsrp'], -80)
                self.assertEqual(result.metrics['phone_rsrp'], -95)
                self.assertEqual(result.collection['android']['source_kind'], 'saved_android_capture')
                self.assertEqual(app.store.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 1)
                self.assertFalse(result.run_id.startswith('android-'))
                with zipfile.ZipFile(result.evidence_zip) as bundle:
                    self.assertEqual(bundle.read('android-capture.json'), capture['raw_bytes'])
                self.assertEqual(verify_bundle(result.evidence_zip)['status'], 'verified')
                selection['expected_sha256'] = 'changed'
                with patch.object(app, 'collect_passive', side_effect=AssertionError('must validate first')):
                    with self.assertRaisesRegex(ValueError, 'changed'): app.run(android_input=selection)
            finally:
                app.close()
