"""Prepare photographic survey context without networking during report viewing."""
import json
import threading
from pathlib import Path
from PySide6.QtCore import QThread, Signal, Slot, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QDoubleSpinBox, QFileDialog, QFormLayout, QScrollArea)
from .survey_imagery import (survey_points, load_imagery, render_image, decode_image,
                             save_imagery, validate_metadata, MAX_BYTES)


class ImageryWorker(QThread):
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, bounds, parent=None):
        super().__init__(parent)
        self.bounds = bounds
        self.cancelled = threading.Event()

    def run(self):
        from .imagery_provider import fetch_naip
        try:
            result = fetch_naip(self.bounds, self.cancelled.is_set)
            if not self.cancelled.is_set():
                self.ready.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class SurveyImageryDialog(QDialog):
    def __init__(self, parent, config, path):
        super().__init__(parent)
        self.config, self.path = config, path
        self.points = survey_points(config, path)
        self.worker = None
        self.closing = False
        self.raw = self.meta = None
        self.setWindowTitle('Prepare survey report map')
        self.resize(960, 760)
        layout = QVBoxLayout(self)
        intro = QLabel('Prepare a saved aerial view with numbered survey points. Download sends only the area below to USGS. '
                       'Viewing and exporting the saved report works offline. Image acquisition date may be unknown.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.area = QLabel(f'{len(self.points)} tests have qualified GPS. ' +
                           ('Area includes these positions.' if self.points else
                            'No qualified GPS: enter an area explicitly. It will be labelled manually selected.'))
        self.area.setWordWrap(True)
        layout.addWidget(self.area)
        form = QFormLayout()
        self.bounds = []
        defaults = self.default_bounds()
        for index, name in enumerate(('West longitude', 'South latitude', 'East longitude', 'North latitude')):
            field = QDoubleSpinBox()
            field.setDecimals(6)
            field.setRange(-180 if index%2 == 0 else -85, 180 if index%2 == 0 else 85)
            field.setValue(defaults[index])
            self.bounds.append(field)
            form.addRow(name, field)
        layout.addLayout(form)
        actions = QHBoxLayout()
        self.fetch = QPushButton('Download USGS aerial preview')
        self.fetch.clicked.connect(self.download)
        self.import_button = QPushButton('Import image + georeferencing JSON…')
        self.import_button.clicked.connect(self.import_image)
        self.cached = QPushButton('Regenerate from saved image')
        self.cached.clicked.connect(self.regenerate)
        for control in (self.fetch, self.import_button, self.cached):
            actions.addWidget(control)
        layout.addLayout(actions)
        self.preview = QLabel('No image prepared. Reports remain usable without photographic context.')
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.preview)
        layout.addWidget(scroll, 1)
        self.status = QLabel('Preview an image, then save it to this survey.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        bottom = QHBoxLayout()
        self.save = QPushButton('Save map to survey')
        self.save.setEnabled(False)
        self.save.clicked.connect(self.save_map)
        self.cancel = QPushButton('Close')
        self.cancel.clicked.connect(self.reject)
        bottom.addWidget(self.save)
        bottom.addWidget(self.cancel)
        layout.addLayout(bottom)

    def default_bounds(self):
        if not self.points:
            return [0, 0, 0, 0]
        xs, ys = [p['lon'] for p in self.points], [p['lat'] for p in self.points]
        dx, dy = max(.002, (max(xs)-min(xs))*.15), max(.002, (max(ys)-min(ys))*.15)
        return [max(-180,min(xs)-dx),max(-85,min(ys)-dy),min(180,max(xs)+dx),min(85,max(ys)+dy)]

    @Slot()
    def download(self):
        bounds = [v.value() for v in self.bounds]
        try:
            validate_metadata(dict(schema_version=1, crs='EPSG:4326', bounds=bounds,
                                   source='USGS NAIP', attribution='USGS / USDA', imagery_date=None))
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self.worker = ImageryWorker(bounds, self)
        self.worker.ready.connect(self.received)
        self.worker.failed.connect(self.failure)
        self.worker.finished.connect(self.worker_finished)
        self.set_busy(True)
        self.status.setText('Downloading aerial imagery from USGS… Close cancels without changing the saved map.')
        self.worker.start()

    def set_busy(self, busy):
        for control in (self.fetch, self.import_button, self.cached, *self.bounds):
            control.setEnabled(not busy)
        self.save.setEnabled(not busy and self.raw is not None)

    @Slot(object)
    def received(self, result):
        if self.closing:
            return
        try:
            self.set_preview(*result)
        except (ValueError, OSError) as exc:
            self.failure(str(exc))

    @Slot(str)
    def failure(self, message):
        self.status.setText(message)

    @Slot()
    def worker_finished(self):
        worker = self.worker
        self.worker = None
        worker.deleteLater()
        self.set_busy(False)
        if self.closing:
            super().reject()

    def set_preview(self, raw, meta):
        meta = validate_metadata(meta)
        overlay = render_image(raw, meta, self.points)
        pixmap = QPixmap.fromImage(decode_image(overlay))
        self.preview.setPixmap(pixmap.scaled(880, 460, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
        self.raw, self.meta = raw, meta
        self.save.setEnabled(self.worker is None)
        self.status.setText(f"{meta['source']} • {meta['imagery_type']} • Acquisition: {meta['imagery_date'] or 'Unknown'}\n"
                            f"{meta['attribution']}\n{len(self.points)} mapped tests. Bounds: {meta['bounds']} ({meta['crs']}). "
                            'Review the coverage before saving.')

    @Slot()
    def import_image(self):
        name, _ = QFileDialog.getOpenFileName(self, 'Import north-up georeferenced image', '', 'Images (*.png *.jpg *.jpeg)')
        if not name:
            return
        sidecar = Path(name).with_suffix('.json')
        if not sidecar.is_file():
            chosen, _ = QFileDialog.getOpenFileName(self, 'Select georeferencing sidecar', str(Path(name).parent), 'JSON (*.json)')
            if not chosen:
                return
            sidecar = Path(chosen)
        try:
            if Path(name).stat().st_size > MAX_BYTES or sidecar.stat().st_size > 65536:
                raise ValueError('Image or metadata exceeds its size limit.')
            self.set_preview(Path(name).read_bytes(), json.loads(sidecar.read_text(encoding='utf-8-sig')))
        except (OSError, ValueError) as exc:
            self.failure(str(exc))

    @Slot()
    def regenerate(self):
        try:
            cached = load_imagery(self.config, self.path)
            if not cached:
                raise ValueError('This survey has no saved image yet.')
            self.set_preview((cached['asset_dir']/'source.image').read_bytes(), cached)
        except (OSError, ValueError) as exc:
            self.failure(str(exc))

    @Slot()
    def save_map(self):
        try:
            save_imagery(self.config, self.path, self.raw, self.meta, self.points)
            self.accept()
        except (OSError, ValueError) as exc:
            self.failure(str(exc))

    @Slot()
    def reject(self):
        if self.worker is not None:
            self.closing = True
            self.worker.cancelled.set()
            self.cancel.setEnabled(False)
            self.status.setText('Cancelling download; waiting for the current network request to finish…')
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)
