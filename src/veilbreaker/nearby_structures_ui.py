"""Explicit operator selection of a physical structure near a map receiver."""
import copy
import math
from functools import partial

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from .background_dialog import JobDialog
from .regional_packs import RegionalPackStore


def _receiver_location(receiver):
    if not isinstance(receiver, dict):
        raise ValueError('Select a receiver location on the map.')
    lat, lon = receiver.get('latitude_deg'), receiver.get('longitude_deg')
    if (type(lat) not in (int, float) or type(lon) not in (int, float) or
            not math.isfinite(lat) or not math.isfinite(lon) or abs(lat) > 90 or abs(lon) > 180):
        raise ValueError('Select a receiver with valid geographic coordinates.')
    manual = receiver.get('manual') is True
    if manual:
        if receiver.get('source') != 'operator' or receiver.get('observation_id') != 'Operator placement':
            raise ValueError('Manual receiver coordinates must be an operator map placement.')
        provenance = 'operator_map_placement'
    else:
        quality = receiver.get('quality')
        if not isinstance(quality, dict) or quality.get('qualified') is not True:
            raise ValueError('Select a qualified recorded location or an operator map placement.')
        provenance = 'qualified_location'
    return float(lat), float(lon), provenance


def receiver_endpoint_context(receiver, candidate):
    """Preserve the receiver provenance and explicit structure selection independently."""
    lat, lon, provenance = _receiver_location(receiver)
    if not isinstance(candidate, dict) or candidate.get('reference_kind') != 'physical structure':
        raise ValueError('Select a physical structure reference.')
    location = {'latitude_deg': lat, 'longitude_deg': lon}
    for key in ('source', 'provider', 'horizontal_accuracy_m', 'fix_age_ms', 'fix_utc', 'received_utc', 'mock', 'placed_utc'):
        if key in receiver:
            location[key] = receiver[key]
    observation = dict(observation_id=receiver.get('observation_id'), location=location,
                       position_source=provenance, location_quality=copy.deepcopy(receiver.get('quality', {})))
    selected = copy.deepcopy(candidate)
    selected['selection_method'] = 'operator_selected'
    map_receiver = dict(run_id=receiver.get('run_id'), observation_id=receiver.get('observation_id'),
                        latitude_deg=lat, longitude_deg=lon, manual=receiver.get('manual') is True)
    for key in ('placed_utc', 'source_kind', 'mobile_capture_id', 'mobile_survey_sha256',
                'source', 'provider', 'fix_utc', 'received_utc', 'horizontal_accuracy_m', 'fix_age_ms', 'mock'):
        if key in receiver:
            map_receiver[key] = receiver[key]
    context = dict(run_id=receiver.get('run_id'), observation=observation, candidate=selected,
                   map_receiver=map_receiver)
    for key in ('capture_sha256', 'source_kind', 'mobile_capture_id', 'mobile_survey_id', 'mobile_survey_sha256'):
        if key in receiver:
            context[key] = receiver[key]
    return context


def _search_job(root, lat, lon, radius, cancelled, progress):
    from .nearby_structures import nearby_structures
    progress('Checking installed physical-structure packs…')
    result = nearby_structures(RegionalPackStore(root), lat, lon, radius_km=radius,
                               limit=30, cancelled=cancelled)
    return dict(kind='search', result=result)


def _verify_job(root, candidate, action, cancelled, progress):
    progress('Verifying the selected structure reference…')
    store = RegionalPackStore(root)
    row = store._manifest(candidate['pack_id'])
    if row.get('kind') != 'structures':
        raise ValueError('The selected structure pack is no longer available.')
    for key in ('source', 'source_date', 'license', 'sha256', 'bounds_wgs84', 'coverage_note'):
        if row.get(key) != candidate.get(key):
            raise ValueError('Structure pack provenance changed. Search again.')
    if row.get('name') != candidate.get('pack_name') or not store.verify(candidate['pack_id'], cancelled):
        raise ValueError('Structure pack verification failed. Search again after restoring the pack.')
    return dict(kind='verified', candidate=copy.deepcopy(candidate), action=action)


