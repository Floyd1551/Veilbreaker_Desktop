"""Explicit selection of a single phone observation and serving cell."""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QTableWidget, QTableWidgetItem, QPlainTextEdit, QPushButton, QCheckBox, QHBoxLayout, QAbstractItemView
from .android_capture import normalize_selection


class AndroidImportDialog(QDialog):
    def __init__(self, parent, capture):
        super().__init__(parent)
        self.capture = capture
        self.setWindowTitle('Review Android cellular capture')
        self.resize(1000, 760)
        layout = QVBoxLayout(self)
        envelope = capture['envelope']
        device = envelope['device']
        heading = QLabel(f"{device['manufacturer']} {device['model']} · Android {device['android_version']} · {envelope['collection']['outcome']}\nSource SHA-256: {capture['sha256']}")
        heading.setTextFormat(Qt.TextFormat.PlainText)
        heading.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(QLabel('Select an observation, then a registered serving cell. Neighbors are reference evidence only.'))
        self.observations = QComboBox()
        self.observations.setAccessibleName('Android observation and subscription')
        self.observations.addItem('Choose an observation…', None)
        for obs in envelope['observations']:
            self.observations.addItem(f"{obs['observation_id']} · {obs['subscription_key']} · {obs['received_utc']} · {obs['outcome']}", obs['observation_id'])
        layout.addWidget(self.observations)
        self.cells = QTableWidget(0, 5)
        self.cells.setHorizontalHeaderLabels(['Radio','Registered','Role','Age at receipt (ms)','Identity'])
        self.cells.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cells.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.cells.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.cells.horizontalHeader().setStretchLastSection(True)
        for column, width in enumerate((85, 100, 110, 160)):
            self.cells.setColumnWidth(column, width)
        layout.addWidget(self.cells, 1)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setAccessibleName('Original cell and optional location details')
        layout.addWidget(self.details, 1)
        self.message = QLabel('No observation selected. No measurement or import has started.')
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.message)
        self.repeat = QCheckBox('Allow another import if this capture is already in history')
        layout.addWidget(self.repeat)
        actions = QHBoxLayout()
        self.import_button = QPushButton('Import selected serving cell')
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.accept)
        actions.addWidget(self.import_button)
        cancel = QPushButton('Cancel')
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        layout.addLayout(actions)
        self.observations.currentIndexChanged.connect(self.show_observation)
        self.cells.itemSelectionChanged.connect(self.show_cell)

    def observation(self):
        return next((o for o in self.capture['envelope']['observations'] if o['observation_id'] == self.observations.currentData()), None)

    def show_observation(self):
        self.cells.clearSelection()
        self.cells.setCurrentCell(-1,-1)
        obs = self.observation()
        cells = obs['cells'] if obs else []
        self.cells.setRowCount(len(cells))
        for row, cell in enumerate(cells):
            for col, value in enumerate([cell['radio'], cell.get('registered'), cell['connection_status'], cell.get('age_ms'), cell['identity']]):
                display = 'Unknown' if value is None else value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
                self.cells.setItem(row,col,QTableWidgetItem(display))
        self.show_cell()

    def selection(self):
        if not self.cells.selectedItems(): return None
        try:
            normalize_selection(self.capture['envelope'],self.observations.currentData(),self.cells.currentRow())
        except ValueError:
            return None
        return self.observations.currentData(), self.cells.currentRow()

    def show_cell(self):
        obs = self.observation()
        index = self.cells.currentRow()
        valid = obs and self.cells.selectedItems() and 0 <= index < len(obs['cells'])
        self.details.setPlainText(json.dumps({'cell':obs['cells'][index], 'location':obs.get('location'), 'source_collection':self.capture['envelope']['collection']},indent=2,ensure_ascii=False) if valid else '')
        selected = self.selection()
        self.import_button.setEnabled(selected is not None)
        self.message.setText('Selected data will be imported, not collected live. Age is measured at phone receipt; cached values are not fresh measurements. Location is retained as metadata only.' if selected else 'Choose an LTE/NR row with Registered = true. Unregistered neighbors and unknown registration cannot be analyzed.')

        if selected and obs['cells'][index]['connection_status'] in {'none', 'unknown'}:
            self.message.setText(self.message.text() + ' Android reports this cell as registered, but its primary/secondary role is not confirmed; the original role is preserved.')
