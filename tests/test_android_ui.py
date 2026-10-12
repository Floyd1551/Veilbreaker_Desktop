import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import unittest
from PySide6.QtWidgets import QApplication
from veilbreaker.android_capture import load_capture
from veilbreaker.android_ui import AndroidImportDialog


class AndroidUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_explicit_selection_and_neighbor_rejection(self):
        capture = load_capture(Path('examples/android-cellular-v1.json'))
        dialog = AndroidImportDialog(None,capture)
        self.assertIsNone(dialog.selection())
        dialog.observations.setCurrentIndex(1)
        self.assertFalse(dialog.import_button.isEnabled())
        dialog.cells.selectRow(0)
        self.assertEqual(dialog.selection(),('snapshot-1',0))
        self.assertTrue(dialog.import_button.isEnabled())
        capture['envelope']['observations'][0]['cells'][0]['registered'] = False
        dialog.show_cell()
        self.assertFalse(dialog.import_button.isEnabled())
        dialog.reject()

    def test_registered_cell_with_none_role_can_be_imported(self):
        capture = load_capture(Path('examples/android-cellular-v1.json'))
        capture['envelope']['observations'][0]['cells'][0]['connection_status'] = 'none'
        dialog = AndroidImportDialog(None, capture)
        dialog.observations.setCurrentIndex(1)
        dialog.cells.selectRow(0)
        self.assertTrue(dialog.import_button.isEnabled())
        self.assertIn('not confirmed', dialog.message.text())
        dialog.reject()
