"""Manual geographic and indoor placement, always separate from captured GPS."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QPen, QColor
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QFormLayout, QGraphicsView, QGraphicsScene, QFileDialog,
    QInputDialog, QMessageBox)
from .survey import read_session
from .survey_spatial import (load_spatial, import_floor, read_floor, save_placement,
                             clear_placement, calibrate_floor, remove_floor, unplaced_measurements)
from .widgets import FlowLayout


class FloorCanvas(QGraphicsView):
    picked = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.dimensions = None
        self.press_position = None
        self.preview = None
        self.setMinimumHeight(280)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setAccessibleName('Floor plan. Click to place a point; drag to pan; scroll to zoom.')

    def set_floor(self, image, markers):
        self.scene().clear()
        self.preview = None
        self.dimensions = (image.width(), image.height())
        self.scene().addPixmap(QPixmap.fromImage(image))
        radius = max(image.width(), image.height()) / 100
        for x, y, label in markers:
            px, py = x * image.width(), y * image.height()
            self.scene().addEllipse(px - radius, py - radius, radius * 2, radius * 2,
                                   QPen(QColor('#231438')), QColor('#ba95f5'))
            text = self.scene().addSimpleText(str(label))
            text.setBrush(QColor('#111111'))
            text.setPos(px + radius, py)
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
        self.refresh()
        self.change_point()

    def refresh(self, selected=None):
        self.data = load_spatial(self.config, self.path)
        from .map_sources import load_survey_map_data
        model = load_survey_map_data(self.config, self.path)
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

    def change_surface(self):
        self.pending = None
        self.calibration_points = None
        geographic = self.surface.currentData() == 'geographic'
        for row in range(self.coordinate_form.rowCount()):
            self.coordinate_form.setRowVisible(row, geographic)
        self.canvas.setVisible(not geographic)
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
            try:
                floor = self.surface.currentData()
                image = read_floor(self.config, self.path, floor)
                markers = [(p['x'], p['y'], i + 1) for i, step in enumerate(self.session['steps'])
                           if (p := self.data['placements'].get(step['run_id'])) and p.get('floor_id') == floor]
                self.canvas.set_floor(image, markers)
                self.canvas.fit_floor()
                scale = self.data['floors'][floor].get('calibration', {}).get('meters_per_pixel')
                self.status.setText('Click to choose a position; drag to pan; scroll to zoom. Save confirms placement. ' +
                                    (f'Scale: {scale:.6g} m / image pixel.' if scale else 'Scale is not calibrated.'))
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
