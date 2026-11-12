"""Manage local, source-preserving mobile survey copies."""
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from .background_dialog import JobDialog
from .mobile_survey_import import load_mobile_survey
from .mobile_survey_library import (import_mobile_survey, list_mobile_surveys, read_mobile_survey,
                                    delete_trashed_mobile_survey, restore_mobile_survey, trash_mobile_survey)
from .mobile_survey_ui import MobileSurveyReviewDialog


class MobileSurveyLibraryDialog(JobDialog):
    def __init__(self, parent, config, attach_input=None):
        super().__init__(parent)
        self.config = config; self.attach_input = attach_input
        self.rows = []; self.mode = ''; self.pending_review = None; self.refresh_after = False; self.notice = ''
        self.setWindowTitle('Imported mobile surveys'); self.resize(900, 600)
        layout = QVBoxLayout(self)
        info = QLabel('Local copies preserve the original mobile survey and can be reopened or mapped offline. Different file versions are kept separately by source hash. Trash hides a copy without deleting its evidence. Copies remain separate from Desktop diagnostic surveys; keep a separate backup.')
        info.setTextFormat(Qt.TextFormat.PlainText); info.setWordWrap(True); layout.addWidget(info)
        self.trash_filter = QCheckBox('Show Trash'); layout.addWidget(self.trash_filter)
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
        self.manage_button = QPushButton('Move to Trash…'); self.manage_button.clicked.connect(self.manage_selected); actions.addWidget(self.manage_button)
        self.delete_button = QPushButton('Delete permanently…'); self.delete_button.hide(); self.delete_button.clicked.connect(self.delete_selected); actions.addWidget(self.delete_button)
        self.refresh_button = QPushButton('Refresh'); self.refresh_button.clicked.connect(self.refresh); actions.addWidget(self.refresh_button)
        close = QPushButton('Close'); close.clicked.connect(self.reject); actions.addWidget(close)
        layout.addLayout(actions)
        self.controls = [self.table, self.import_button, self.open_button, self.manage_button, self.delete_button, self.refresh_button, self.trash_filter]
        self.table.itemSelectionChanged.connect(self.update_selection)
        self.table.itemDoubleClicked.connect(lambda *_: self.open_selected())
        self.trash_filter.toggled.connect(self.refresh)
        self.refresh()

    def set_busy(self, busy):
        super().set_busy(busy)
        if not busy: self.update_selection()

    def update_selection(self):
        selected = self.worker is None and bool(self.table.selectedItems()) and 0 <= self.table.currentRow() < len(self.rows)
        trashed = self.trash_filter.isChecked()
        self.open_button.setEnabled(selected and not trashed)
        self.manage_button.setEnabled(selected)
        self.manage_button.setText('Restore selected' if trashed else 'Move to Trash…')
        self.delete_button.setVisible(trashed)
        self.delete_button.setEnabled(selected and trashed)
        self.import_button.setEnabled(self.worker is None and not trashed)

    def refresh(self):
        if self.worker is not None: return
        self.mode = 'list'; self.status.setText('Checking saved mobile surveys…')
        trashed = self.trash_filter.isChecked()
        self.start_job(lambda cancelled, progress: list_mobile_surveys(self.config, trashed=trashed))

    def import_file(self):
        if self.worker is not None or self.trash_filter.isChecked(): return
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
        if self.worker is not None or self.trash_filter.isChecked() or not self.table.selectedItems() or not 0 <= index < len(self.rows): return
        digest = self.rows[index]['sha256']
        self.mode = 'open'; self.status.setText('Checking the stored source…')
        self.start_job(lambda cancelled, progress: read_mobile_survey(self.config, digest))

    def manage_selected(self):
        index = self.table.currentRow()
        if self.worker is not None or not self.table.selectedItems() or not 0 <= index < len(self.rows): return
        digest = self.rows[index]['sha256']
        if self.trash_filter.isChecked():
            self.mode = 'restore'; self.status.setText('Checking and restoring the saved source…')
            self.start_job(lambda cancelled, progress: restore_mobile_survey(self.config, digest))
        else:
            answer = QMessageBox.question(self, 'Move mobile survey to Trash?',
                'Hide this local copy? Its original evidence bytes remain on disk and can be restored. Other survey and source files are unchanged.')
            if answer != QMessageBox.StandardButton.Yes: return
            self.mode = 'trash'; self.status.setText('Moving the local copy to Trash…')
            self.start_job(lambda cancelled, progress: trash_mobile_survey(self.config, digest))

    def delete_selected(self):
        index = self.table.currentRow()
        if self.worker is not None or not self.trash_filter.isChecked() or not self.table.selectedItems() or not 0 <= index < len(self.rows): return
        row = self.rows[index]; digest = row['sha256']
        answer = QMessageBox.question(self, 'Permanently delete local copy?',
            f"Permanently delete the local copy of {row['name']} (source hash {digest[:12]})? This cannot be undone. Original mobile files, exports, and Desktop survey sessions are not changed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes: return
        self.mode = 'delete'; self.status.setText('Permanently deleting the verified local copy…')
        self.start_job(lambda cancelled, progress: delete_trashed_mobile_survey(self.config, digest))

    @Slot()
    def reject(self):
        if self.worker is not None and self.mode == 'delete':
            self.status.setText('Permanent deletion is in progress; wait for it to finish.')
            return
        super().reject()

    @Slot(object)
    def job_ready(self, value):
        if self.closing: return
        if self.mode == 'list':
            self.rows, unavailable = value
            self.table.clearSelection()
            self.table.setRowCount(len(self.rows))
            for index, row in enumerate(self.rows):
                state = 'Trash' if self.trash_filter.isChecked() else row['lifecycle']
                for column, item in enumerate((row['name'], state, str(row['point_count']), row['created_utc'], row['sha256'][:12])):
                    cell = QTableWidgetItem(item)
                    if column == 1 and row.get('removed_utc'): cell.setToolTip('Moved to Trash: ' + row['removed_utc'])
                    self.table.setItem(index, column, cell)
            label = 'in Trash' if self.trash_filter.isChecked() else 'saved'
            self.status.setText((self.notice + ' ' if self.notice else '') + f'{len(self.rows)} mobile survey(s) {label}.' +
                                (f' {unavailable} unavailable or changed copy/copies were preserved.' if unavailable else ''))
            self.notice = ''
        elif self.mode == 'import' and value is not None:
            self.notice = 'Mobile survey saved.' if value['imported'] else 'This exact survey is already saved.'
            self.refresh_after = True
        elif self.mode == 'open':
            self.pending_review = value
        elif self.mode in ('trash', 'restore', 'delete'):
            self.notice = {'trash': 'Moved to Trash; evidence was preserved.', 'restore': 'Mobile survey restored.',
                           'delete': 'Local copy permanently deleted.'}[self.mode]
            self.refresh_after = True

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
