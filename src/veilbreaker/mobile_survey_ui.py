"""Review mobile survey points without changing Desktop or mobile evidence."""
import json
import uuid
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QLabel,
                               QMessageBox, QPlainTextEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from .mobile_survey_import import export_mobile_survey_bundle, load_mobile_survey, write_selected_capture


class MobileSurveyReviewDialog(QDialog):
    def __init__(self, parent, source, loaded, attach_input=None):
        super().__init__(parent)
        self.source, self.loaded = source, loaded
        self.attach_input = attach_input
        self.setWindowTitle('Review mobile survey')
        self.resize(980, 700)
        layout = QVBoxLayout(self)
        survey = loaded['survey']
        heading = QLabel(f"{survey['name']} · {survey['lifecycle']} · {len(survey['points'])} points\nCreated {survey['created_utc']}\nSource SHA-256: {loaded['sha256']}")
        heading.setTextFormat(Qt.TextFormat.PlainText); heading.setWordWrap(True)
        layout.addWidget(heading)
        info = QLabel('Review saved phone evidence and operator notes. Save a selected capture or export all points to a new folder. This does not create a Desktop survey or run a test. Coordinates and identifiers may be included.')
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
        self.attach = QPushButton('Save and attach as input…'); self.attach.setEnabled(False)
        self.attach.setVisible(attach_input is not None)
        self.attach.clicked.connect(self.attach_capture); actions.addWidget(self.attach)
        batch = QPushButton('Export all points to folder…'); batch.clicked.connect(self.export_all); actions.addWidget(batch)
        close = QPushButton('Close'); close.clicked.connect(self.reject); actions.addWidget(close)
        layout.addLayout(actions)
        map_button = QPushButton('Preview recorded locations on map…')
        map_button.clicked.connect(self.preview_map); layout.addWidget(map_button)
        self.points.itemSelectionChanged.connect(self.show_point)

    def show_point(self):
        index = self.points.currentRow()
        points = self.loaded['survey']['points']
        selected = bool(self.points.selectedItems()) and 0 <= index < len(points)
        self.save.setEnabled(selected)
        self.attach.setEnabled(selected and self.attach_input is not None)
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
        self._save_capture(False)

    def attach_capture(self):
        self._save_capture(True)

    def _save_capture(self, attach):
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
        if attach and self.attach_input is not None:
            if self.attach_input(target):
                self.accept()
                return
            self.status.setText('Capture saved, but no input was attached. The mobile survey remains unchanged.')
        else:
            self.status.setText('Capture saved. In Investigate, choose Attach Android input and select the saved file. The mobile survey itself has not been imported.')

    def export_all(self):
        parent = QFileDialog.getExistingDirectory(self, 'Choose a parent folder for a new survey export')
        if not parent: return
        folder = Path(parent) / ('mobile-survey-' + str(uuid.UUID(self.loaded['survey']['survey_id'])))
        try:
            export_mobile_survey_bundle(self.source, self.loaded['sha256'], folder)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Survey not exported', str(exc) + '\nChoose a parent without an existing export folder. The source survey remains unchanged.')
            return
        self.status.setText('Exported the original survey, individual captures, and a provenance manifest to a new folder. No Desktop survey was created.')

    def preview_map(self):
        from .mobile_survey_map import build_mobile_survey_map
        from .map_ui import MapWindow
        try:
            current = load_mobile_survey(self.source)
            if current['sha256'] != self.loaded['sha256']:
                raise ValueError('Mobile survey changed since preview; reopen it before mapping.')
            model = build_mobile_survey_map(current)
            window = MapWindow(self, model, None, config=None)
            window.exec()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Map preview unavailable', str(exc))
