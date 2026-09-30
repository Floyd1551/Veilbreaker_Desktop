"""Native desktop workspace around the same collectors and reasoning as the CLI."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

from PySide6.QtCore import Qt, QProcess, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)
from . import __version__, core
from .jobs import demo_payload
from .spectrum import SpectrumView

STYLE = """
QWidget { background: #101722; color: #dee7f2; font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 13px; }
QLabel { background: transparent; }
QMainWindow { background: #101722; }
QFrame#sidebar { background: #0b111b; border-right: 1px solid #243145; }
QLabel#brand { color: #f4f8ff; font-size: 21px; font-weight: 700; letter-spacing: 2px; }
QLabel#eyebrow { color: #55d7c0; font-size: 11px; font-weight: 700; letter-spacing: 2px; }
QLabel#title { font-size: 29px; font-weight: 600; color: #f4f8ff; }
QLabel#muted { color: #98aac0; }
QLabel#metric { font-size: 29px; color: #6be0ca; font-weight: 600; }
QFrame#card { background: #172131; border: 1px solid #2a394e; border-radius: 10px; }
QFrame#card QLabel { background: transparent; border: none; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { padding: 14px 12px; margin: 3px 0; border-radius: 7px; color: #aebdd1; }
QListWidget::item:selected { background: #1c3540; color: #77ead3; }
QListWidget::item:hover { background: #1b283a; }
QPushButton { background: #223249; border: 1px solid #354960; border-radius: 6px; padding: 9px 14px; }
QPushButton:hover { background: #2c425d; border-color: #7390ae; }
QPushButton:focus { border: 2px solid #72deca; }
QPushButton:disabled { color: #63738a; background: #192232; border-color: #263247; }
QPushButton#primary { background: #5bd7bd; color: #09241f; font-weight: 700; border: 1px solid #5bd7bd; }
QPushButton#primary:hover { background: #87ecd5; }
QPushButton#primary:disabled { background: #31564f; color: #a6bab6; }
QLineEdit, QComboBox, QPlainTextEdit, QTextBrowser { background: #111b29; border: 1px solid #35465e; border-radius: 5px; padding: 8px; selection-background-color: #28574e; }
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus { border-color: #65d7c0; }
QComboBox::drop-down { border: none; width: 24px; }
QCheckBox { padding: 6px 0; }
QCheckBox::indicator { width: 17px; height: 17px; }
QTableWidget { background: #131e2d; alternate-background-color: #182536; border: 1px solid #2b3c52; gridline-color: #253449; selection-background-color: #254d4b; }
QHeaderView::section { background: #1c2a3c; color: #adbed3; padding: 10px; border: none; font-weight: 600; }
QTabWidget::pane { border: 1px solid #2b3c52; }
QTabBar::tab { background: #162132; padding: 11px 16px; color: #9cacc2; }
QTabBar::tab:selected { background: #243b46; color: #84e4d2; }
QProgressBar { background: #18283b; border: none; border-radius: 3px; height: 5px; }
QProgressBar::chunk { background: #5bd7bd; }
QScrollArea { border: none; }
QStatusBar { background: #0b111b; color: #a1b4c7; }
"""


def label(text, name=None):
    widget = QLabel(text)
    widget.setWordWrap(True)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    if primary:
        widget.setObjectName("primary")
    return widget


def table(headers):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    widget.verticalHeader().hide()
    widget.setAlternatingRowColors(True)
    widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    widget.setWordWrap(True)
    return widget


def fill(widget, rows):
    widget.setSortingEnabled(False)
    widget.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            item = QTableWidgetItem(str(value))
            item.setToolTip(str(value))
            widget.setItem(r, c, item)
    widget.resizeRowsToContents()


def page(title, subtitle):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(28, 24, 28, 22)
    layout.setSpacing(16)
    layout.addWidget(label(title, "title"))
    layout.addWidget(label(subtitle, "muted"))
    return widget, layout


class MainWindow(QMainWindow):
    def __init__(self, config=None):
        super().__init__()
        self.config = config if config is not None else core.load_config(None)
        self.process = None
        self.job_dir = None
        self.cancelled = False
        self.payload = None
        self.history_rows = []
        self.setWindowTitle(f"Veilbreaker • Network Intelligence {__version__}")
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "assets/app.svg")))
        self.resize(1320, 890)
        self.setMinimumSize(980, 720)
        root = QWidget()
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(225)
        rail = QVBoxLayout(side)
        rail.setContentsMargins(18, 30, 18, 20)
        rail.addWidget(label("VEILBREAKER", "brand"))
        rail.addWidget(label("NETWORK INTELLIGENCE", "eyebrow"))
        rail.addSpacing(30)
        self.nav = QListWidget()
        self.nav.setAccessibleName("Workspace navigation")
        self.nav.addItems(["Overview", "Diagnostics", "Run history", "Tools & readiness", "Settings"])
        rail.addWidget(self.nav)
        rail.addWidget(label("FIELD WORKSPACE", "eyebrow"))
        rail.addWidget(label("Evidence first.\nExplain every conclusion.", "muted"))
        rail.addSpacing(12)
        rail.addWidget(label(f"Desktop + CLI\nv{__version__}", "muted"))
        self.pages = QStackedWidget()
        row.addWidget(side)
        row.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        self.build_overview()
        self.build_diagnostics()
        self.build_history()
        self.build_tools()
        self.build_settings()
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)
        self.statusBar().showMessage("Ready • Choose a workflow or explore the synthetic demo")
        self.refresh_history()

    def build_overview(self):
        widget, layout = page("See the evidence. Find the cause.",
                              "A field workspace for network, cellular, satellite and RF diagnostics.")
        hero = QFrame()
        hero.setObjectName("card")
        box = QVBoxLayout(hero)
        box.setContentsMargins(25, 24, 25, 24)
        box.addWidget(label("YOUR NEXT INVESTIGATION", "eyebrow"))
        box.addWidget(label("Start with a snapshot", "title"))
        box.addWidget(label("Collect host and link information, analyze a saved metric file, or explore a demonstration. Active tests and hardware collectors are selected explicitly.", "muted"))
        actions = QHBoxLayout()
        actions.addWidget(button("New diagnostic", lambda: self.nav.setCurrentRow(1), True))
        actions.addWidget(button("Import metrics…", self.import_metrics))
        actions.addWidget(button("Explore demo", self.show_demo))
        actions.addStretch()
        box.addLayout(actions)
        layout.addWidget(hero)
        cards = QHBoxLayout()
        for title, detail in [
            ("01  Collect", "Windows and Linux host collectors. Optional modem, Starlink and receive-only SDR evidence."),
            ("02  Explain", "Ranked hypotheses with supporting and contradicting evidence, data quality and next tests."),
            ("03  Preserve", "Local run history, site baselines, confirmed cases and portable evidence bundles."),
        ]:
            frame = QFrame()
            frame.setObjectName("card")
            col = QVBoxLayout(frame)
            col.setContentsMargins(20, 22, 20, 22)
            col.addWidget(label(title, "eyebrow"))
            col.addWidget(label(detail, "muted"))
            cards.addWidget(frame)
        layout.addLayout(cards)
        layout.addWidget(label("WORKSPACE STATUS", "eyebrow"))
        self.overview_status = label("No saved runs yet.", "muted")
        layout.addWidget(self.overview_status)
        layout.addWidget(label("Hardware support depends on drivers, permissions and available tools. A hypothesis score expresses the engine's ranking, not a calibrated probability of root cause.", "muted"))
        layout.addStretch()
        self.pages.addWidget(widget)

    def build_diagnostics(self):
        widget, layout = page("Diagnostic workspace", "Collect a snapshot, review competing explanations, and preserve the evidence.")
        controls = QHBoxLayout()
        self.site = QLineEdit(self.config.site_id)
        self.site.setAccessibleName("Site identifier")
        self.site.setPlaceholderText("Site identifier")
        self.scenario = QComboBox()
        self.scenario.addItems(sorted(core.SCENARIO_OVERRIDES))
        self.scenario.setCurrentText(self.config.scenario)
        self.scenario.setAccessibleName("Diagnostic scenario")
        controls.addWidget(label("Site"))
        controls.addWidget(self.site, 1)
        controls.addWidget(label("Scenario"))
        controls.addWidget(self.scenario, 1)
        layout.addLayout(controls)
        options = QHBoxLayout()
        self.flags = {}
        for key, title, tip in [
            ("active", "Ping + DNS", "Send bounded ping and DNS measurements to configured targets."),
            ("guided", "Guided follow-up", "Also permits active tests and one supported follow-up cycle."),
            ("cellular", "Cellular", "Query the selected modem using read-only AT commands."),
            ("starlink", "Starlink", "Read telemetry from the configured dish management endpoint."),
            ("sdr", "SDR sweep", "Receive-only HackRF sweep of configured ranges."),
            ("throughput", "Throughput", "Generate traffic to the configured iperf3 server."),
        ]:
            check = QCheckBox(title)
            check.setToolTip(tip)
            options.addWidget(check)
            self.flags[key] = check
        layout.addLayout(options)
        actions = QHBoxLayout()
        self.run_button = button("Run diagnostic", self.run_diagnostic, True)
        self.import_button = button("Import metrics…", self.import_metrics)
        self.cancel_button = button("Cancel task", self.cancel_task)
        self.cancel_button.setEnabled(False)
        self.export_button = button("Save evidence ZIP…", self.export_evidence)
        self.export_button.setEnabled(False)
        actions.addWidget(self.run_button)
        actions.addWidget(self.import_button)
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        actions.addWidget(self.export_button)
        layout.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.result_caption = label("No assessment yet • Run a diagnostic or import a JSON metric snapshot.", "muted")
        layout.addWidget(self.result_caption)
        stats = QHBoxLayout()
        self.stat_labels = []
        for name in ("HEALTH / 100", "DATA QUALITY / 100", "FINDINGS", "ASSESSMENT"):
            card = QFrame()
            card.setObjectName("card")
            col = QVBoxLayout(card)
            col.addWidget(label(name, "eyebrow"))
            value = label("—", "metric")
            col.addWidget(value)
            stats.addWidget(card)
            self.stat_labels.append(value)
        layout.addLayout(stats)
        self.tabs = QTabWidget()
        self.summary = QTextBrowser()
        self.summary.setOpenExternalLinks(False)
        self.summary.setPlainText("Your evidence summary will appear here. Missing measurements remain unknown.")
        self.hypotheses = table(["Likely cause", "Score", "Status", "Supporting / contradicting evidence"])
        self.findings = table(["Severity", "Finding", "Observation", "Recommended action"])
        self.next_tests = table(["Priority", "Next test", "Why", "Action"])
        self.metrics = table(["Metric", "Value"])
        self.notes = QPlainTextEdit()
        self.notes.setReadOnly(True)
        self.spectrum = SpectrumView()
        spectrum_panel = QWidget()
        spectrum_layout = QVBoxLayout(spectrum_panel)
        self.sweep_selector = QComboBox()
        self.sweep_selector.setAccessibleName("Captured spectrum range")
        self.sweep_selector.currentIndexChanged.connect(self.select_sweep)
        spectrum_layout.addWidget(self.sweep_selector)
        spectrum_layout.addWidget(self.spectrum, 1)
        for name, panel in [("Summary", self.summary), ("Hypotheses", self.hypotheses),
                            ("Findings", self.findings), ("Next tests", self.next_tests),
                            ("Metrics", self.metrics), ("Collector notes", self.notes), ("Spectrum", spectrum_panel)]:
            self.tabs.addTab(panel, name)
        layout.addWidget(self.tabs, 1)
        self.pages.addWidget(widget)

    def build_history(self):
        widget, layout = page("Run history", "Reopen saved evidence or compare two snapshots from the same investigation.")
        actions = QHBoxLayout()
        actions.addWidget(button("Refresh", self.refresh_history))
        actions.addWidget(button("Open selected run", self.open_history))
        actions.addWidget(button("Compare selected to previous", self.compare_history))
        actions.addStretch()
        layout.addLayout(actions)
        self.history = table(["Run", "UTC", "Site", "Scenario", "Note"])
        self.history.cellDoubleClicked.connect(lambda *_: self.open_history())
        layout.addWidget(self.history, 2)
        self.comparison = QPlainTextEdit()
        self.comparison.setReadOnly(True)
        self.comparison.setPlaceholderText("Comparison uses the preceding saved run at the same site and scenario. Numeric deltas describe change; they do not automatically mean improvement.")
        layout.addWidget(self.comparison, 1)
        self.pages.addWidget(widget)

    def build_tools(self):
        widget, layout = page("Tools & readiness", "Inspect local dependencies and supported modem families before field work.")
        actions = QHBoxLayout()
        for title, action in [("Check readiness", "doctor"), ("List serial ports", "ports"),
                              ("Modem driver matrix", "drivers"), ("Engine self-test", "selftest")]:
            actions.addWidget(button(title, lambda checked=False, a=action: self.start_job(a)))
        actions.addStretch()
        layout.addLayout(actions)
        layout.addWidget(button("Verify evidence ZIP…", self.verify_evidence))
        sdr_actions = QHBoxLayout()
        sdr_actions.addWidget(button("Discover HackRF", lambda: self.start_job("hackrf_info")))
        capture = button("Capture 2.4 GHz", self.capture_wifi, True)
        capture.setToolTip("Receive-only 2400–2500 MHz, 1 MHz bins, 3 sweeps. RF amplifier and antenna power off.")
        sdr_actions.addWidget(capture)
        sdr_actions.addWidget(label("3 receive-only sweeps • 1 MHz bins • antenna power off", "muted"))
        sdr_actions.addStretch()
        layout.addLayout(sdr_actions)
        layout.addWidget(label("Readiness can query hardware enabled in Settings. Serial-port listing does not open ports. Additional CLI commands remain available for targeted modem, Starlink, SDR and path tests.", "muted"))
        self.tool_output = QPlainTextEdit()
        self.tool_output.setReadOnly(True)
        self.tool_output.setPlaceholderText("Choose a check above. Missing optional hardware does not prevent offline analysis.")
        layout.addWidget(self.tool_output, 1)
        layout.addWidget(button("Cancel running task", self.cancel_task))
        self.pages.addWidget(widget)

    def verify_evidence(self):
        source, _ = QFileDialog.getOpenFileName(self, "Verify evidence bundle", "", "ZIP archive (*.zip)")
        if source:
            self.start_job("verify", input=source)

    def build_settings(self):
        widget, layout = page("Settings", "Configure targets, hardware and storage. Existing CLI configuration is supported.")
        layout.addWidget(label(f"Configuration: {core.default_config_path()}\nData: {self.config.root}", "muted"))
        layout.addWidget(label("JSON adapter commands run as your user when their collector is used. Diagnostic checkboxes control optional hardware for desktop runs; readiness uses saved configuration.", "muted"))
        actions = QHBoxLayout()
        actions.addWidget(button("Save settings", self.save_settings, True))
        actions.addWidget(button("Reload saved settings", self.reload_settings))
        actions.addWidget(button("Open data folder", self.open_data_folder))
        actions.addStretch()
        layout.addLayout(actions)
        self.config_editor = QPlainTextEdit(json.dumps(self.config.to_dict(), indent=2))
        self.config_editor.setAccessibleName("Configuration JSON")
        layout.addWidget(self.config_editor, 1)
        self.pages.addWidget(widget)

    def effective_config(self):
        cfg = core.AppConfig.from_dict(self.config.to_dict())
        cfg.site_id = self.site.text().strip() or "default"
        cfg.scenario = self.scenario.currentText()
        return cfg

    def run_diagnostic(self):
        options = {key: check.isChecked() for key, check in self.flags.items()}
        options["active"] = options["active"] or options["guided"]
        if options["throughput"] and not self.config.iperf3_server:
            self.error("Set iperf3_server in Settings before enabling throughput.")
            return
        self.start_job("run", options=options)

    def capture_wifi(self):
        self.start_job("run", options={"sdr": True}, wifi_capture=True)

    def import_metrics(self):
        if self.process is not None:
            self.statusBar().showMessage("A task is already running. Finish or cancel it first.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Import metric snapshot", "", "JSON metrics (*.json)")
        if path:
            self.nav.setCurrentRow(1)
            self.start_job("analyze", input=path)

    def show_demo(self):
        self.display_payload(demo_payload())
        self.nav.setCurrentRow(1)

    def start_job(self, action, **extra):
        if self.process is not None:
            self.statusBar().showMessage("A task is already running. Finish or cancel it first.")
            return
        cfg = self.effective_config()
        if extra.pop("wifi_capture", False):
            cfg.sdr.ranges = [core.SDRRange("wifi24", 2400, 2500)]
            cfg.sdr.sweeps = 3
            cfg.sdr.bin_width_hz = 1_000_000
            cfg.sdr.lna_gain_db, cfg.sdr.vga_gain_db = 16, 20
            cfg.sdr.amp_enable = cfg.sdr.antenna_power = False
            cfg.satellite.command = None
        if action == "run":
            opts = extra.get("options", {})
            cfg.cellular.enabled = bool(opts.get("cellular"))
            cfg.starlink.enabled = bool(opts.get("starlink"))
            cfg.sdr.enabled = bool(opts.get("sdr"))
        self.job_dir = tempfile.TemporaryDirectory(prefix="veilbreaker-job-")
        job_path = Path(self.job_dir.name)
        request = {"action": action, "config": cfg.to_dict(), **extra}
        (job_path / "request.json").write_text(json.dumps(request), encoding="utf-8")
        self.cancelled = False
        process = QProcess(self)
        self.process = process
        process.finished.connect(self.job_finished)
        process.errorOccurred.connect(self.job_error)
        if getattr(sys, "frozen", False):
            program = str(Path(sys.executable).with_name("veilbreaker.exe" if os.name == "nt" else "veilbreaker"))
            args = []
        else:
            program, args = sys.executable, ["-m", "veilbreaker"]
        args += ["--desktop-job", str(job_path / "request.json"), str(job_path / "result.json")]
        self.set_busy(True)
        self.statusBar().showMessage(f"Running {action}… Collectors may take a moment; cancellation is available.")
        process.start(program, args)

    def set_busy(self, busy):
        self.run_button.setEnabled(not busy)
        self.import_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.progress.setVisible(busy)
        self.pages.widget(4).setEnabled(not busy)

    def job_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.error("Could not launch the diagnostic worker. Reinstall the complete application bundle.")
            self.cleanup_job()

    def job_finished(self, code, status):
        if self.process is None:
            return
        try:
            result_path = Path(self.job_dir.name) / "result.json"
            if self.cancelled:
                self.statusBar().showMessage("Task cancelled. Any completed artifacts remain in the data folder.")
            elif result_path.exists():
                obj = json.loads(result_path.read_text(encoding="utf-8"))
                if not obj["ok"]:
                    self.error(obj["error"])
                elif "report" in obj["result"]:
                    self.display_payload(obj["result"])
                    self.nav.setCurrentRow(1)
                    if obj["result"].get("sweeps"):
                        self.tabs.setCurrentIndex(6)
                    self.statusBar().showMessage("Diagnostic complete • Evidence saved locally")
                else:
                    self.tool_output.setPlainText(obj["result"]["text"])
                    self.statusBar().showMessage("Check complete" if not obj["result"].get("returncode") else "Check completed with issues • Review the output")
            else:
                stderr = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
                self.error(f"Task exited ({code}) without a result. {stderr[-1800:]}")
        except (OSError, ValueError, KeyError) as exc:
            self.error(str(exc))
        finally:
            self.cleanup_job()
            self.refresh_history()

    def cleanup_job(self):
        process, self.process = self.process, None
        if process:
            process.deleteLater()
        if self.job_dir:
            self.job_dir.cleanup()
            self.job_dir = None
        self.set_busy(False)

    def cancel_task(self):
        if self.process is None:
            return
        self.cancelled = True
        pid = int(self.process.processId())
        if pid and os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
        elif pid:
            try:
                if os.getpgid(pid) == pid:
                    os.killpg(pid, signal.SIGTERM)
                else:
                    self.process.kill()
            except ProcessLookupError:
                pass
        self.process.kill()

    def display_payload(self, payload):
        self.payload = payload
        report = payload["report"]
        self.result_caption.setText(f"{'SYNTHETIC DEMO • ' if payload['run_id'] == 'demo' else ''}{payload.get('site_id', '')}  /  {payload['run_id']}")
        insufficient = report["status"] == "INSUFFICIENT_EVIDENCE"
        for item, value in zip(self.stat_labels, ["—" if insufficient else report["health_score"], report["data_quality_score"], len(report["findings"]), "Needs evidence" if insufficient else report["status"].replace("_", " ").title()]):
            item.setText(str(value))
        status_color = {"critical": "#ff8585", "impaired": "#ffb36b", "degraded": "#f3d27a", "healthy": "#6be0ca", "unknown": "#a8b8cc"}.get(report["status"].lower(), "#a8b8cc")
        self.stat_labels[-1].setStyleSheet(f"color: {status_color};")
        self.summary.setPlainText("\n\n".join(report["summary"]) + "\n\nScores rank competing hypotheses; they are not calibrated probabilities. Review evidence and collector notes before acting.")
        fill(self.hypotheses, [[h["title"], f"{h['confidence']:.0%}", h["status"],
                               "\n".join(f"{e['direction']}: {e['statement']}" for e in h["evidence"])] for h in report["hypotheses"]])
        fill(self.findings, [[f["severity"], f["title"], f["observation"], f["recommendation"]] for f in report["findings"]])
        fill(self.next_tests, [[t["priority"], t["title"], t["purpose"], t["action"]] for t in report["next_tests"]])
        fill(self.metrics, [[k, json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v] for k, v in sorted(payload["metrics"].items())])
        self.notes.setPlainText("\n".join(payload.get("notes", [])) or "No collector notes recorded.")
        self.export_button.setEnabled(bool(payload.get("evidence_zip")))
        self.sweep_selector.blockSignals(True)
        self.sweep_selector.clear()
        for sweep in payload.get("sweeps", []):
            self.sweep_selector.addItem(sweep["label"], sweep)
        self.sweep_selector.blockSignals(False)
        self.select_sweep()

    def select_sweep(self, *_):
        self.spectrum.load_sweep(self.sweep_selector.currentData())

    def refresh_history(self):
        if not self.config.db_path.exists():
            self.history_rows = []
        else:
            try:
                store = core.VeilbreakerStore(self.config.db_path)
                try:
                    self.history_rows = [dict(r) for r in store.list_runs(limit=200)]
                finally:
                    store.close()
            except Exception as exc:
                self.statusBar().showMessage(f"Could not read history: {exc}")
                return
        fill(self.history, [[r["run_id"], r["ts_utc"], r["site_id"], r["scenario"], r["note"] or ""] for r in self.history_rows])
        self.overview_status.setText(f"{len(self.history_rows)} recent saved runs • {self.config.root}")

    def selected_run(self):
        row = self.history.currentRow()
        return self.history_rows[row] if 0 <= row < len(self.history_rows) else None

    def open_history(self):
        row = self.selected_run()
        if not row:
            self.statusBar().showMessage("Select a saved run first.")
            return
        pack = self.config.reports_dir / f"{row['run_id']}_evidence.zip"
        notes = Path(row["artifact_dir"]) / "collector_notes.txt" if row.get("artifact_dir") else None
        sweep_file = Path(row["artifact_dir"]) / "sdr_summaries.json" if row.get("artifact_dir") else None
        self.display_payload({"report": json.loads(row["report_json"]), "metrics": json.loads(row["metrics_json"]),
                              "run_id": row["run_id"], "site_id": row["site_id"],
                              "notes": notes.read_text(encoding="utf-8", errors="replace").splitlines() if notes and notes.exists() else [],
                              "evidence_zip": str(pack) if pack.exists() else None,
                              "sweeps": json.loads(sweep_file.read_text(encoding="utf-8")) if sweep_file and sweep_file.exists() else []})
        self.nav.setCurrentRow(1)

    def compare_history(self):
        row = self.selected_run()
        if not row:
            self.statusBar().showMessage("Select a saved run first.")
            return
        older = next((r for r in self.history_rows[self.history.currentRow() + 1:]
                      if r["site_id"] == row["site_id"] and r["scenario"] == row["scenario"]), None)
        if not older:
            self.comparison.setPlainText("No preceding run for this site and scenario in the most recent 200 runs.")
            return
        from .comparison import compare_runs
        self.comparison.setPlainText(compare_runs(older, row))

    def export_evidence(self):
        if not self.payload or not self.payload.get("evidence_zip"):
            return
        source = Path(self.payload["evidence_zip"])
        target, _ = QFileDialog.getSaveFileName(self, "Save evidence bundle", source.name, "ZIP archive (*.zip)")
        if target:
            try:
                if Path(target).resolve() != source.resolve():
                    shutil.copy2(source, target)
                self.statusBar().showMessage(f"Evidence saved: {target}")
            except OSError as exc:
                self.error(str(exc))

    def save_settings(self):
        try:
            cfg = core.AppConfig.from_dict(json.loads(self.config_editor.toPlainText()))
            if not isinstance(cfg.data_dir, str) or not cfg.data_dir.strip():
                raise ValueError("data_dir must be a nonempty path")
            if cfg.scenario not in core.SCENARIO_OVERRIDES:
                raise ValueError("Unknown scenario")
            destination = core.default_config_path()
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(".tmp")
            temporary.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
            temporary.replace(destination)
            self.config = cfg
            self.site.setText(cfg.site_id)
            self.scenario.setCurrentText(cfg.scenario)
            self.refresh_history()
            self.statusBar().showMessage(f"Settings saved: {destination}")
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            self.error(f"Settings were not saved: {exc}")

    def reload_settings(self):
        try:
            self.config = core.load_config(None)
            self.config_editor.setPlainText(json.dumps(self.config.to_dict(), indent=2))
            self.site.setText(self.config.site_id)
            self.scenario.setCurrentText(self.config.scenario)
            self.refresh_history()
        except Exception as exc:
            self.error(str(exc))

    def open_data_folder(self):
        self.config.root.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.config.root)))

    def error(self, message):
        self.statusBar().showMessage(message)
        QMessageBox.warning(self, "Veilbreaker", message)

    def closeEvent(self, event):
        if self.process is not None:
            self.cancel_task()
            self.process.waitForFinished(5000)
        event.accept()


def smoke(destination):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    if os.name == "nt":
        for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf"):
            QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name))
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    with tempfile.TemporaryDirectory(prefix="veilbreaker-smoke-") as folder:
        window = MainWindow(core.AppConfig(data_dir=folder))
        errors = []
        window.error = errors.append
        window.show()
        from PySide6.QtTest import QTest
        import time
        source = Path(folder) / "smoke-metrics.json"
        source.write_text(json.dumps(demo_payload()["metrics"]), encoding="utf-8")
        window.site.setText("Packaging check (synthetic)")
        window.start_job("analyze", input=str(source))
        deadline = time.monotonic() + 30
        while window.process is not None and time.monotonic() < deadline:
            QTest.qWait(30)
        if window.process is not None:
            window.cancel_task()
            window.process.waitForFinished(5000)
            raise RuntimeError("GUI analysis worker timed out")
        if errors or window.history.rowCount() != 1:
            raise RuntimeError(f"GUI worker/history failed: {errors}")
        window.show_demo()
        app.processEvents()
        target = Path(destination)
        target.mkdir(parents=True, exist_ok=True)
        for index, name in enumerate(["overview", "diagnostics", "history", "tools", "settings"]):
            window.nav.setCurrentRow(index)
            QTest.qWait(80)
            app.processEvents()
            if not window.grab().save(str(target / f"{name}.png")):
                raise RuntimeError("Could not save GUI screenshot")
        assert window.metrics.rowCount() == len(demo_payload()["metrics"])
        assert not window.export_button.isEnabled()
        window.close()
    (target / "gui-smoke.json").write_text(json.dumps({"passed": True, "version": __version__, "pages": 5}), encoding="utf-8")
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke-test":
        return smoke(sys.argv[2])
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Veilbreaker")
    app.setOrganizationName("Outpost Relay")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    try:
        window = MainWindow()
    except Exception as exc:
        QMessageBox.critical(None, "Veilbreaker could not start", f"{exc}\n\nCheck configuration at {core.default_config_path()}.")
        return 2
    window.show()
    return app.exec()
