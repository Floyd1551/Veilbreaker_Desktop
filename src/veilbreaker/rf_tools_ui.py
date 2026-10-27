"""Reusable native dialog for offline field calculations."""
import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QTextBrowser, QVBoxLayout, QWidget,
)
from .field_tools import TOOLS, REGISTRY, calculate, format_snapshot
from .paths import data_root
from .tool_presets import delete_preset, list_presets, save_preset


class RFToolsDialog(QDialog):
    def __init__(self, parent=None, embedded=False, preset_path=None):
        super().__init__(parent)
        self.embedded = embedded
        if embedded:
            self.setWindowFlags(Qt.WindowType.Widget)
        self.setWindowTitle('Field calculators')
        self.resize(760, 780)
        self.inputs = {}
        self.snapshot = None
        self.preset_path = Path(preset_path) if preset_path is not None else data_root() / 'tool-presets.json'
        layout = QVBoxLayout(self)
        heading = QLabel('Field calculators')
        heading.setObjectName('section')
        layout.addWidget(heading)
        caption = QLabel('Offline planning tools · Results are calculated estimates, not measured signals.')
        caption.setWordWrap(True)
        layout.addWidget(caption)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Find a calculator: power, wavelength, loss, margin…')
        self.search.setAccessibleName('Find a calculator')
        layout.addWidget(self.search)
        self.selector = QComboBox()
        self.selector.setAccessibleName('Calculator')
        layout.addWidget(self.selector)
        self.purpose = QLabel()
        self.purpose.setWordWrap(True)
        layout.addWidget(self.purpose)
        preset_heading = QLabel('Saved input presets · operator-entered specifications')
        preset_heading.setWordWrap(True)
        layout.addWidget(preset_heading)
        self.preset_selector = QComboBox()
        self.preset_selector.setAccessibleName('Saved calculator input preset')
        layout.addWidget(self.preset_selector)
        preset_actions = QHBoxLayout()
        self.preset_save_button = QPushButton('Save preset…')
        self.preset_load_button = QPushButton('Load inputs')
        self.preset_delete_button = QPushButton('Delete preset')
        for control in (self.preset_save_button, self.preset_load_button, self.preset_delete_button):
            preset_actions.addWidget(control)
        layout.addLayout(preset_actions)
        self.preset_status = QLabel()
        self.preset_status.setWordWrap(True)
        layout.addWidget(self.preset_status)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(140)
        self.form_widget = QWidget()
        self.form = QFormLayout(self.form_widget)
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        scroll.setWidget(self.form_widget)
        layout.addWidget(scroll, 1)
        actions = QHBoxLayout()
        self.calculate_button = QPushButton('Calculate')
        self.calculate_button.setDefault(True)
        self.copy_button = QPushButton('Copy result with inputs')
        self.save_button = QPushButton('Save result…')
        actions.addWidget(self.calculate_button)
        actions.addWidget(self.copy_button)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        from .rf_diagrams import RFDiagram
        self.diagram = RFDiagram(self)
        self.diagram.hide()
        layout.addWidget(self.diagram)
        from .engineering_diagrams import EngineeringDiagram
        self.flow_diagram = EngineeringDiagram(self)
        self.flow_diagram.hide()
        layout.addWidget(self.flow_diagram)
        self.result = QTextBrowser()
        self.result.setAccessibleName('Calculation result and assumptions')
        layout.addWidget(self.result, 2)
        close = QPushButton('Close')
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        close.setVisible(not embedded)
        self.calculate_button.clicked.connect(self.run_calculation)
        self.copy_button.clicked.connect(self.copy_result)
        self.save_button.clicked.connect(self.save_result)
        self.preset_save_button.clicked.connect(self._save_preset_clicked)
        self.preset_load_button.clicked.connect(self.load_selected_preset)
        self.preset_delete_button.clicked.connect(lambda: self.delete_selected_preset())
        self.search.textChanged.connect(self.filter_tools)
        self.selector.currentIndexChanged.connect(self.select_tool)
        self.filter_tools('')

    def reject(self):
        if not self.embedded:
            super().reject()

    def accept(self):
        if not self.embedded:
            super().accept()

    def filter_tools(self, query):
        previous = self.selector.currentData()
        self.selector.blockSignals(True)
        self.selector.clear()
        for tool in TOOLS:
            if query.casefold().strip() in (tool.title + ' ' + tool.purpose).casefold():
                self.selector.addItem(tool.title, tool.key)
        index = self.selector.findData(previous)
        if index >= 0:
            self.selector.setCurrentIndex(index)
        self.selector.blockSignals(False)
        if self.selector.currentData() != previous or not self.inputs:
            self.select_tool()

    def select_tool(self, *_):
        self.inputs = {}
        while self.form.rowCount():
            self.form.removeRow(0)
        tool = REGISTRY.get(self.selector.currentData())
        self.calculate_button.setEnabled(tool is not None)
        self.purpose.setText(tool.purpose if tool else 'No matching calculators. Try a broader search.')
        if tool:
            for field in tool.fields:
                entry = QLineEdit(f'{field.default:g}')
                entry.setAccessibleName(field.label)
                entry.setToolTip(f'Range: {field.minimum:g} to {field.maximum:g}. Decimal point or scientific notation accepted.')
                entry.textChanged.connect(self.invalidate)
                self.form.addRow(field.label, entry)
                self.inputs[field.key] = entry
        self.refresh_presets()
        self.invalidate()

    def refresh_presets(self, selected_id=None):
        self.preset_selector.clear()
        try:
            records = list_presets(self.preset_path, self.selector.currentData())
        except ValueError as exc:
            records = ()
            self.preset_status.setText(str(exc))
        else:
            self.preset_status.clear()
        for record in records:
            self.preset_selector.addItem(record.get('name', 'Unnamed preset'), record['id'])
            self.preset_selector.setItemData(self.preset_selector.count() - 1,
                                             record.get('notes', ''), Qt.ItemDataRole.ToolTipRole)
        if selected_id:
            index = self.preset_selector.findData(selected_id)
            if index >= 0:
                self.preset_selector.setCurrentIndex(index)
        self.preset_save_button.setEnabled(bool(self.selector.currentData()))
        self.preset_load_button.setEnabled(bool(records))
        self.preset_delete_button.setEnabled(bool(records))

    def _save_preset_clicked(self):
        details = QDialog(self)
        details.setWindowTitle('Save calculator input preset')
        form = QFormLayout(details)
        name = QLineEdit()
        name.setAccessibleName('Preset name')
        notes = QLineEdit()
        notes.setAccessibleName('Preset notes')
        form.addRow('Name', name)
        form.addRow('Notes (optional)', notes)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(details.accept)
        buttons.rejected.connect(details.reject)
        form.addRow(buttons)
        if details.exec() == QDialog.DialogCode.Accepted:
            self.save_current_preset(name.text(), notes.text())

    def save_current_preset(self, name, notes=''):
        try:
            record = save_preset(self.preset_path, name, self.selector.currentData(),
                                 {key: entry.text() for key, entry in self.inputs.items()}, notes)
        except (ValueError, OSError) as exc:
            self.preset_status.setText(f'Could not save preset: {exc}')
            return False
        self.refresh_presets(record['id'])
        self.preset_status.setText(f'Saved operator input preset: {record["name"]}. No measurement was created.')
        return True

    def load_selected_preset(self):
        preset_id = self.preset_selector.currentData()
        try:
            record = next((item for item in list_presets(self.preset_path, self.selector.currentData())
                           if item['id'] == preset_id), None)
            if record is None or set(record['inputs']) != set(self.inputs):
                raise ValueError('Selected preset is unavailable or does not match this calculator.')
            calculate(record['tool_id'], record['inputs'])
        except (ValueError, OSError) as exc:
            self.preset_status.setText(f'Could not load preset: {exc}')
            return False
        for key, value in record['inputs'].items():
            self.inputs[key].setText(f'{value:g}')
        self.invalidate()
        self.preset_status.setText(f'Loaded operator inputs from {record["name"]}. Choose Calculate for a new result.')
        return True

    def delete_selected_preset(self, confirm=True):
        preset_id = self.preset_selector.currentData()
        if not preset_id:
            return False
        if confirm and QMessageBox.question(self, 'Delete input preset',
                                            'Delete this saved calculator input preset?') != QMessageBox.StandardButton.Yes:
            return False
        try:
            removed = delete_preset(self.preset_path, preset_id)
        except (ValueError, OSError) as exc:
            self.preset_status.setText(f'Could not delete preset: {exc}')
            return False
        self.refresh_presets()
        self.preset_status.setText('Deleted saved input preset.' if removed else 'Preset was already absent.')
        return removed

    def invalidate(self, *_):
        self.snapshot = None
        self.result.clear()
        self.diagram.set_snapshot(None)
        self.flow_diagram.set_snapshot(None)
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.status.setText('Enter values and choose Calculate.' if self.inputs else '')

    def run_calculation(self):
        self.invalidate()
        if not self.selector.currentData():
            return
        try:
            self.snapshot = calculate(self.selector.currentData(), {k: entry.text() for k, entry in self.inputs.items()})
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self.result.setPlainText(format_snapshot(self.snapshot))
        self.diagram.set_snapshot(self.snapshot)
        self.flow_diagram.set_snapshot(self.snapshot)
        self.copy_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.status.setText('WARNING: Approximation is unsuitable for clearance decisions at these inputs. See limitations below.'
                            if self.snapshot['limitations'].startswith('WARNING:') else
                            'Calculated estimate. Review the assumptions below before applying it to a survey.')

    def copy_result(self):
        if self.snapshot is not None:
            QApplication.clipboard().setText(format_snapshot(self.snapshot))
            self.status.setText('Copied result, inputs, method and limitations.')

    def save_result(self):
        if self.snapshot is None:
            return
        target, selected = QFileDialog.getSaveFileName(
            self, 'Save calculation snapshot', self.snapshot['tool_id'] + '.txt',
            'Text report (*.txt);;JSON snapshot (*.json)')
        if not target:
            return
        path = Path(target)
        # A typed extension takes precedence over the selected chooser filter.
        as_json = path.suffix.lower() == '.json' or (not path.suffix and selected.startswith('JSON'))
        # Keep the exact chooser path so its overwrite confirmation covers the file written.
        content = json.dumps(self.snapshot, ensure_ascii=False, indent=2, allow_nan=False) if as_json else format_snapshot(self.snapshot)
        try:
            path.write_text(content + '\n', encoding='utf-8')
        except OSError as exc:
            self.status.setText(f'Could not save calculation: {exc}')
            return
        self.status.setText(f'Saved calculation snapshot: {path}')
