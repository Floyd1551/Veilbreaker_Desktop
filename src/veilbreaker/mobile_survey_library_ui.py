"""Manage local, source-preserving mobile survey copies."""
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from .background_dialog import JobDialog
from .mobile_survey_import import load_mobile_survey
from .mobile_survey_library import import_mobile_survey, list_mobile_surveys, read_mobile_survey
from .mobile_survey_ui import MobileSurveyReviewDialog


class MobileSurveyLibraryDialog(JobDialog):
    def __init__(self, parent, config, attach_input=None):
        super().__init__(parent)
        self.config = config; self.attach_input = attach_input
        self.rows = []; self.mode = ''; self.pending_review = None; self.refresh_after = False; self.notice = ''
        self.setWindowTitle('Imported mobile surveys'); self.resize(900, 600)
        layout = QVBoxLayout(self)
        info = QLabel('Local copies preserve the original mobile survey and can be reopened or mapped offline. Different file versions are kept separately by source hash. Copies remain separate from Desktop diagnostic surveys; importing does not run tests. In-app removal is not yet available; keep a separate backup.')
        info.setTextFormat(Qt.TextFormat.PlainText); info.setWordWrap(True); layout.addWidget(info)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['Survey', 'State', 'Points', 'Created UTC', 'Source hash'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.status = QLabel('Loading mobile surveys…'); self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText); layout.addWidget(self.status)
        actions = QHBoxLayout()
        self.import_button = QPushButton('Import mobile survey…'); self.import_button.clicked.connect(self.import_file); actions.addWidget(self.import_button)
        self.open_button = QPushButton('Open selected…'); self.open_button.clicked.connect(self.open_selected); actions.addWidget(self.open_button)
        self.refresh_button = QPushButton('Refresh'); self.refresh_button.clicked.connect(self.refresh); actions.addWidget(self.refresh_button)
        close = QPushButton('Close'); close.clicked.connect(self.reject); actions.addWidget(close)
        layout.addLayout(actions)
        self.controls = [self.table, self.import_button, self.open_button, self.refresh_button]
        self.table.itemSelectionChanged.connect(self.update_selection)
        self.table.itemDoubleClicked.connect(lambda *_: self.open_selected())
        self.refresh()

    def set_busy(self, busy):
        super().set_busy(busy)
        if not busy: self.update_selection()

    def update_selection(self):
        self.open_button.setEnabled(self.worker is None and bool(self.table.selectedItems()) and 0 <= self.table.currentRow() < len(self.rows))

    def refresh(self):
        if self.worker is not None: return
        self.mode = 'list'; self.status.setText('Checking saved mobile surveys…')
        self.start_job(lambda cancelled, progress: list_mobile_surveys(self.config))

    def import_file(self):
        if self.worker is not None: return
        path, _ = QFileDialog.getOpenFileName(self, 'Import mobile survey', '', 'Mobile survey JSON (*.json)')
        if not path: return
        self.mode = 'import'; self.status.setText('Validating and saving a local copy…')
        def work(cancelled, progress):
            loaded = load_mobile_survey(path)
            if cancelled(): return None
            return import_mobile_survey(self.config, path, loaded['sha256'])
        self.start_job(work)

    def open_selected(self):
        index = self.table.currentRow()
        if self.worker is not None or not self.table.selectedItems() or not 0 <= index < len(self.rows): return
        digest = self.rows[index]['sha256']
        self.mode = 'open'; self.status.setText('Checking the stored source…')
        self.start_job(lambda cancelled, progress: read_mobile_survey(self.config, digest))

    @Slot(object)
    def job_ready(self, value):
        if self.closing: return
        if self.mode == 'list':
            self.rows, unavailable = value
            self.table.setRowCount(len(self.rows))
            for index, row in enumerate(self.rows):
                for column, item in enumerate((row['name'], row['lifecycle'], str(row['point_count']), row['created_utc'], row['sha256'][:12])):
                    self.table.setItem(index, column, QTableWidgetItem(item))
            self.status.setText((self.notice + ' ' if self.notice else '') + f'{len(self.rows)} saved mobile survey(s).' +
                                (f' {unavailable} unavailable or changed copy/copies were preserved.' if unavailable else ''))
            self.notice = ''
        elif self.mode == 'import' and value is not None:
            self.notice = 'Mobile survey saved.' if value['imported'] else 'This exact survey is already saved.'
            self.refresh_after = True
        elif self.mode == 'open':
            self.pending_review = value

    @Slot()
    def job_finished(self):
        closing = self.closing
        super().job_finished()
        if closing: return
        if self.refresh_after:
            self.refresh_after = False; self.refresh()
        elif self.pending_review is not None:
            loaded = self.pending_review; self.pending_review = None
            if MobileSurveyReviewDialog(self, loaded['path'], loaded, attach_input=self.attach_input).exec() == self.DialogCode.Accepted:
                self.accept()
