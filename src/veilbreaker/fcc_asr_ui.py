"""Prepare a local FCC physical-structure reference pack without a network connection."""
from functools import partial

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QVBoxLayout)

from .background_dialog import JobDialog
from .fcc_asr import FCC_URL, install_fcc_asr
from .regional_packs import RegionalPackStore


def _import_job(root, source, bounds, date, name, cancelled, progress):
    return install_fcc_asr(RegionalPackStore(root), source, bounds, date, name, cancelled, progress)


class FccAsrImportDialog(JobDialog):
    def __init__(self, parent, store_root):
        super().__init__(parent)
        self.store_root = store_root
        self.setWindowTitle('Import FCC physical structures')
        self.resize(650, 430)
        layout = QVBoxLayout(self)
        info = QLabel('Select the FCC complete registration ZIP (r_tower.zip), then set a regional extent. '
                      'Only registrations marked constructed are imported. FCC ASR records are incomplete, '
                      'can be out of date, and do not identify a carrier, serving cell, or antenna location.')
        info.setWordWrap(True)
        layout.addWidget(info)
        link = QLabel('<a href="' + FCC_URL + '">FCC complete registration archive</a>')
        link.setOpenExternalLinks(True)
        layout.addWidget(link)
        form = QFormLayout()
        self.path = QLineEdit()
        self.path.setPlaceholderText('Local r_tower.zip')
        browse = QPushButton('Browse…')
        browse.clicked.connect(self.browse)
        source_row = QHBoxLayout()
        source_row.addWidget(self.path)
        source_row.addWidget(browse)
        form.addRow('FCC archive', source_row)
        self.name = QLineEdit('Huntsville area · FCC ASR')
        self.bounds = QLineEdit('-87.2, 34.3, -86.2, 35.2')
        self.date = QLineEdit()
        self.date.setPlaceholderText('YYYY-MM-DD · archive publication date')
        form.addRow('Pack name', self.name)
        form.addRow('West, south, east, north', self.bounds)
        form.addRow('Source date', self.date)
        layout.addLayout(form)
        note = QLabel('Filed NAD83 coordinates are displayed as approximate WGS84 without a datum transformation. '
                      'Check the original registration and field conditions before using a structure for planning.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.status = QLabel('Choose an archive and enter its publication date.')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        layout.addStretch()
        buttons = QHBoxLayout()
        self.install = QPushButton('Import regional pack')
        self.install.clicked.connect(self.start_import)
        close = QPushButton('Close')
        close.clicked.connect(self.reject)
        buttons.addWidget(self.install)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self.controls = [self.path, browse, self.name, self.bounds, self.date, self.install]

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select FCC registration ZIP', '', 'ZIP archives (*.zip)')
        if path:
            self.path.setText(path)

    def start_import(self):
        try:
            bounds = [float(part.strip()) for part in self.bounds.text().split(',')]
        except ValueError:
            self.status.setText('Enter four numerical bounds: west, south, east, north.')
            return
        self.start_job(partial(_import_job, self.store_root, self.path.text().strip(), bounds,
                               self.date.text().strip(), self.name.text().strip()))

    @Slot(object)
    def job_ready(self, result):
        self.status.setText('Installed ' + str(result['installed']['record_count']) + ' constructed structure references. '
                            'Their presence does not identify the connected cell.')

    @Slot(object)
    def job_progress(self, value):
        self.status.setText(str(value))
