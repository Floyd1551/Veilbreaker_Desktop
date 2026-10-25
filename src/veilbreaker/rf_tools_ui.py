"""Reusable native dialog for offline field calculations."""
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QTextBrowser, QVBoxLayout, QWidget,
)
from .rf_tools import TOOLS, REGISTRY, calculate, format_snapshot


class RFToolsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('RF field calculators')
        self.resize(760, 780)
        self.inputs = {}
        self.snapshot = None
        layout = QVBoxLayout(self)
        heading = QLabel('RF field calculators')
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
        self.result = QTextBrowser()
        self.result.setAccessibleName('Calculation result and assumptions')
        layout.addWidget(self.result, 2)
        close = QPushButton('Close')
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self.calculate_button.clicked.connect(self.run_calculation)
        self.copy_button.clicked.connect(self.copy_result)
        self.save_button.clicked.connect(self.save_result)
        self.search.textChanged.connect(self.filter_tools)
        self.selector.currentIndexChanged.connect(self.select_tool)
        self.filter_tools('')

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
        self.invalidate()

    def invalidate(self, *_):
        self.snapshot = None
        self.result.clear()
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
