"""Explicit, local terrain assessment for a selected reference candidate."""
import base64
from functools import partial
from PySide6.QtCore import Slot,Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QVBoxLayout,QFormLayout,QHBoxLayout,QPushButton,QLabel,QLineEdit,QComboBox,QDoubleSpinBox,QCheckBox,QFileDialog,QScrollArea
from .background_dialog import JobDialog
from .core import utcnow_iso


def assessment_job(path,metadata,context,receiver_height,site_height,frequency,factor,cancelled,progress):
    from .terrain_raster import sample_path
    from .terrain_profile import assess_profile
    location=context['observation']['location'];candidate=context['candidate']
    terrain=sample_path(path,[location['longitude_deg'],location['latitude_deg']],[candidate['lon'],candidate['lat']],metadata,cancelled)
    profile=assess_profile(terrain['distances_m'],terrain['elevations_m'],receiver_height,site_height,frequency,factor)
    return dict(schema_version=1,prepared_utc=utcnow_iso(),endpoint_context=context,terrain=terrain,profile=profile)


class PathAssessmentDialog(JobDialog):
    def __init__(self,parent,config,selected_endpoint_context):
        super().__init__(parent);self.context=selected_endpoint_context;self.assessment=None
        self.setWindowTitle('Assess selected terrain path');self.resize(1050,800)
        layout=QVBoxLayout(self)
        note=QLabel('Conditional on the selected cell reference. Enter actual antenna heights above ground; phone altitude and mast height are not substitutes. No network download is performed.')
        note.setWordWrap(True);layout.addWidget(note)
        form=QFormLayout();layout.addLayout(form)
        self.file=QLineEdit();self.choose=QPushButton('Select regional GeoTIFF…');self.choose.clicked.connect(self.select_file)
        line=QHBoxLayout();line.addWidget(self.file);line.addWidget(self.choose);form.addRow('Elevation file',line)
        self.source=QLineEdit();self.source.setPlaceholderText('e.g. USGS 3DEP product and date');form.addRow('DEM source',self.source)
        self.datum=QLineEdit();self.datum.setPlaceholderText('Confirm from product documentation, e.g. NAVD88');form.addRow('Vertical datum',self.datum)
        self.units=QComboBox();self.units.addItems(['Select units','m','ft','us-ft']);form.addRow('Elevation units',self.units)
        self.receiver=QDoubleSpinBox();self.site=QDoubleSpinBox()
        for widget in (self.receiver,self.site):widget.setRange(-1,10000);widget.setValue(-1);widget.setSpecialValueText('Required');widget.setSuffix(' m')
        form.addRow('Receiver antenna AGL',self.receiver);form.addRow('Reference antenna AGL',self.site)
        self.frequency=QDoubleSpinBox();self.frequency.setRange(0,1000000);self.frequency.setDecimals(3);self.frequency.setSpecialValueText('Unknown — geometric only');form.addRow('Frequency MHz',self.frequency)
        self.factor=QComboBox();self.factor.addItem('Geometric Earth (k = 1)',1.);self.factor.addItem('Assumed refraction (k = 4/3)',4/3);form.addRow('Earth model',self.factor)
        self.confirm=QCheckBox('I confirmed the DEM units/datum and antenna heights from the relevant source.');layout.addWidget(self.confirm)
        self.calculate=QPushButton('Calculate terrain profile');self.calculate.clicked.connect(self.run_assessment);layout.addWidget(self.calculate)
        self.preview=QLabel('Select a local regional DEM and supply the missing inputs.');self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.preview);layout.addWidget(scroll,1)
        self.status=QLabel('No assessment calculated.');self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
        self.keep=QPushButton('Keep assessment in context');self.keep.clicked.connect(self.accept_assessment);self.keep.setEnabled(False);layout.addWidget(self.keep)
        self.controls=[self.file,self.choose,self.source,self.datum,self.units,self.receiver,self.site,self.frequency,self.factor,self.confirm,self.calculate,self.keep]
        for field in (self.file,self.source,self.datum):field.textChanged.connect(self.invalidate)
        for field in (self.receiver,self.site,self.frequency):field.valueChanged.connect(self.invalidate)
        for field in (self.units,self.factor):field.currentIndexChanged.connect(self.invalidate)
        self.confirm.toggled.connect(self.invalidate)
    @Slot()
    def invalidate(self):
        self.assessment=None;self.keep.setEnabled(False)
        self.preview.clear();self.status.setText('Inputs changed. Calculate a new profile before keeping it.')
    @Slot()
    def select_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Select local regional DEM','','GeoTIFF (*.tif *.tiff)')
        if path:self.file.setText(path)
    @Slot()
    def run_assessment(self):
        if not self.confirm.isChecked() or min(self.receiver.value(),self.site.value())<0:
            self.status.setText('Confirm elevation metadata and supply both antenna heights above ground.');return
        self.assessment=None;self.keep.setEnabled(False)
        metadata=dict(source=self.source.text(),vertical_datum=self.datum.text(),units=self.units.currentText())
        self.start_job(partial(assessment_job,self.file.text(),metadata,self.context,self.receiver.value(),self.site.value(),self.frequency.value() or None,self.factor.currentData()))
    @Slot(object)
    def job_ready(self,value):
        if self.closing:return
        from .path_assessment_report import profile_png
        png=profile_png(value['profile'])
        value['profile_png']=base64.b64encode(png).decode() if png else None
        if png:
            pixmap=QPixmap();pixmap.loadFromData(png);self.preview.setPixmap(pixmap.scaled(980,390,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        else:self.preview.setText('Incomplete terrain coverage; no clearance conclusion is available.')
        self.assessment=value
        p=value['profile'];self.status.setText(f"{p['status']} · Fresnel: {p['fresnel_status']} · Minimum sampled clearance: {p['minimum_clearance_m']} m. Buildings and vegetation are not included.")
    def set_busy(self,busy):
        super().set_busy(busy);self.keep.setEnabled(not busy and self.assessment is not None)
    @Slot()
    def accept_assessment(self):
        if self.assessment is not None and self.worker is None:self.accept()
