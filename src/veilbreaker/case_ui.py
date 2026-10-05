"""Desktop management of operator-confirmed diagnostic cases."""
import json
import sqlite3
from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPlainTextEdit, QCheckBox, QHeaderView, QScrollArea, QWidget, QComboBox, QFileDialog
from . import core


def show_cases(window):
    from .gui import label, button, table, fill
    dialog = QDialog(window)
    dialog.setWindowTitle("Confirmed cases")
    available = window.screen().availableGeometry()
    dialog.resize(min(1000, available.width() - 40), min(750, available.height() - 80))
    outer = QVBoxLayout(dialog)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    scroll.setWidget(content)
    outer.addWidget(scroll)
    layout = QVBoxLayout(content)
    layout.addWidget(label("Confirmed cases", "title"))
    layout.addWidget(label("Record only causes verified through your investigation. Similar cases inform future diagnostic suggestions; they do not prove the cause of a new problem. Original run evidence is unchanged.", "muted"))
    search = QLineEdit()
    search.setAccessibleName("Search cases")
    search.setPlaceholderText("Find cases by site, cause, resolution or run ID")
    search.setClearButtonEnabled(True)
    layout.addWidget(search)
    state = QComboBox()
    state.setAccessibleName("Case state")
    state.addItems(["All states","Confirmed","Withdrawn"])
    layout.addWidget(state)
    rows = table(["Case", "Site", "Cause", "State", "Source run"])
    rows.setAccessibleName("Saved cases")
    layout.addWidget(rows, 1)
    details = QPlainTextEdit()
    details.setReadOnly(True)
    details.setMaximumHeight(100)
    details.setAccessibleName("Case details")
    layout.addWidget(details)
    status = label("", "muted")
    layout.addWidget(status)
    records = []
    offset = [0]
    def refresh():
        store = core.VeilbreakerStore(window.config.db_path)
        try:
            found,total = store.search_cases(search.text(),state.currentText(),offset=offset[0])
            if offset[0] and not found:
                offset[0] = 0
                found,total = store.search_cases(search.text(),state.currentText())
            records[:] = [dict(r) for r in found]
        finally:
            store.close()
        rows.blockSignals(True)
        rows.clearSelection()
        rows.setCurrentCell(-1,-1)
        fill(rows, [[r["case_id"], r["site_id"], r["cause"], "Confirmed" if r["confirmed"] else "Withdrawn", r["source_run_id"]] for r in records])
        rows.blockSignals(False)
        details.clear()
        withdraw.setEnabled(False)
        export_button.setEnabled(False)
        source_button.setEnabled(False)
        previous.setEnabled(offset[0] > 0)
        next_page.setEnabled(offset[0]+len(records) < total)
        status.setText(f"{offset[0]+1 if records else 0}–{offset[0]+len(records)} of {total} matching cases")
        rows.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        rows.setColumnWidth(2, 300)
    def select():
        i = rows.currentRow()
        if 0 <= i < len(records):
            r = records[i]
            store = core.VeilbreakerStore(window.config.db_path)
            try:
                record = store.case_record(r["case_id"])
            finally:
                store.close()
            history = "\n".join(f"{e['timestamp_utc']} • {e['action']} • {json.dumps(e['details'],ensure_ascii=False)}" for e in record["events"])
            details.setPlainText(f"Created: {r['created_utc']}\nCause: {r['cause']}\nResolution: {r['resolution'] or 'Not recorded'}\nEvents:\n{history or 'No recorded events; legacy case.'}")
            withdraw.setEnabled(bool(r["confirmed"]))
            export_button.setEnabled(True)
            source_button.setEnabled(record["source"] is not None)
    def unconfirm():
        i = rows.currentRow()
        if not 0 <= i < len(records):
            return
        store = core.VeilbreakerStore(window.config.db_path)
        try:
            store.withdraw_case(records[i]["case_id"], reason.text())
            reason.clear()
            refresh()
            status.setText("Confirmation withdrawn. This case will no longer inform new diagnostic suggestions; past reports are unchanged.")
        except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
            window.error(str(exc))
        finally:
            store.close()
    reason = QLineEdit()
    reason.setMaxLength(2000)
    reason.setAccessibleName("Withdrawal reason")
    reason.setPlaceholderText("Reason for withdrawing confirmation (optional; retained in event history)")
    layout.addWidget(reason)
    withdraw = button("Withdraw selected confirmation", unconfirm)
    layout.addWidget(withdraw)
    def selected_record():
        i = rows.currentRow()
        if not 0 <= i < len(records):
            return None
        store = core.VeilbreakerStore(window.config.db_path)
        try:
            return store.case_record(records[i]["case_id"])
        finally:
            store.close()
    def export():
        record = selected_record()
        if record is None:
            return
        path,_ = QFileDialog.getSaveFileName(dialog,"Export case record",record["case"]["case_id"]+".json","JSON (*.json)")
        if path:
            from .recovery import atomic_json
            try:
                atomic_json(Path(path),record)
                status.setText("Case record and recorded events exported; original evidence unchanged.")
            except OSError as exc:
                window.error(str(exc))
    def open_source():
        record = selected_record()
        if record is None or record["source"] is None:
            return
        store = core.VeilbreakerStore(window.config.db_path)
        try:
            row = store.get_run(record["source"]["run_id"])
        finally:
            store.close()
        if row:
            window.display_saved_run(dict(row))
            dialog.accept()
    from .widgets import FlowLayout
    actions = FlowLayout()
    export_button = button("Export selected case…",export)
    source_button = button("Open source diagnostic",open_source)
    def page(delta):
        offset[0] = max(0,offset[0]+delta)
        refresh()
    previous = button("Newer cases",lambda: page(-200))
    next_page = button("Older cases",lambda: page(200))
    for control in (export_button,source_button,previous,next_page):
        actions.addWidget(control)
    layout.addLayout(actions)
    rows.itemSelectionChanged.connect(select)
    source = window.selected_run()
    layout.addWidget(label("New case source: " + (source["run_id"] if source else "Select a run in Run history, then reopen this window."), "muted"))
    cause = QLineEdit()
    cause.setMaxLength(2000)
    cause.setPlaceholderText("Verified cause")
    cause.setAccessibleName("Confirmed cause")
    layout.addWidget(cause)
    resolution = QPlainTextEdit()
    resolution.setMaximumHeight(90)
    resolution.setPlaceholderText("What resolved it, and how you verified the outcome (up to 4000 characters)")
    resolution.setAccessibleName("Confirmed resolution")
    layout.addWidget(resolution)
    verified = QCheckBox("I verified this cause; it is not just the diagnostic hypothesis")
    layout.addWidget(verified)
    def save():
        if not source or not verified.isChecked():
            return
        store = core.VeilbreakerStore(window.config.db_path)
        try:
            case_id = store.add_case(source["run_id"], cause.text(), resolution.toPlainText())
            cause.clear(); resolution.clear(); verified.setChecked(False)
            refresh()
            status.setText(f"Saved {case_id}. Original evidence preserved.")
        except (ValueError, KeyError, sqlite3.Error) as exc:
            window.error(str(exc))
        finally:
            store.close()
    save_button = button("Save confirmed case", save, True)
    save_button.setEnabled(False)
    verified.toggled.connect(lambda checked: save_button.setEnabled(bool(source) and checked))
    layout.addWidget(save_button)
    def filtered():
        offset[0] = 0
        refresh()
    search.textChanged.connect(filtered)
    state.currentIndexChanged.connect(filtered)
    refresh()
    dialog.exec()
