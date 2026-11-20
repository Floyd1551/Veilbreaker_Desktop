import os
import tempfile
import hashlib
import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from veilbreaker.core import AppConfig
from veilbreaker.cell_reference_ui import CellReferenceDialog
from veilbreaker.cell_reference import activate_reference, active_reference, import_reference
from test_cell_reference import HEADER, ROW, META


class IncludedCellReferenceUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_install_button_starts_background_job_and_retains_explicit_activation(self):
        with tempfile.TemporaryDirectory() as folder, patch('veilbreaker.deployment_data.seed_reference'):
            dialog = CellReferenceDialog(None, AppConfig(data_dir=folder))
            try:
                with patch.object(dialog, 'start_job') as start:
                    dialog.included_reference_button.click()
                    start.assert_called_once()
                dialog.job_progress({'copied_bytes': 1048576, 'total_bytes': 2097152})
                self.assertIn('1.0 / 2.0 MiB', dialog.status.text())
                with patch.object(dialog, 'refresh'), patch.object(dialog, 'activate') as activate:
                    dialog.job_ready({'included_reference': {'status': 'unavailable', 'dataset_id': None}})
                    self.assertIn('no included', dialog.status.text().lower())
                    dialog.job_ready({'included_reference': {'status': 'installed', 'dataset_id': 'a'*32}})
                    self.assertIn('use selected reference', dialog.status.text().lower())
                    activate.assert_not_called()
            finally:
                dialog.close()

    def test_installs_included_snapshot_without_changing_active_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); config = AppConfig(data_dir=str(root / 'user'))
            csv = root / 'cells.csv'; csv.write_text(HEADER + ROW, encoding='utf-8')
            bundle = root / 'offline-data'
            included = import_reference(bundle / 'cell-reference', csv, META, lambda: False, lambda _: None)
            db = bundle / 'cell-reference' / included['dataset_id'] / 'cells.sqlite'
            (bundle / 'manifest.json').write_text(json.dumps({'cell_database_sha256': hashlib.sha256(db.read_bytes()).hexdigest()}), encoding='utf-8')
            old = import_reference(config.root / 'cell-references', csv, dict(META, date='older'), lambda: False, lambda _: None)
            activate_reference(config.root / 'cell-references', old['dataset_id'])
            with patch('veilbreaker.deployment_data.seed_reference'), patch('veilbreaker.deployment_data.deployment_root', return_value=bundle):
                dialog = CellReferenceDialog(None, config)
                try:
                    dialog.included_reference_button.click()
                    deadline = time.monotonic() + 10
                    while dialog.worker is not None and time.monotonic() < deadline:
                        self.app.processEvents(); time.sleep(.01)
                    self.assertIsNone(dialog.worker)
                    self.assertEqual(dialog.datasets.currentData(), included['dataset_id'])
                    self.assertEqual(active_reference(config.root / 'cell-references')['dataset_id'], old['dataset_id'])
                    self.assertIn('use selected reference', dialog.status.text().lower())
                finally:
                    dialog.close()


if __name__ == '__main__':
    unittest.main()
