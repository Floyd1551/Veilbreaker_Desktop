"""Offline saved-report viewing without a browser or archive extraction."""
from pathlib import Path
import zipfile
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTextBrowser, QVBoxLayout
from .widgets import FlowLayout

MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024


def read_reports(path):
    """Return original report bytes; ZIP members are never extracted to disk."""
    path = Path(path)
    def read(stream):
        data = stream.read(MAX_REPORT_BYTES + 1)
        if len(data) > MAX_REPORT_BYTES:
            raise ValueError('A report exceeds the 8 MiB viewing limit.')
        return data
    if path.is_dir():
        result = []
        for name in ('report.html', 'sdr_report.html', 'survey_report.html'):
            source = path / name
            if source.is_file():
                with source.open('rb') as stream:
                    result.append((name, read(stream)))
    elif path.suffix.lower() == '.zip':
        try:
            with zipfile.ZipFile(path) as archive:
                entries = [e for e in archive.infolist() if not e.is_dir() and Path(e.filename).suffix.lower() in ('.html', '.htm')]
                if len(entries) > 20 or sum(e.file_size for e in entries) > MAX_TOTAL_BYTES:
                    raise ValueError('This bundle contains too many or oversized reports.')
                if len({e.filename for e in entries}) != len(entries):
                    raise ValueError('This bundle contains duplicate report names.')
                result = []
                for entry in sorted(entries, key=lambda e: (Path(e.filename).name != 'report.html', e.filename)):
                    if entry.file_size > MAX_REPORT_BYTES:
                        raise ValueError('A report exceeds the 8 MiB viewing limit.')
                    with archive.open(entry) as stream:
                        result.append((entry.filename, read(stream)))
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
            raise ValueError(f'Cannot read reports from this ZIP: {exc}') from exc
    elif path.suffix.lower() in ('.html', '.htm'):
        with path.open('rb') as stream:
            result = [(path.name, read(stream))]
    else:
        raise ValueError('Choose an HTML report or an evidence ZIP.')
    if not result:
        raise ValueError('No HTML reports were found. Open another report or evidence bundle.')
    return result


class OfflineReportBrowser(QTextBrowser):
    def loadResource(self, resource_type, url):
        # Saved report text/tables need no remote content or unrelated local files.
        return QByteArray()


class ReportViewer(QDialog):
    def __init__(self, parent, path, reports=None):
        reports = read_reports(path) if reports is None else reports
        super().__init__(parent)
        self.reports = reports
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle('Veilbreaker • Saved reports')
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.resize(1100, 780)
        layout = QVBoxLayout(self)
        title = QLabel('Saved reports')
        title.setObjectName('section')
        layout.addWidget(title)
        source = QLabel(str(path))
        source.setWordWrap(True)
        source.setTextFormat(Qt.TextFormat.PlainText)
        source.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(source)
        self.selector = QComboBox()
        self.selector.setAccessibleName('Report to view')
        for name, _ in reports:
            friendly = {'report.html': 'Diagnostic report', 'sdr_report.html': 'SDR survey report', 'survey_report.html': 'Site survey report'}.get(Path(name).name, name)
            self.selector.addItem(friendly, name)
        layout.addWidget(self.selector)
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Find in this report · Ctrl+F')
        self.search.setAccessibleName('Find in report')
        self.search.setClearButtonEnabled(True)
        search_row.addWidget(self.search, 1)
        next_button = QPushButton('Find next')
        next_button.clicked.connect(self.find_next)
        search_row.addWidget(next_button)
        layout.addLayout(search_row)
        self.browser = OfflineReportBrowser()
        self.browser.setAccessibleName('Saved report content')
        self.browser.setOpenLinks(False)
        self.browser.setOpenExternalLinks(False)
        self.browser.setStyleSheet('QTextBrowser {background: white; color: #172131; padding: 18px; selection-background-color: #c5e7df; selection-color: #172131;}')
        self.browser.document().setDefaultStyleSheet('body, p, td, th {font-family: "Segoe UI", Arial, sans-serif; font-size: 13px;}')
        self.browser.anchorClicked.connect(self.follow_anchor)
        layout.addWidget(self.browser, 1)
        self.status = QLabel('Offline viewer • Text and tables • Opening a report does not verify its evidence bundle.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        actions = FlowLayout()
        for title, callback in [('Zoom in', lambda: self.browser.zoomIn(1)), ('Zoom out', lambda: self.browser.zoomOut(1)), ('Save HTML…', self.save_html), ('Close', self.close)]:
            control = QPushButton(title)
            control.clicked.connect(callback)
            actions.addWidget(control)
        layout.addLayout(actions)
        self.find_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.find_shortcut.activated.connect(self.search.setFocus)
        self.search.returnPressed.connect(self.find_next)
        self.selector.currentIndexChanged.connect(self.show_report)
        self.show_report()

    def show_report(self, *_):
        self.browser.setHtml(self.reports[self.selector.currentIndex()][1].decode('utf-8-sig', errors='replace'))
        self.browser.moveCursor(QTextCursor.MoveOperation.Start)
        self.search.clear()
        self.status.setText('Offline viewer • Text and tables • Opening a report does not verify its evidence bundle.')

    def find_next(self):
        query = self.search.text().strip()
        if not query:
            return
        found = self.browser.find(query)
        if not found:
            self.browser.moveCursor(QTextCursor.MoveOperation.Start)
            found = self.browser.find(query)
        self.status.setText('Match selected.' if found else 'No matching text in this report.')

    def follow_anchor(self, url):
        if url.toString().startswith('#'):
            self.browser.scrollToAnchor(url.fragment())
        else:
            self.status.setText('External links stay offline. Select and copy the reference if needed.')

    def save_html(self):
        name, data = self.reports[self.selector.currentIndex()]
        path, _ = QFileDialog.getSaveFileName(self, 'Save report HTML', Path(name).name, 'HTML report (*.html *.htm)')
        if path:
            try:
                target = Path(path)
                if target.suffix.lower() not in ('.html', '.htm'):
                    target = target.with_suffix('.html')
                target.write_bytes(data)
                self.status.setText('HTML report saved.')
            except OSError as exc:
                QMessageBox.warning(self, 'Could not save report', str(exc))
