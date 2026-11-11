"""Review mobile survey points without changing Desktop or mobile evidence."""
import json
import uuid
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QLabel,
                               QMessageBox, QPlainTextEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from .mobile_survey_import import write_selected_capture


class MobileSurveyReviewDialog(QDialog):
    def __init__(self, parent, source, loaded):
        super().__init__(parent)
        self.source, self.loaded = source, loaded
        self.setWindowTitle('Review mobile survey')
        self.resize(980, 700)
        layout = QVBoxLayout(self)
        survey = loaded['survey']
        heading = QLabel(f"{survey['name']} · {survey['lifecycle']} · {len(survey['points'])} points\nCreated {survey['created_utc']}\nSource SHA-256: {loaded['sha256']}")
        heading.setTextFormat(Qt.TextFormat.PlainText); heading.setWordWrap(True)
        layout.addWidget(heading)
        info = QLabel('Review saved phone evidence and operator notes. Save a selected capture as JSON, then attach it in Investigate. This does not create a Desktop survey or run a test. Coordinates and identifiers may be included.')
        info.setTextFormat(Qt.TextFormat.PlainText); info.setWordWrap(True)
        layout.addWidget(info)
        self.points = QTableWidget(0, 5)
        self.points.setHorizontalHeaderLabels(['Point', 'Captured UTC', 'Outcome', 'Observations', 'Location'])
        self.points.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.points.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.points.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.points.horizontalHeader().setStretchLastSection(True)
        self.points.setRowCount(len(survey['points']))
        for index, point in enumerate(survey['points']):
            capture = point['capture']; observations = capture['observations']
            locations = sum(isinstance(o.get('location'), dict) and o['location'].get('status') == 'available' for o in observations)
            row = [str(index + 1), capture['created_utc'], capture['collection']['outcome'], str(len(observations)),
                   f'{locations} reported fix(es)' if locations else 'No available fix reported']
            for col, value in enumerate(row): self.points.setItem(index, col, QTableWidgetItem(value))
        layout.addWidget(self.points, 1)
        self.details = QPlainTextEdit(); self.details.setReadOnly(True)
        self.details.setAccessibleName('Mobile survey point details')
        layout.addWidget(self.details, 1)
        self.status = QLabel('Select a point to inspect its source capture and operator note.')
        self.status.setTextFormat(Qt.TextFormat.PlainText); self.status.setWordWrap(True)
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        self.save = QPushButton('Save selected capture as JSON…'); self.save.setEnabled(False)
        self.save.clicked.connect(self.save_capture); actions.addWidget(self.save)
        close = QPushButton('Close'); close.clicked.connect(self.reject); actions.addWidget(close)
        layout.addLayout(actions)
        self.points.itemSelectionChanged.connect(self.show_point)

    def show_point(self):
        index = self.points.currentRow()
        points = self.loaded['survey']['points']
        selected = bool(self.points.selectedItems()) and 0 <= index < len(points)
        self.save.setEnabled(selected)
        if not selected:
            self.details.clear(); return
        point = points[index]; capture = point['capture']
        detail = {'capture_id': capture['capture_id'], 'attached_utc': point['attached_utc'],
                  'operator_note': point.get('operator_note'), 'device': capture['device'],
                  'collection': capture['collection'], 'observations': capture['observations']}
        raw = json.dumps(detail, indent=2, ensure_ascii=False)
        self.details.setPlainText(raw[:40000] + ('\n[Preview truncated; the extracted capture retains all evidence.]' if len(raw) > 40000 else ''))
        self.status.setText('Operator notes remain in the mobile survey. The capture is re-encoded as JSON and has its own file hash. Keep the original survey for context.')

    def save_capture(self):
        index = self.points.currentRow()
        points = self.loaded['survey']['points']
        if not self.points.selectedItems() or not 0 <= index < len(points): return
        capture_id = str(uuid.UUID(points[index]['capture']['capture_id']))
        target, _ = QFileDialog.getSaveFileName(self, 'Save a new capture file', f'android-{capture_id}.json', 'JSON (*.json)')
        if not target: return
        try:
            write_selected_capture(self.source, self.loaded['sha256'], index, target)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Capture not saved', str(exc) + '\nChoose a new filename; the source survey remains unchanged.')
            return
        self.status.setText('Capture saved. In Investigate, choose Attach Android input and select the saved file. The mobile survey itself has not been imported.')
