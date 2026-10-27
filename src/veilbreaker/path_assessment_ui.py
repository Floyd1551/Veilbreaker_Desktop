"""Explicit, local terrain assessment for a selected reference candidate."""
import base64
from functools import partial
from PySide6.QtCore import Slot,Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QVBoxLayout,QFormLayout,QHBoxLayout,QPushButton,QLabel,QLineEdit,QComboBox,QDoubleSpinBox,QCheckBox,QFileDialog,QScrollArea
from .background_dialog import JobDialog
from .core import utcnow_iso


def assessment_job(path,metadata,context,receiver_height,site_height,frequency,factor,cancelled,progress,pack_context=None):
    from .terrain_raster import sample_path
    from .terrain_profile import assess_profile
    location=context['observation']['location'];candidate=context['candidate']
    terrain=sample_path(path,[location['longitude_deg'],location['latitude_deg']],[candidate['lon'],candidate['lat']],metadata,cancelled)
    if pack_context and terrain['dem']['sha256'] != pack_context['sha256']:
        raise ValueError('Installed terrain pack checksum changed. Reverify or reinstall the pack.')
    profile=assess_profile(terrain['distances_m'],terrain['elevations_m'],receiver_height,site_height,frequency,factor)
    result=dict(schema_version=1,prepared_utc=utcnow_iso(),endpoint_context=context,terrain=terrain,profile=profile)
    if pack_context:
        result['regional_pack']={key:pack_context[key] for key in ('pack_id','name','source','license','source_date','sha256','bounds_wgs84','coverage_note')}
    return result


class PathAssessmentDialog(JobDialog):
    def __init__(self,parent,config,selected_endpoint_context):
        super().__init__(parent);self.context=selected_endpoint_context;self.assessment=None
        self.store_root=config.root/'regional-packs';self.selected_pack=None;self.expected_pack_sha256=None
        self.setWindowTitle('Assess selected terrain path');self.resize(1050,800)
        layout=QVBoxLayout(self)
        note=QLabel('Conditional on the selected cell reference. Enter actual antenna heights above ground; phone altitude and mast height are not substitutes. No network download is performed.')
        note.setWordWrap(True);layout.addWidget(note)
        form=QFormLayout();layout.addLayout(form)
        self.file=QLineEdit();self.choose=QPushButton('Select regional GeoTIFF…');self.choose.clicked.connect(self.select_file)
        line=QHBoxLayout();line.addWidget(self.file);line.addWidget(self.choose);form.addRow('Elevation file',line)
        self.installed=QComboBox();self.installed.setAccessibleName('Installed regional terrain pack')
        from .regional_packs import RegionalPackStore
        for row in RegionalPackStore(self.store_root).list_packs():
            if row.get('kind')=='terrain' and row['status']=='available':
                self.installed.addItem(f"{row['name']} · {row['source_date']} · {row['bounds_wgs84']}",row['pack_id'])
        self.use_pack=QPushButton('Use installed terrain');self.use_pack.clicked.connect(self.use_installed_terrain)
        self.use_pack.setEnabled(self.installed.count()>0)
        pack_line=QHBoxLayout();pack_line.addWidget(self.installed,1);pack_line.addWidget(self.use_pack)
        form.addRow('Installed pack',pack_line)
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
        self.controls=[self.file,self.choose,self.installed,self.use_pack,self.source,self.datum,self.units,self.receiver,self.site,self.frequency,self.factor,self.confirm,self.calculate,self.keep]
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
        if path:
            self.selected_pack=None;self.expected_pack_sha256=None
            self.file.setText(path)
    @Slot()
    def use_installed_terrain(self):
        from .regional_packs import RegionalPackStore
        pack_id=self.installed.currentData()
        if not pack_id:return False
        store=RegionalPackStore(self.store_root)
        try:
            row=store._manifest(pack_id)
            path=store.data_path(pack_id)
        except (OSError,ValueError) as exc:
            self.status.setText(str(exc));return False
        self.file.setText(str(path))
        self.source.setText(f"{row['source']} · {row['source_date']}")
        self.datum.setText(row['vertical_datum'])
        self.units.setCurrentText(row['units'])
        self.selected_pack=row;self.expected_pack_sha256=row['sha256']
        self.status.setText(f"Selected {row['name']}. Raster bounds may contain no-data gaps. Confirm antenna heights before calculation.")
        return True
    @Slot()
    def run_assessment(self):
        if not self.confirm.isChecked() or min(self.receiver.value(),self.site.value())<0:
            self.status.setText('Confirm elevation metadata and supply both antenna heights above ground.');return
        self.assessment=None;self.keep.setEnabled(False)
        metadata=dict(source=self.source.text(),vertical_datum=self.datum.text(),units=self.units.currentText())
        pack=self.selected_pack
        if pack:
            if self.file.text()!=str(self.store_root/pack['pack_id']/pack['data_file']):
                pack=None
            elif metadata!=dict(source=f"{pack['source']} · {pack['source_date']}",vertical_datum=pack['vertical_datum'],units=pack['units']):
                self.status.setText('Installed terrain metadata changed. Reselect the pack to restore its verified provenance, or choose a separate local file.')
                return
        self.start_job(partial(assessment_job,self.file.text(),metadata,self.context,self.receiver.value(),self.site.value(),self.frequency.value() or None,self.factor.currentData(),pack_context=pack))
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
