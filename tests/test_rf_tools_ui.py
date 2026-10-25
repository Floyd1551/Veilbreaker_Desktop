import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from PySide6.QtWidgets import QApplication
from veilbreaker.rf_tools_ui import RFToolsDialog


class RFToolsUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_result_invalidated_after_input_or_selection_change(self):
        dialog = RFToolsDialog()
        dialog.run_calculation()
        self.assertTrue(dialog.copy_button.isEnabled())
        self.assertIn('Power (mW)', dialog.result.toPlainText())
        dialog.inputs['power'].setText('bad')
        self.assertFalse(dialog.copy_button.isEnabled())
        self.assertEqual(dialog.result.toPlainText(), '')
        dialog.run_calculation()
        self.assertIn('enter a number', dialog.status.text())
        dialog.search.setText('wavelength')
        self.assertEqual(dialog.selector.count(), 1)
        dialog.run_calculation()
        self.assertIn('Quarter wavelength', dialog.result.toPlainText())
        dialog.search.setText('no such tool')
        self.assertFalse(dialog.calculate_button.isEnabled())
        self.assertFalse(dialog.copy_button.isEnabled())
        dialog.close()

    def test_search_preserves_inputs_for_same_calculator(self):
        dialog = RFToolsDialog()
        dialog.inputs['power'].setText('33')
        dialog.run_calculation()
        dialog.search.setText('power')
        self.assertEqual(dialog.inputs['power'].text(), '33')
        self.assertTrue(dialog.copy_button.isEnabled())
        dialog.close()
