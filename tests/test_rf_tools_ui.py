import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from veilbreaker.rf_tools_ui import RFToolsDialog
from veilbreaker.field_tools import TOOLS, calculate, format_snapshot


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

    def test_every_tool_displays_and_exports_exact_snapshot(self):
        dialog = RFToolsDialog()
        with tempfile.TemporaryDirectory() as folder:
            for tool in TOOLS:
                with self.subTest(tool=tool.key):
                    dialog.selector.setCurrentIndex(dialog.selector.findData(tool.key))
                    dialog.run_calculation()
                    expected = calculate(tool.key, {f.key: f.default for f in tool.fields})
                    self.assertEqual(dialog.snapshot, expected)
                    self.assertEqual(dialog.result.toPlainText(), format_snapshot(expected))
                    dialog.copy_result()
                    self.assertEqual(self.app.clipboard().text(), format_snapshot(expected))
                    path = Path(folder) / (tool.key + '.json')
                    with patch('veilbreaker.rf_tools_ui.QFileDialog.getSaveFileName', return_value=(str(path), 'JSON snapshot (*.json)')):
                        dialog.save_result()
                    self.assertEqual(json.loads(path.read_text(encoding='utf-8')), expected)
                    first = next(iter(dialog.inputs.values()))
                    first.setText('nan')
                    dialog.run_calculation()
                    self.assertIsNone(dialog.snapshot)
                    self.assertFalse(dialog.copy_button.isEnabled())
                    self.assertFalse(dialog.save_button.isEnabled())
        dialog.close()

    def test_cancel_export_and_invalid_result_do_not_write(self):
        dialog = RFToolsDialog()
        dialog.run_calculation()
        original = dialog.snapshot
        with patch('veilbreaker.rf_tools_ui.QFileDialog.getSaveFileName', return_value=('', '')):
            dialog.save_result()
        self.assertEqual(dialog.snapshot, original)
        dialog.inputs['power'].setText('')
        with patch('veilbreaker.rf_tools_ui.QFileDialog.getSaveFileName') as chooser:
            dialog.save_result()
            chooser.assert_not_called()
        dialog.close()

    def test_fresnel_applicability_warning_is_visible(self):
        dialog = RFToolsDialog()
        dialog.selector.setCurrentIndex(dialog.selector.findData('fresnel'))
        for key, value in dict(frequency='1', distance='.001', position='.0005').items():
            dialog.inputs[key].setText(value)
        dialog.run_calculation()
        self.assertIn('WARNING', dialog.status.text())
        dialog.close()
