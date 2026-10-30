"""Manual geographic and indoor placement, always separate from captured GPS."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QPen, QColor
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QFormLayout, QGraphicsView, QGraphicsScene, QFileDialog,
    QInputDialog, QMessageBox, QWidget)
from .survey import read_session
from .survey_spatial import (load_spatial, import_floor, read_floor, save_placement,
                             clear_placement, calibrate_floor, remove_floor, unplaced_measurements)
from .widgets import FlowLayout
from .survey_metrics import (METRICS, UNATTRIBUTED, available_metrics, clean_metrics,
    floor_measurements, provenance_label, source_options, cell_group_options, select_cell_group)
from .display_labels import source_label


class FloorCanvas(QGraphicsView):
    picked = Signal(float, float)
    marker_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.dimensions = None
        self.press_position = None
        self.preview = None
        self.marker_positions = []
        self.setMinimumHeight(280)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setAccessibleName('Floor plan. Click to place a point; drag to pan; scroll to zoom.')

    def set_floor(self, image, markers, metric_mode=False):
        self.scene().clear()
        self.preview = None
        self.marker_positions = []
        self.dimensions = (image.width(), image.height())
        self.scene().addPixmap(QPixmap.fromImage(image))
        radius = max(6, max(image.width(), image.height()) / 100)
        for marker in markers:
            x, y = marker['x'], marker['y']
            metric = marker.get('metric')
            px, py = x * image.width(), y * image.height()
            dot = self.scene().addEllipse(px - radius, py - radius, radius * 2, radius * 2,
                                   QPen(QColor('#ba95f5'), max(2, radius / 4)),
                                   QColor(metric['color'] if metric else ('#65748b' if metric_mode else '#ba95f5')))
            value = f"{metric['label']} {metric['value']:g} {metric['unit']} · saved run metric" if metric else 'Selected metric unavailable'
            dot.setToolTip(f"{marker['scan_label']} · operator floor placement; not GPS evidence. {value}.")
            if marker.get('run_id'):
                self.marker_positions.append((px, py, radius, marker['run_id']))
            caption = str(marker['number']) + (f" · {metric['value']:g} {metric['unit']}" if metric_mode and metric else '')
            text = self.scene().addSimpleText(caption)
            text.setBrush(QColor('#111111'))
            label_x, label_y = px + radius + 2, py - radius
            extent = text.boundingRect()
            background = self.scene().addRect(label_x - 2, label_y - 1, extent.width() + 4, extent.height() + 2,
                                              QPen(QColor('#46566c')), QColor('#e6eef5'))
            background.setZValue(1)
            text.setPos(label_x, label_y)
            text.setZValue(2)
        self.scene().setSceneRect(0, 0, image.width(), image.height())

    def fit_floor(self):
        if self.dimensions:
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def show_preview(self, x, y):
        if not self.dimensions:
            return
        if self.preview is not None:
            self.scene().removeItem(self.preview)
        width, height = self.dimensions
        radius = max(width, height) / 80
        self.preview = self.scene().addEllipse(x * width - radius, y * height - radius, radius * 2, radius * 2,
                                               QPen(QColor('#111111')), QColor('#55d7c0'))

    def wheelEvent(self, event):
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        if .02 <= self.transform().m11() * factor <= 100:
            self.scale(factor, factor)
        event.accept()

    def mousePressEvent(self, event):
        self.press_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        moved = self.press_position is None or (event.position().toPoint() - self.press_position).manhattanLength() > 4
        super().mouseReleaseEvent(event)
        if not moved and event.button() == Qt.MouseButton.LeftButton and self.dimensions:
            point = self.mapToScene(event.position().toPoint())
            for px, py, radius, run_id in reversed(self.marker_positions):
                if (point.x() - px) ** 2 + (point.y() - py) ** 2 <= (radius + 2) ** 2:
                    self.marker_selected.emit(run_id)
                    return
            x, y = point.x() / self.dimensions[0], point.y() / self.dimensions[1]
            if 0 <= x <= 1 and 0 <= y <= 1:
                self.picked.emit(x, y)


class SpatialDialog(QDialog):
    def __init__(self, parent, config, path):
        super().__init__(parent)
        self.config, self.path = config, path
        self.session = read_session(config, path)
        self.pending = None
        self.calibration_points = None
        self.pick_map = None
        self.setWindowTitle('Survey point placement')
        self.resize(950, 800)
        layout = QVBoxLayout(self)
        caption = QLabel('Place a survey point or scan on a map or floor plan. Purple pins are operator placement, not GPS evidence.')
        caption.setWordWrap(True)
        layout.addWidget(caption)
        self.placement_summary = QLabel()
        self.placement_summary.setWordWrap(True)
        layout.addWidget(self.placement_summary)
        self.point = QComboBox()
        for step in self.session['steps']:
            self.point.addItem(step['label'] + ' · ' + step['status'], step['run_id'])
        self.point.setAccessibleName('Survey point or scan')
        layout.addWidget(self.point)
        self.surface = QComboBox()
        self.surface.setAccessibleName('Geographic map or floor plan')
        layout.addWidget(self.surface)
        self.metric_panel = QLabel('Floor-plan measured metric')
        layout.addWidget(self.metric_panel)
        self.metric_selector = QComboBox()
        self.metric_selector.setAccessibleName('Floor-plan measured metric')
        self.metric_selector.addItem('Placement positions', None)
        metric_model = {'run_metrics': {step['run_id']: clean_metrics(step.get('metrics')) for step in self.session['steps']}}
        for key in available_metrics(metric_model):
            title, unit = METRICS[key]
            self.metric_selector.addItem(f'{title} ({unit})', key)
        layout.addWidget(self.metric_selector)
        self.cell_row = QWidget()
        cell_layout = QHBoxLayout(self.cell_row);cell_layout.setContentsMargins(0,0,0,0)
        cell_layout.addWidget(QLabel('Reported cell group'))
        self.cell_selector = QComboBox()
        self.cell_selector.setAccessibleName('Filter floor-plan live cellular measurements by reported cell group')
        self.cell_selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cell_selector.setMinimumContentsLength(12)
        self.cell_selector.addItem('Automatic · single group only',None)
        cell_layout.addWidget(self.cell_selector,1)
        layout.addWidget(self.cell_row);self.cell_row.hide()
        self.source_caption = QLabel('Metric source')
        layout.addWidget(self.source_caption)
        self.source_filter = QComboBox()
        self.source_filter.setAccessibleName('Filter floor-plan measurements by recorded source')
        self.source_filter.addItem('All recorded sources', None)
        layout.addWidget(self.source_filter)
        self.metric_legend = QLabel()
        self.metric_legend.setWordWrap(True)
        self.metric_legend.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.metric_legend)
        self.measurement_detail = QLabel()
        self.measurement_detail.setWordWrap(True)
        self.measurement_detail.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.measurement_detail)
        actions = FlowLayout()
        add = QPushButton('Import floor plan…')
        add.clicked.connect(self.add_floor)
        actions.addWidget(add)
        self.remove_button = QPushButton('Remove floor…')
        self.remove_button.clicked.connect(self.remove_selected_floor)
        actions.addWidget(self.remove_button)
        self.pick_button = QPushButton('Pick on offline map…')
        self.pick_button.clicked.connect(self.pick_geographic)
        actions.addWidget(self.pick_button)
        self.fit_button = QPushButton('Fit floor')
        self.fit_button.clicked.connect(lambda: self.canvas.fit_floor())
        actions.addWidget(self.fit_button)
        self.calibrate_button = QPushButton('Calibrate floor scale…')
        self.calibrate_button.clicked.connect(self.begin_calibration)
        actions.addWidget(self.calibrate_button)
        layout.addLayout(actions)
        self.coordinate_form = QFormLayout()
        self.latitude, self.longitude = QLineEdit(), QLineEdit()
        self.latitude.setAccessibleName('Manual latitude')
        self.longitude.setAccessibleName('Manual longitude')
        self.coordinate_form.addRow('Latitude (degrees)', self.latitude)
        self.coordinate_form.addRow('Longitude (degrees)', self.longitude)
        layout.addLayout(self.coordinate_form)
        self.canvas = FloorCanvas()
        self.canvas.picked.connect(self.floor_picked)
        self.canvas.marker_selected.connect(self.select_floor_marker)
        layout.addWidget(self.canvas, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        save = QPushButton('Save placement')
        save.clicked.connect(self.save)
        buttons.addWidget(save)
        clear = QPushButton('Clear saved placement…')
        clear.clicked.connect(self.clear)
        buttons.addWidget(clear)
        close = QPushButton('Close')
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self.surface.currentIndexChanged.connect(self.change_surface)
        self.point.currentIndexChanged.connect(self.change_point)
        self.metric_selector.currentIndexChanged.connect(lambda _index: self.change_metric())
        self.cell_selector.currentIndexChanged.connect(lambda _index: self.change_cell())
        self.source_filter.currentIndexChanged.connect(lambda _index: self.render_floor())
        self.refresh()
        self.change_point()

    def refresh(self, selected=None):
        self.data = load_spatial(self.config, self.path)
        from .map_sources import load_survey_map_data
        model = load_survey_map_data(self.config, self.path)
        self.base_map_model = model
        self.map_model = model
        self.update_metric_steps()
        selected_metric = self.metric_selector.currentData()
        self.metric_selector.blockSignals(True)
        self.metric_selector.clear()
        self.metric_selector.addItem('Placement positions', None)
        available = dict(model,run_metrics={s['run_id']:s['metrics'] for s in self.metric_steps})
        for key in available_metrics(available):
            title, unit = METRICS[key]
            self.metric_selector.addItem(f'{title} ({unit})', key)
        self.metric_selector.setCurrentIndex(max(0, self.metric_selector.findData(selected_metric)))
        self.metric_selector.blockSignals(False)
        self.refresh_cell_options()
        self.map_model=select_cell_group(self.base_map_model,self.cell_selector.currentData())
        self.update_metric_steps()
        gps_runs = {row['run_id'] for row in model['rows'] if row['id'] in model['representatives'] and row.get('renderable')}
        unplaced = unplaced_measurements(self.session['steps'], self.data, gps_runs)
        self.placement_summary.setText(f'Unplaced measurements: {len(unplaced)} · Select a scan below to place it now or later.')
        selected = selected or self.surface.currentData()
        self.surface.blockSignals(True)
        self.surface.clear()
        self.surface.addItem('Geographic map · operator coordinates', 'geographic')
        for key, floor in self.data['floors'].items():
            self.surface.addItem(floor['label'], key)
        index = self.surface.findData(selected)
        self.surface.setCurrentIndex(max(0, index))
        self.surface.blockSignals(False)
        self.change_surface()

    def change_point(self):
        placement = self.data['placements'].get(self.point.currentData())
        if placement:
            self.surface.setCurrentIndex(self.surface.findData(placement.get('floor_id', 'geographic')))
        self.change_surface()

    def select_floor_marker(self, run_id):
        index = self.point.findData(run_id)
        if index >= 0:
            self.point.setCurrentIndex(index)
            self.render_floor()

    def change_surface(self):
        self.pending = None
        self.calibration_points = None
        geographic = self.surface.currentData() == 'geographic'
        for row in range(self.coordinate_form.rowCount()):
            self.coordinate_form.setRowVisible(row, geographic)
        self.canvas.setVisible(not geographic)
        self.metric_panel.setVisible(not geographic)
        self.metric_selector.setVisible(not geographic)
        self.cell_row.setVisible(not geographic and self.cell_selector.count()>1)
        self.source_caption.setVisible(not geographic)
        self.source_filter.setVisible(not geographic)
        self.metric_legend.setVisible(not geographic)
        self.measurement_detail.setVisible(not geographic)
        self.pick_button.setEnabled(geographic)
        self.fit_button.setEnabled(not geographic)
        self.calibrate_button.setEnabled(not geographic)
        self.remove_button.setEnabled(not geographic)
        self.latitude.clear()
        self.longitude.clear()
        placement = self.data['placements'].get(self.point.currentData())
        if placement and placement.get('floor_id', 'geographic') == self.surface.currentData():
            self.pending = placement
            if geographic:
                self.latitude.setText(str(placement['latitude']))
                self.longitude.setText(str(placement['longitude']))
        if geographic:
            self.status.setText('Enter coordinates or pick on the offline map, then Save placement.')
        else:
            self.refresh_floor_sources()
            self.render_floor(fit=True)

    def change_metric(self):
        self.refresh_cell_options()
        self.map_model=select_cell_group(self.base_map_model,self.cell_selector.currentData())
        self.update_metric_steps()
        if self.surface.currentData() != 'geographic':
            self.refresh_floor_sources()
            self.render_floor()

    def update_metric_steps(self):
        self.metric_steps=[]
        for step in self.session['steps']:
            view_step=dict(step)
            base=clean_metrics(step.get('metrics'))
            if self.cell_selector.currentData() is not None or self.map_model.get('auto_live_suppressed'):
                base={key:value for key,value in base.items() if not key.startswith('live_phone_')}
            view_step['metrics']={**base,**clean_metrics(self.map_model.get('run_metrics',{}).get(step['run_id']))}
            self.metric_steps.append(view_step)

    def refresh_cell_options(self):
        selected=self.cell_selector.currentData()
        choices=cell_group_options(self.base_map_model,self.metric_selector.currentData())
        self.cell_selector.blockSignals(True);self.cell_selector.clear()
        self.cell_selector.addItem('Automatic · single group only',None)
        for key,label in choices:self.cell_selector.addItem(label,key)
        self.cell_selector.setCurrentIndex(max(0,self.cell_selector.findData(selected)))
        self.cell_selector.blockSignals(False)
        self.cell_row.setVisible(self.surface.currentData() != 'geographic' and bool(choices))

    def change_cell(self):
        self.map_model=select_cell_group(self.base_map_model,self.cell_selector.currentData())
        self.update_metric_steps()
        if self.surface.currentData() != 'geographic':
            self.refresh_floor_sources()
            self.render_floor()

    def refresh_floor_sources(self):
        floor = self.surface.currentData()
        key = self.metric_selector.currentData()
        run_metrics = {step['run_id']: clean_metrics(step.get('metrics')) for step in self.metric_steps
                       if (position := self.data['placements'].get(step['run_id'])) and
                       position.get('kind') == 'floor' and position.get('floor_id') == floor}
        model = {'run_metrics': run_metrics, 'run_context': self.map_model.get('run_context', {})}
        selected = self.source_filter.currentData()
        self.source_filter.blockSignals(True)
        self.source_filter.clear()
        self.source_filter.addItem('All recorded sources', None)
        for source in source_options(model, key) if key else []:
            self.source_filter.addItem('Source unrecorded' if source == UNATTRIBUTED else source_label(source), source)
        index = self.source_filter.findData(selected)
        self.source_filter.setCurrentIndex(max(0, index))
        self.source_filter.blockSignals(False)

    def render_floor(self, fit=False):
        if self.surface.currentData() == 'geographic':
            return
        try:
            floor = self.surface.currentData()
            image = read_floor(self.config, self.path, floor)
            key = self.metric_selector.currentData()
            source = self.source_filter.currentData()
            markers, metric_scale = floor_measurements(self.metric_steps, self.data['placements'], floor, key,
                                                       source_filter=source, run_context=self.map_model.get('run_context', {}))
            self.canvas.set_floor(image, markers, metric_mode=bool(key))
            unsaved = self.pending and self.pending.get('kind') == 'floor' and self.pending.get('floor_id') == floor and 'placed_utc' not in self.pending
            if unsaved:
                self.canvas.show_preview(self.pending['x'], self.pending['y'])
            if fit:
                self.canvas.fit_floor()
            if key and metric_scale:
                low, high = metric_scale['minimum'], metric_scale['maximum']
                spread = f'single value {low:g}' if low == high else f'{low:g} to {high:g}'
                colors = 'Teal = the single observed value.' if low == high else 'Blue = lower observed value; amber = higher.'
                self.metric_legend.setText(f"{metric_scale['label']} · {spread} {metric_scale['unit']} on this floor across {metric_scale['count']} placed scans. {colors} Colors are relative, not a quality verdict. Purple outlines = operator placement; gray fill = value unavailable. Saved run metrics are not exact per-position samples.")
            elif key and key.startswith('live_phone_') and self.map_model.get('auto_live_suppressed'):
                action = 'Select a reported cell group to view one run.' if self.cell_selector.count()>1 else 'No complete cell groups are selectable; review the Cellular report.'
                self.metric_legend.setText(action+' Automatic comparison is unavailable because receiver identity is not verified across runs.')
            elif key and key.startswith('live_phone_') and self.cell_selector.count()>1:
                self.metric_legend.setText('Select a reported cell group to view one run. Each value summarizes fresh samples from that run, not an individual position.')
            elif key:
                self.metric_legend.setText('No saved values for this metric on this floor. Gray points remain operator placements; no coverage is estimated.')
            else:
                self.metric_legend.setText('Purple markers are operator floor-plan placements, not GPS evidence. Choose a measured metric to color placed scans.')
            selected_run = self.point.currentData()
            selected = next((marker for marker in markers if marker['run_id'] == selected_run), None)
            if selected:
                metric = selected['metric']
                kind = 'derived live-session value' if key and key.startswith('live_phone_') else 'saved run metric'
                value = f"{metric['label']} {metric['value']:g} {metric['unit']} · {kind}" if metric else ('Selected metric unavailable' if key else 'No metric selected')
                placed = selected.get('placed_utc') or 'time unavailable'
                context = self.map_model.get('run_context', {}).get(selected['run_id'], {}).get(key, {}) if key else {}
                timing = ' ' + provenance_label(context) + '.' if key else ''
                self.measurement_detail.setText(f"{selected['scan_label']} · scan {selected['number']} · Run {selected['run_id']} · operator floor-plan placement · Operator placed {placed}. {value}.{timing} Original diagnostic evidence is unchanged.")
            else:
                self.measurement_detail.setText('The selected scan is not shown for this floor and source. Choose another scan, source or floor.')
            scale = self.data['floors'][floor].get('calibration', {}).get('meters_per_pixel')
            self.status.setText('Click to choose a position; drag to pan; scroll to zoom. Save confirms placement. ' +
                                (f'Scale: {scale:.6g} m / image pixel.' if scale else 'Scale is not calibrated.'))
            if unsaved:
                self.status.setText(f"Unsaved placement: {self.pending['x'] * 100:.1f}% across, {self.pending['y'] * 100:.1f}% down. Choose Save placement to confirm.")
        except (OSError, ValueError) as exc:
            self.canvas.scene().clear()
            self.canvas.dimensions = None
            self.status.setText(str(exc))

    def floor_picked(self, x, y):
        if self.calibration_points is not None:
            self.calibration_points.append([x, y])
            if len(self.calibration_points) == 1:
                self.status.setText('Click the second end of the known distance.')
                return
            first, second = self.calibration_points
            self.calibration_points = None
            distance, ok = QInputDialog.getDouble(self, 'Floor scale', 'Actual separation (meters)', 10, .001, 100000, 3)
            if ok:
                try:
                    calibrate_floor(self.config, self.path, self.surface.currentData(), first, second, distance)
                    self.refresh()
                except (OSError, ValueError) as exc:
                    self.status.setText(str(exc))
            return
        self.pending = dict(kind='floor', floor_id=self.surface.currentData(), x=x, y=y)
        self.canvas.show_preview(x, y)
        self.status.setText(f'Unsaved placement: {x * 100:.1f}% across, {y * 100:.1f}% down. Choose Save placement to confirm.')

    def save(self):
        try:
            if self.surface.currentData() == 'geographic':
                value = dict(kind='geographic', latitude=float(self.latitude.text()), longitude=float(self.longitude.text()))
            else:
                value = self.pending
            if value is None:
                raise ValueError('Choose a floor-plan position first.')
            save_placement(self.config, self.path, self.point.currentData(), value)
            self.refresh()
            self.status.setText('Placement saved. Original GPS and diagnostic evidence are unchanged.')
        except (OSError, ValueError) as exc:
            self.status.setText(str(exc))

    def clear(self):
        if QMessageBox.question(self, 'Clear manual placement', 'Remove the selected point’s manual placement? Captured GPS and scan evidence will remain.') != QMessageBox.StandardButton.Yes:
            return
        try:
            clear_placement(self.config, self.path, self.point.currentData())
            self.refresh()
            self.status.setText('Manual placement cleared.')
        except (OSError, ValueError) as exc:
            self.status.setText(str(exc))

    def add_floor(self):
        source, _ = QFileDialog.getOpenFileName(self, 'Import floor plan (up to 2048 × 2048 pixels)', '', 'Images (*.png *.jpg *.jpeg)')
        if not source:
            return
        label, ok = QInputDialog.getText(self, 'Floor label', 'Building / floor name:')
        if ok:
            try:
                floor = import_floor(self.config, self.path, source, label)
                self.refresh(floor)
            except (OSError, ValueError) as exc:
                self.status.setText(str(exc))

    def begin_calibration(self):
        self.calibration_points = []
        self.status.setText('Click the first end of a known distance, then the second. Use a top-down, undistorted floor plan.')

    def remove_selected_floor(self):
        if QMessageBox.question(self, 'Remove floor plan', 'Remove this floor from the survey? First clear or move any points assigned to it.') != QMessageBox.StandardButton.Yes:
            return
        try:
            remove_floor(self.config, self.path, self.surface.currentData())
            self.refresh()
        except (OSError, ValueError) as exc:
            self.status.setText(str(exc))

    def pick_geographic(self):
        from .map_ui import MapWindow
        from .map_sources import load_survey_map_data
        try:
            model = load_survey_map_data(self.config, self.path)
            def picked(longitude, latitude):
                self.latitude.setText(f'{latitude:.8f}')
                self.longitude.setText(f'{longitude:.8f}')
                self.status.setText('Map position selected. Choose Save placement to confirm.')
                if self.pick_map:
                    self.pick_map.close()
                    self.pick_map = None
            self.pick_map = MapWindow(self, model, lambda _: None, config=self.config, pick_callback=picked)
            self.pick_map.setModal(True)
            self.pick_map.show()
        except (OSError, ValueError) as exc:
            self.status.setText(str(exc))
