"""Searchable band reference and local import controls."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QFileDialog, QMessageBox
from .bandplan import default_plan, load_plan, NOTICE
from pathlib import Path
from .widgets import FlowLayout


class BandPlanDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Spectrum band reference')
        self.resize(900, 520)
        layout = QVBoxLayout(self)
        self.caption = QLabel()
        self.caption.setWordWrap(True)
        layout.addWidget(self.caption)
        notice = QLabel(NOTICE)
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search band name, MHz, use or source')
        layout.addWidget(self.search)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['MHz', 'Band', 'Expected use', 'Source'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setWordWrap(True)
        layout.addWidget(self.table, 1)
        actions = FlowLayout()
        for title, callback in [('Import CSV / JSON…', self.import_plan), ('Restore supplied U.S. reference', lambda: self.apply(default_plan())), ('Use basic FCC reference', lambda: self.apply(load_plan(Path(__file__).parent / 'assets' / 'us-selected-bands.json'))), ('Close', self.close)]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.search.textChanged.connect(self.refresh)
        self.refresh()

    def apply(self, plan):
        try:
            self.parent().apply_band_plan(plan)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Band plan was not changed', str(exc))
            return
        self.refresh()

    def import_plan(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Import band plan', '', 'Band plans (*.csv *.json)')
        if path:
            try:
                self.apply(load_plan(path))
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, 'Cannot import band plan', str(exc))

    def refresh(self):
        plan = self.parent().spectrum.band_plan
        self.caption.setText(f"{plan['name']} • Region: {plan['region']} • Reference version: {plan['version']}")
        query = self.search.text().casefold()
        rows = [b for b in plan['bands'] if query in ' '.join(str(v) for v in b.values()).casefold()]
        self.table.setRowCount(len(rows))
        for i, band in enumerate(rows):
            for j, value in enumerate((f"{band['min_mhz']:g}–{band['max_mhz']:g}", band['label'], band['service'], band['source'])):
                item = QTableWidgetItem(value)
                from PySide6.QtCore import Qt
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setToolTip(value)
                self.table.setItem(i, j, item)
        self.table.resizeRowsToContents()