class NearbyStructuresDialog(JobDialog):
    """Find physical records and explicitly assess a chosen receiver-to-structure path."""
    def __init__(self, parent, config, receiver, on_map=None, on_assessment=None):
        super().__init__(parent)
        lat, lon, provenance = _receiver_location(receiver)
        self.config, self.receiver = config, copy.deepcopy(receiver)
        self.latitude, self.longitude = lat, lon
        self.on_map, self.on_assessment = on_map, on_assessment
        self.candidates, self.assessment = [], None
        self.assessment_saved = False
        self.setWindowTitle('Nearby physical structures'); self.resize(950, 700)
        layout = QVBoxLayout(self)
        intro = QLabel('Search installed offline physical-structure packs around this receiver. A structure record does not establish a serving cell, carrier, antenna location, or line of sight.')
        intro.setWordWrap(True); intro.setTextFormat(Qt.TextFormat.PlainText); layout.addWidget(intro)
        position = QLabel(('Operator map placement' if provenance == 'operator_map_placement' else 'Qualified recorded location') +
                          f' · {lat:.6f}, {lon:.6f}\nSource: {receiver.get("source") or "Not reported"} · Provider: {receiver.get("provider") or "Not reported"}')
        position.setWordWrap(True); position.setTextFormat(Qt.TextFormat.PlainText); layout.addWidget(position)
        form = QFormLayout()
        self.radius = QDoubleSpinBox(); self.radius.setRange(0.1, 100); self.radius.setValue(10); self.radius.setDecimals(1); self.radius.setSuffix(' km')
        self.radius.setAccessibleName('Physical structure search radius')
        form.addRow('Search radius', self.radius); layout.addLayout(form)
        self.search_button = QPushButton('Search installed structures'); self.search_button.clicked.connect(self.search)
        layout.addWidget(self.search_button)
        self.table = QTableWidget(0, 4); self.table.setHorizontalHeaderLabels(['Structure ID', 'Distance km', 'Height AGL m', 'Source / date'])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self.select_candidate); layout.addWidget(self.table, 1)
        self.details = QLabel('Select a physical structure to inspect its reference provenance.')
        self.details.setWordWrap(True); self.details.setTextFormat(Qt.TextFormat.PlainText); layout.addWidget(self.details)
        row = QHBoxLayout(); layout.addLayout(row)
        self.map_button = QPushButton('Show selected path'); self.map_button.clicked.connect(self.show_selected); row.addWidget(self.map_button)
        self.path_button = QPushButton('Assess terrain / LOS…'); self.path_button.clicked.connect(self.assess_selected); row.addWidget(self.path_button)
        row = QHBoxLayout(); layout.addLayout(row)
        self.report_button = QPushButton('View assessment'); self.report_button.clicked.connect(self.view_report); row.addWidget(self.report_button)
        self.export_button = QPushButton('Export assessment JSON…'); self.export_button.clicked.connect(self.export_report); row.addWidget(self.export_button)
        self.save_button = QPushButton('Save to survey'); self.save_button.clicked.connect(self.save_assessment)
        self.save_button.setVisible(on_assessment is not None); row.addWidget(self.save_button)
        self.status = QLabel('Select a search radius and search installed packs.'); self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText); layout.addWidget(self.status)
        self.controls = [self.radius, self.search_button, self.table, self.map_button, self.path_button, self.report_button, self.export_button, self.save_button]
        self.radius.valueChanged.connect(self.invalidate_results)
        self.select_candidate()

    def set_busy(self, busy):
        super().set_busy(busy)
        if not busy:
            self.select_candidate()

    def selected(self):
        index = self.table.currentRow()
        return self.candidates[index] if 0 <= index < len(self.candidates) else None

    @Slot()
    def select_candidate(self):
        candidate = self.selected()
        available = candidate is not None and self.worker is None
        self.map_button.setEnabled(available and self.on_map is not None)
        self.path_button.setEnabled(available)
        self.report_button.setEnabled(self.assessment is not None and self.worker is None)
        self.export_button.setEnabled(self.assessment is not None and self.worker is None)
        self.save_button.setEnabled(self.assessment is not None and not self.assessment_saved and self.on_assessment is not None and self.worker is None)
        if candidate:
            self.details.setText('Physical structure ' + str(candidate.get('structure_id', 'Unknown')) +
                ' · Owner: ' + str(candidate.get('owner') or 'Not reported') +
                '\nSource: ' + str(candidate.get('source')) + ' · Date: ' + str(candidate.get('source_date')) +
                ' · License: ' + str(candidate.get('license')) + '\nPack SHA-256: ' + str(candidate.get('sha256')) +
                '\nPack coverage: ' + str(candidate.get('coverage_note') or 'Not reported') +
                '\nPosition reference: ' + str(candidate.get('position_source') or 'Not reported') +
                '\nReported structure height is not an antenna height. The serving relationship is unverified.' +
                (('\nIdentical reference also found in these packs, verified at search time: ' +
                  '; '.join(str(p.get('pack_name') or p.get('pack_id') or 'Unknown') for p in candidate['alternate_packs'][:8]) +
                  (f"; {len(candidate['alternate_packs']) - 8} more" if len(candidate['alternate_packs']) > 8 else ''))
                 if candidate.get('alternate_packs') else ''))
        else:
            self.details.setText('Select a physical structure to inspect its reference provenance.')

    @Slot()
    def invalidate_results(self):
        self.candidates = []; self.table.setRowCount(0); self.select_candidate()
        self.status.setText('Search radius changed. Search again before selecting a structure.')

    @Slot()
    def search(self):
        self.invalidate_results()
        self.start_job(partial(_search_job, self.config.root / 'regional-packs', self.latitude, self.longitude, self.radius.value()))

    @Slot()
    def show_selected(self):
        candidate = self.selected()
        if candidate and self.on_map:
            self.start_job(partial(_verify_job, self.config.root / 'regional-packs', copy.deepcopy(candidate), 'map'))

    @Slot()
    def assess_selected(self):
        candidate = self.selected()
        if candidate:
            self.start_job(partial(_verify_job, self.config.root / 'regional-packs', copy.deepcopy(candidate), 'assess'))

    @Slot(object)
    def job_ready(self, value):
        if self.closing:
            return
        if value.get('kind') == 'search':
            result = value['result']; self.candidates = result['candidates']
            self.table.setRowCount(len(self.candidates))
            for i, candidate in enumerate(self.candidates):
                height = candidate.get('height_agl_m')
                values = [candidate.get('structure_id'), f"{candidate['distance_m']/1000:.2f}",
                          'Not reported' if height is None else f'{height:g}',
                          f"{candidate.get('source', 'Unknown')} · {candidate.get('source_date', 'Unknown')}"]
                for j, item in enumerate(values):
                    self.table.setItem(i, j, QTableWidgetItem(str(item)))
            message = f"{result['total_matches']} structure record(s) within {self.radius.value():g} km; showing {len(self.candidates)}."
            if result.get('duplicate_records'):
                message += f" {result['duplicate_records']} duplicate pack record(s) combined."
            if result.get('declared_coverage'):
                message += ' Declared pack extent coverage: ' + result['declared_coverage'] + '. Extents do not imply a complete inventory.'
            if result.get('truncated'):
                message += ' Results are limited; narrow the radius to inspect more.'
            if result.get('warnings'):
                message += ' ' + ' '.join(map(str, result['warnings']))
            self.status.setText(message); self.select_candidate()
            return
        if value.get('kind') != 'verified':
            return
        candidate = value['candidate']
        candidate['selection_method'] = 'operator_selected'
        if value['action'] == 'map':
            self.on_map(copy.deepcopy(self.receiver), candidate)
            self.status.setText('Showing the selected receiver-to-structure path. It is not a serving-cell match or a line-of-sight result.')
        elif value['action'] == 'assess':
            from .path_assessment_ui import PathAssessmentDialog
            dialog = PathAssessmentDialog(self, self.config, receiver_endpoint_context(self.receiver, candidate))
            if dialog.exec() and dialog.assessment:
                self.assessment = dialog.assessment
                self.assessment_saved = False
                if self.on_assessment:
                    self.save_assessment()
                else:
                    self.status.setText('Assessment kept in this window. View it or explicitly export its JSON.')
                self.select_candidate()

    @Slot()
    def save_assessment(self):
        if self.assessment is None or self.assessment_saved or self.on_assessment is None:
            return
        try:
            result = self.on_assessment(copy.deepcopy(self.assessment))
            self.assessment_saved = True
            self.status.setText(str(result) if result else 'Assessment accepted for the survey. Original receiver evidence is unchanged.')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.status.setText('Assessment remains in this window; survey save failed: ' + str(exc))
        self.select_candidate()

    @Slot()
    def view_report(self):
        if self.assessment is None:
            return
        from .path_assessment_report import assessment_html
        from .report_viewer import ReportViewer
        body = ('<html><body>' + assessment_html(self.assessment) + '</body></html>').encode('utf-8')
        self.viewer = ReportViewer(self, 'Physical-structure path assessment', reports=[('path-assessment.html', body)])
        self.viewer.show()

    @Slot()
    def export_report(self):
        if self.assessment is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Export path assessment', 'structure-path-assessment.json', 'JSON (*.json)')
        if path:
            try:
                from .recovery import atomic_json
                atomic_json(path, self.assessment)
                self.status.setText('Assessment JSON exported. Original evidence is unchanged.')
            except (OSError, ValueError, TypeError) as exc:
                self.status.setText('Could not export assessment: ' + str(exc))
