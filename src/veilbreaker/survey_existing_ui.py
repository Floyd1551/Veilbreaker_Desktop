"""Choose saved diagnostics without acquiring new measurements."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel, QPushButton
from . import core

class ExistingDiagnosticsDialog(QDialog):
    def __init__(self, config, session, parent=None):
        super().__init__(parent)
        self.config = config
        self.existing = {s['run_id'] for s in session['steps']}
        self.capacity = 20 - len(session['steps'])
        self.chosen = set()
        self.offset = 0
        self.setWindowTitle('Add existing diagnostics')
        self.resize(820, 480)
        body = QVBoxLayout(self)
        body.addWidget(QLabel('Select saved tests. Original site, scenario and evidence are retained.'))
        self.search = QLineEdit(); self.search.setPlaceholderText('Search run, date, site, scenario or note; press Enter')
        body.addWidget(self.search)
        self.items = QListWidget(); body.addWidget(self.items)
        self.count = QLabel(); body.addWidget(self.count)
        actions = QHBoxLayout(); body.addLayout(actions)
        self.previous = QPushButton('Previous'); self.next = QPushButton('Next')
        self.add = QPushButton('Add selected diagnostics'); cancel = QPushButton('Cancel')
        for control in (self.previous, self.next, self.add, cancel): actions.addWidget(control)
        self.previous.clicked.connect(lambda: self.page(-1)); self.next.clicked.connect(lambda: self.page(1))
        self.search.returnPressed.connect(self.restart)
        self.items.itemChanged.connect(self.changed)
        self.add.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        self.refresh()

    def selected_ids(self):
        return sorted(self.chosen)

    def restart(self):
        self.offset = 0; self.refresh()

    def page(self, direction):
        self.offset = max(0, self.offset + direction * 100); self.refresh()

    def changed(self, item):
        run_id = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked: self.chosen.add(run_id)
        else: self.chosen.discard(run_id)
        self.update_count()

    def update_count(self):
        self.count.setText(f'{len(self.chosen)} selected • {self.capacity} slots available')
        self.add.setEnabled(0 < len(self.chosen) <= self.capacity)

    def refresh(self):
        store = core.VeilbreakerStore(self.config.db_path)
        try: rows, total = store.search_runs(self.search.text(), limit=100, offset=self.offset)
        finally: store.close()
        self.items.blockSignals(True); self.items.clear()
        for row in rows:
            run_id = row['run_id']
            text = f"{row['ts_utc']} | {row['site_id']} | {row['scenario']} | {row['note'] or run_id}"
            item = QListWidgetItem(text); item.setToolTip(run_id)
            item.setData(Qt.ItemDataRole.UserRole, run_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if run_id in self.chosen else Qt.CheckState.Unchecked)
            if run_id in self.existing:
                item.setText(text + ' — Already in survey'); item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.items.addItem(item)
        self.items.blockSignals(False)
        self.previous.setEnabled(self.offset > 0); self.next.setEnabled(self.offset + 100 < total)
        self.update_count()
