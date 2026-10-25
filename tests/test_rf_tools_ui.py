import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
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

    def test_save_json_and_text_and_invalidation(self):
        dialog = RFToolsDialog()
        self.assertFalse(dialog.save_button.isEnabled())
        dialog.run_calculation()
        with tempfile.TemporaryDirectory() as folder:
            for suffix, selected in [('json', 'JSON snapshot (*.json)'), ('txt', 'Text report (*.txt)')]:
                target = Path(folder) / ('result.' + suffix)
                with patch('veilbreaker.rf_tools_ui.QFileDialog.getSaveFileName', return_value=(str(target), selected)):
                    dialog.save_result()
                content = target.read_text(encoding='utf-8')
                if suffix == 'json':
                    self.assertEqual(json.loads(content)['inputs']['power'], 20)
                    self.assertIn('limitations', json.loads(content))
                else:
                    self.assertIn('Inputs', content)
                    self.assertIn('Method', content)
            directory_target = Path(folder) / 'directory.txt'
            directory_target.mkdir()
            with patch('veilbreaker.rf_tools_ui.QFileDialog.getSaveFileName', return_value=(str(directory_target), 'Text report (*.txt)')):
                dialog.save_result()
            self.assertIn('Could not save', dialog.status.text())
            exact = Path(folder) / 'no-extension'
            with patch('veilbreaker.rf_tools_ui.QFileDialog.getSaveFileName', return_value=(str(exact), 'JSON snapshot (*.json)')):
                dialog.save_result()
            self.assertEqual(json.loads(exact.read_text(encoding='utf-8'))['tool_id'], 'power_dbm')
            self.assertFalse(exact.with_suffix('.json').exists())
        dialog.inputs['power'].setText('30')
        self.assertFalse(dialog.save_button.isEnabled())
        dialog.close()
