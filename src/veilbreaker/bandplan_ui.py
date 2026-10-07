"""Searchable band reference and local import controls."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QFileDialog, QMessageBox, QCheckBox, QAbstractItemView
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
        self.search.setPlaceholderText('Search carrier, band, uplink/downlink, MHz or source')
        layout.addWidget(self.search)
        self.captured_only = QCheckBox('Only bands in the captured range')
        self.captured_only.setChecked(bool(parent.spectrum.points))
        layout.addWidget(self.captured_only)
        self.result_count = QLabel()
        layout.addWidget(self.result_count)
        self.table = QTableWidget(0, 6)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setHorizontalHeaderLabels(['MHz', 'Band / direction', 'General carrier association', 'Expected use', 'Source', 'Association limits'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setWordWrap(True)
        layout.addWidget(self.table, 1)
        actions = FlowLayout()
        self.focus_button = QPushButton('Zoom to selected band')
        self.focus_button.setEnabled(False)
        self.focus_button.clicked.connect(self.focus_selected)
        actions.addWidget(self.focus_button)
        for title, callback in [('Import CSV / JSON…', self.import_plan), ('Apply advanced U.S. plan', lambda: self.apply(default_plan())), ('Use basic FCC reference', lambda: self.apply(load_plan(Path(__file__).parent / 'assets' / 'us-selected-bands.json'))), ('Close', self.close)]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.search.textChanged.connect(self.refresh)
        self.captured_only.toggled.connect(self.refresh)
        self.table.itemSelectionChanged.connect(self.update_selection)
        self.table.cellDoubleClicked.connect(lambda *_: self.focus_selected())
        self.refresh()

    def selected_bounds(self):
        index = self.table.currentRow()
        view = self.parent().spectrum
        if not view.points or not 0 <= index < len(self.rows):
            return None
        band = self.rows[index]
        low, high = view.full_bounds
        start, stop = band['min_mhz'], band['max_mhz']
        if start == stop:
            if not low <= start < high:
                return None
            # Give center-frequency markers a visible window without assigning bandwidth.
            margin = max((high-low)/100, (high-low)/max(1, len(view.points))*2)
            start, stop = start-margin, stop+margin
        start, stop = max(start, low), min(stop, high)
        return (start, stop) if stop > start else None

    def update_selection(self):
        available = self.selected_bounds() is not None
        self.focus_button.setEnabled(available)
        self.focus_button.setToolTip('Zoom within the existing capture; no acquisition starts.' if available else 'Select a band overlapping a loaded spectrum capture.')

    def focus_selected(self):
        bounds = self.selected_bounds()
        if bounds is None:
            return
        self.parent().spectrum.set_bounds(*bounds)
        self.parent().tabs.setCurrentIndex(6)
        self.close()

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
        view = self.parent().spectrum
        if self.captured_only.isChecked():
            low, high = view.full_bounds
            rows = [b for b in rows if view.points and (
                low <= b['min_mhz'] < high if b['min_mhz'] == b['max_mhz'] else
                b['min_mhz'] < high and b['max_mhz'] > low)]
        self.table.clearSelection()
        self.table.setCurrentCell(-1, -1)
        self.rows = rows
        self.result_count.setText(f"{len(rows)} of {len(plan['bands'])} reference entries. Select a row to zoom; double-click also works." if rows else 'No matching bands. Clear the search or turn off the captured-range filter.')
        self.result_count.setWordWrap(True)
        self.table.setRowCount(len(rows))
        for i, band in enumerate(rows):
            for j, value in enumerate((f"{band['min_mhz']:g}–{band['max_mhz']:g}", band['label'] + '\n' + band.get('direction', 'Not specified'), band.get('carrier', 'Not specified'), band['service'], band['source'], band.get('association_note', ''))):
                item = QTableWidgetItem(value)
                from PySide6.QtCore import Qt
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setToolTip(value)
                self.table.setItem(i, j, item)
        self.table.resizeRowsToContents()
        self.update_selection()
