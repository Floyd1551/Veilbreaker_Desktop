import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from veilbreaker.core import AppConfig
from veilbreaker.cell_reference import activate_reference, active_reference, import_reference
from veilbreaker.cell_reference_ui import CellReferenceDialog
from test_cell_reference import HEADER, ROW, META


class CellReferenceIntegrityUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_legacy_and_reimport_are_distinguishable_without_changing_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = AppConfig(data_dir=tmp)
            root = config.root / 'cell-references'
            source = Path(tmp) / 'cells.csv'
            source.write_text(HEADER + ROW, encoding='utf-8')
            legacy = import_reference(root, source, META, lambda: False, lambda _: None)
            path = root / legacy['dataset_id'] / 'manifest.json'
            manifest = json.loads(path.read_text(encoding='utf-8'))
            manifest.pop('database_sha256'); manifest.pop('database_bytes')
            path.write_text(json.dumps(manifest), encoding='utf-8')
            activate_reference(root, legacy['dataset_id'])
            fresh = import_reference(root, source, META, lambda: False, lambda _: None)
            with patch('veilbreaker.deployment_data.seed_reference'):
                dialog = CellReferenceDialog(None, config)
            try:
                old_index = dialog.datasets.findData(legacy['dataset_id'])
                new_index = dialog.datasets.findData(fresh['dataset_id'])
                self.assertIn('legacy', dialog.datasets.itemText(old_index).lower())
                self.assertIn('checksum recorded', dialog.datasets.itemText(new_index).lower())
                self.assertNotIn('verified', dialog.datasets.itemText(new_index).lower())
                dialog.job_ready({'imported': fresh})
                self.assertEqual(dialog.datasets.currentData(), fresh['dataset_id'])
                self.assertEqual(active_reference(root)['dataset_id'], legacy['dataset_id'])
            finally:
                dialog.close()


if __name__ == '__main__':
    unittest.main()
