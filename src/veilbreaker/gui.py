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
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QFontDatabase, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSpinBox, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem, QTabWidget, QSizePolicy,
    QTextBrowser, QVBoxLayout, QWidget,
)
from . import __version__, core
from .jobs import demo_payload
from .spectrum import SpectrumView
from .widgets import FlowLayout
from .scenarios import SCENARIOS, scenario_help

STYLE = """
QWidget { background: #101722; color: #dee7f2; font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 13px; }
QWidget#surfaceContainer { background: transparent; }
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
QFrame#card QCheckBox { background: transparent; }
QFrame#taskBanner { background: #1c3540; border-bottom: 1px solid #3b6b6c; }
QLabel#section { font-size: 18px; font-weight: 600; color: #f4f8ff; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { padding: 14px 12px; margin: 3px 0; border-radius: 7px; color: #aebdd1; }
QListWidget::item:selected { background: #1c3540; color: #77ead3; }
QListWidget::item:hover { background: #1b283a; }
QPushButton { background: #223249; border: 1px solid #354960; border-radius: 6px; padding: 9px 14px; }
QPushButton:hover { background: #2c425d; border-color: #7390ae; }
QPushButton:focus { border: 2px solid #72deca; }
QPushButton:checked { background: #243b46; border-color: #65d7c0; color: #84e4d2; }
QPushButton:disabled { color: #63738a; background: #192232; border-color: #263247; }
QPushButton#primary { background: #5bd7bd; color: #09241f; font-weight: 700; border: 1px solid #5bd7bd; }
QPushButton#primary:hover { background: #87ecd5; }
QPushButton#primary:disabled { background: #31564f; color: #a6bab6; }
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextBrowser { background: #111b29; border: 1px solid #35465e; border-radius: 5px; padding: 8px; selection-background-color: #28574e; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus, QTableWidget:focus { border-color: #65d7c0; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url(ASSET_ROOT/chevron-down.svg); width: 12px; height: 12px; }
QSpinBox { padding: 2px 24px 2px 8px; min-height: 30px; }
QSpinBox QLineEdit { border: none; padding: 0; background: transparent; }
QSpinBox::up-button, QSpinBox::down-button { width: 22px; background: #223249; border: none; }
QSpinBox::up-arrow { image: url(ASSET_ROOT/chevron-up.svg); width: 12px; height: 12px; }
QSpinBox::down-arrow { image: url(ASSET_ROOT/chevron-down.svg); width: 12px; height: 12px; }
QCheckBox { padding: 6px 0; }
QCheckBox::indicator { width: 17px; height: 17px; background: #111b29; border: 1px solid #71839b; border-radius: 3px; }
QCheckBox::indicator:checked { background: #5bd7bd; border-color: #5bd7bd; image: url(ASSET_ROOT/check.svg); }
QCheckBox::indicator:disabled { border-color: #35465e; }
QCheckBox:focus { color: #87ecd5; }
QToolTip { background: #223249; color: #f4f8ff; border: 1px solid #7390ae; padding: 6px; }
QTableWidget { background: #131e2d; alternate-background-color: #182536; border: 1px solid #2b3c52; gridline-color: #253449; selection-background-color: #254d4b; }
QHeaderView::section { background: #1c2a3c; color: #adbed3; padding: 10px; border: none; font-weight: 600; }
QTabWidget::pane { border: 1px solid #2b3c52; }
QTabBar::tab { background: #162132; padding: 11px 16px; color: #9cacc2; }
QTabBar::tab:selected { background: #243b46; color: #84e4d2; }
QProgressBar { background: #18283b; border: none; border-radius: 3px; height: 5px; }
QProgressBar::chunk { background: #5bd7bd; }
QScrollArea { border: none; }
QStatusBar { background: #0b111b; color: #a1b4c7; }
""".replace("ASSET_ROOT", (Path(__file__).parent / "assets").as_posix())


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
        available = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1320, available.width()), min(890, available.height()))
        self.setMinimumSize(min(760, available.width()), min(480, available.height()))
        root = QWidget()
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        side = QFrame()
        self.sidebar = side
        side.setObjectName("sidebar")
        side.setFixedWidth(210)
        rail = QVBoxLayout(side)
        rail.setContentsMargins(18, 30, 18, 20)
        rail.addWidget(label("VEILBREAKER", "brand"))
        rail.addWidget(label("NETWORK INTELLIGENCE", "eyebrow"))
        rail.addSpacing(30)
        self.nav = QListWidget()
        self.nav.setAccessibleName("Workspace navigation")
        sections = ["Overview", "Diagnostics", "Run history", "Tools & readiness", "Settings", "Site surveys"]
        self.nav.addItems(sections)
        navigation = self.menuBar().addMenu("Navigate")
        for index, title in enumerate(sections):
            action = navigation.addAction(title, lambda checked=False, i=index: self.nav.setCurrentRow(i))
            action.setShortcut(QKeySequence(f"Alt+{index + 1}"))
        rail.addWidget(self.nav)
        rail.addWidget(label("FIELD WORKSPACE", "eyebrow"))
        rail.addWidget(label("Evidence first.\nExplain every conclusion.", "muted"))
        rail.addSpacing(12)
        rail.addWidget(label(f"Desktop + CLI\nv{__version__}", "muted"))
        self.pages = QStackedWidget()
        row.addWidget(side)
        workspace = QVBoxLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(0)
        self.compact_navigation = QComboBox()
        self.compact_navigation.addItems(sections)
        self.compact_navigation.setAccessibleName("Choose workspace page")
        self.compact_navigation.currentIndexChanged.connect(self.nav.setCurrentRow)
        self.nav.currentRowChanged.connect(self.compact_navigation.setCurrentIndex)
        workspace.addWidget(self.compact_navigation)
        self.task_banner = QFrame()
        self.task_banner.setObjectName("taskBanner")
        task_layout = QHBoxLayout(self.task_banner)
        task_layout.setContentsMargins(20, 10, 20, 10)
        self.task_status = label("", "muted")
        self.task_status.setAccessibleName("Current task progress")
        task_layout.addWidget(self.task_status, 1)
        self.task_cancel = button("Cancel task", self.cancel_task)
        task_layout.addWidget(self.task_cancel)
        self.task_banner.hide()
        workspace.addWidget(self.task_banner)
        workspace.addWidget(self.pages, 1)
        row.addLayout(workspace, 1)
        self.setCentralWidget(root)
        self.build_overview()
        self.build_diagnostics()
        self.build_history()
        self.build_tools()
        self.build_settings()
        from .survey_ui import SurveyPage
        self.survey_page = SurveyPage(self)
        self.add_scroll_page(self.survey_page)
        for spin in self.findChildren(QSpinBox):
            spin.lineEdit().setStyleSheet("padding: 0; border: none; background: transparent;")
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)
        self.update_navigation()
        self.find_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.find_shortcut.activated.connect(self.focus_search)
        self.statusBar().showMessage("Ready • Choose a workflow or explore the synthetic demo")
        self.statusBar().messageChanged.connect(self.update_task_status)
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
        self.add_scroll_page(widget)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_navigation()

    def update_navigation(self):
        if hasattr(self, "compact_navigation"):
            compact = self.width() < 1050
            self.sidebar.setVisible(not compact)
            self.compact_navigation.setVisible(compact)

    def focus_search(self):
        if self.nav.currentRow() == 1:
            self.tabs.setCurrentIndex(4)
            field = self.metric_search
        else:
            self.nav.setCurrentRow(2)
            field = self.history_search
        field.setFocus()
        field.selectAll()

    def add_scroll_page(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        self.pages.addWidget(scroll)

    def compact_diagnostics(self, index):
        compact = index in (6, 8)
        self.show_setup.blockSignals(True)
        self.show_setup.setChecked(not compact and not bool(self.payload))
        self.show_setup.blockSignals(False)
        self.toggle_setup(self.show_setup.isChecked())
        for panel in self.diagnostic_heading + [self.stats_panel]:
            panel.setVisible(not compact)

    def toggle_setup(self, checked):
        for panel in self.setup_panels:
            panel.setVisible(checked)

    def expand_spectrum(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Veilbreaker • Spectrum inspector")
        dialog.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        layout = QVBoxLayout(dialog)
        view = SpectrumView()
        view.set_band_plan(self.spectrum.band_plan, self.spectrum.show_bands)
        readout = label("", "muted")
        view.inspected.connect(readout.setText)
        actions = QHBoxLayout()
        actions.addWidget(button("Zoom in", lambda: view.zoom(0.75)))
        actions.addWidget(button("Zoom out", lambda: view.zoom(1.333333)))
        actions.addWidget(button("Reset view", view.reset_view))
        actions.addStretch()
        actions.addWidget(button("Close", dialog.close))
        layout.addLayout(actions)
        layout.addWidget(view, 1)
        layout.addWidget(readout)
        view.load_sweep(self.sweep_selector.currentData())
        self.spectrum_dialog = dialog
        dialog.showMaximized()

    def retry_diagnostic(self):
        if getattr(self, "last_run_request", None):
            self.start_job("run", **self.last_run_request)

    def build_diagnostics(self):
        widget, layout = page("Diagnostic workspace", "Collect a snapshot, review competing explanations, and preserve the evidence.")
        self.diagnostic_heading = [layout.itemAt(0).widget(), layout.itemAt(1).widget()]
        page_layout = layout
        self.show_setup = QCheckBox("Configure next run")
        self.show_setup.setChecked(True)
        self.show_setup.toggled.connect(self.toggle_setup)
        page_layout.addWidget(self.show_setup)
        self.run_setup_card = QFrame()
        self.run_setup_card.setObjectName("card")
        page_layout.addWidget(self.run_setup_card)
        layout = QVBoxLayout(self.run_setup_card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        self.setup_panels = [self.run_setup_card]
        controls = QHBoxLayout()
        self.site = QLineEdit(self.config.site_id)
        self.site.setAccessibleName("Site identifier")
        self.site.setPlaceholderText("Site identifier")
        self.scenario = QComboBox()
        for key in sorted(core.SCENARIO_OVERRIDES):
            self.scenario.addItem(SCENARIOS[key][0], key)
        self.scenario.setCurrentIndex(self.scenario.findData(self.config.scenario))
        self.scenario.setAccessibleName("Diagnostic scenario")
        controls.addWidget(label("Site"))
        controls.addWidget(self.site, 1)
        controls.addWidget(label("Scenario"))
        controls.addWidget(self.scenario, 1)
        setup = QWidget()
        setup.setObjectName("surfaceContainer")
        setup.setLayout(controls)
        layout.addWidget(setup)
        self.scenario_description = label(scenario_help(self.scenario.currentData()), "muted")
        self.scenario_description.setWordWrap(True)
        self.scenario.currentIndexChanged.connect(lambda: self.scenario_description.setText(scenario_help(self.scenario.currentData())))
        scenario_actions = QHBoxLayout()
        self.scenario_hint = label(SCENARIOS.get(self.scenario.currentData(), ("", ""))[1].split(" Suggested tests:")[0], "muted")
        self.scenario.currentIndexChanged.connect(lambda: self.scenario_hint.setText(SCENARIOS.get(self.scenario.currentData(), ("", ""))[1].split(" Suggested tests:")[0]))
        scenario_actions.addWidget(self.scenario_hint, 1)
        self.scenario_help_toggle = QPushButton("Scenario details")
        self.scenario_help_toggle.setCheckable(True)
        self.scenario_help_toggle.toggled.connect(self.scenario_description.setVisible)
        scenario_actions.addWidget(self.scenario_help_toggle)
        layout.addLayout(scenario_actions)
        layout.addWidget(self.scenario_description)
        self.scenario_description.hide()
        options = FlowLayout()
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
        options_panel = QWidget()
        options_panel.setObjectName("surfaceContainer")
        options_panel.setLayout(options)
        layout.addWidget(options_panel)
        self.run_plan = label("", "muted")
        layout.addWidget(self.run_plan)
        for check in self.flags.values():
            check.toggled.connect(self.update_run_plan)
        self.update_run_plan()
        actions = FlowLayout()
        self.run_button = button("Run diagnostic", self.run_diagnostic, True)
        self.import_button = button("Import metrics…", self.import_metrics)
        self.cancel_button = button("Cancel task", self.cancel_task)
        self.cancel_button.setEnabled(False)
        self.cancel_button.hide()
        self.export_button = button("Save evidence ZIP…", self.export_evidence)
        self.export_button.setEnabled(False)
        actions.addWidget(self.run_button)
        actions.addWidget(button("Check selected test readiness", self.check_selected_readiness))
        actions.addWidget(self.import_button)
        actions.addWidget(self.cancel_button)
        self.retry_button = button("Retry after reconnect", self.retry_diagnostic)
        self.retry_button.setToolTip("Start a new diagnostic using the previous request and rediscover hardware. Requested active tests will run again.")
        self.retry_button.setEnabled(False)
        self.retry_button.hide()
        actions.addWidget(self.retry_button)
        action_panel = QWidget()
        action_panel.setObjectName("surfaceContainer")
        action_panel.setLayout(actions)
        layout.addWidget(action_panel)
        layout = page_layout
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.result_caption = label("No assessment yet • Run a diagnostic or import a JSON metric snapshot.", "muted")
        result_actions = QHBoxLayout()
        result_actions.addWidget(self.result_caption, 1)
        self.view_report_button = button("View report", self.view_current_report)
        self.view_report_button.setEnabled(False)
        result_actions.addWidget(self.view_report_button)
        result_actions.addWidget(self.export_button)
        layout.addLayout(result_actions)
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
        stats_panel = QWidget()
        stats_panel.setLayout(stats)
        self.stats_panel = stats_panel
        layout.addWidget(stats_panel)
        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(320)
        self.tabs.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.tabBar().setExpanding(False)
        self.summary = QTextBrowser()
        self.summary.setOpenExternalLinks(False)
        self.summary.setPlainText("Your evidence summary will appear here. Missing measurements remain unknown.")
        self.hypotheses = table(["Likely cause", "Score", "Status", "Supporting / contradicting evidence"])
        self.findings = table(["Severity", "Finding", "Observation", "Recommended action"])
        self.next_tests = table(["Priority", "Next test", "Why", "Action"])
        followup_panel = QWidget()
        followup_layout = QVBoxLayout(followup_panel)
        followup_layout.addWidget(self.next_tests, 1)
        self.followup_details = QPlainTextEdit()
        self.followup_details.setReadOnly(True)
        self.followup_details.setAccessibleName("Selected follow-up guidance")
        self.followup_details.setPlaceholderText("Select a recommendation to review its procedure, requirements and supported setup.")
        followup_layout.addWidget(self.followup_details, 1)
        followup_actions = FlowLayout()
        self.prepare_followup_button = button("Prepare supported test options", self.prepare_followup)
        self.prepare_followup_button.setEnabled(False)
        followup_actions.addWidget(self.prepare_followup_button)
        followup_actions.addWidget(button("Open settings", lambda: self.nav.setCurrentRow(4)))
        followup_actions.addWidget(button("Tools & readiness", lambda: self.nav.setCurrentRow(3)))
        followup_layout.addLayout(followup_actions)
        self.next_tests.itemSelectionChanged.connect(self.select_followup)

        self.metrics = table(["Metric", "Value", "Sources (last source supplies value)"])
        metrics_panel = QWidget()
        metrics_layout = QVBoxLayout(metrics_panel)
        self.metric_search = QLineEdit()
        self.metric_search.setPlaceholderText("Filter metrics by name, value or collector · Ctrl+F")
        self.metric_search.setAccessibleName("Filter captured metrics")
        self.metric_search.setClearButtonEnabled(True)
        self.metric_search.textChanged.connect(self.filter_metrics)
        self.metric_count = label("No measurements yet.", "muted")
        metrics_layout.addWidget(self.metric_search)
        metrics_layout.addWidget(self.metric_count)
        metrics_layout.addWidget(self.metrics, 1)
        self.collection_table = table(["Collector", "Requested", "Outcome", "Seconds", "Missing measurements", "Notes"])
        self.notes = QPlainTextEdit()
        self.notes.setReadOnly(True)
        self.spectrum = SpectrumView()
        from .bandplan import load_plan
        try:
            self.spectrum.set_band_plan(load_plan(self.config.root / 'band-plan.json'))
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            QTimer.singleShot(0, lambda message=str(exc): QMessageBox.warning(self, 'Using built-in U.S. reference', 'Saved band plan could not be loaded: ' + message))
        spectrum_panel = QWidget()
        spectrum_layout = QVBoxLayout(spectrum_panel)
        self.sweep_selector = QComboBox()
        self.sweep_selector.setAccessibleName("Captured spectrum range")
        self.sweep_selector.currentIndexChanged.connect(self.select_sweep)
        spectrum_actions = FlowLayout()
        range_actions = QHBoxLayout()
        range_actions.addWidget(self.sweep_selector, 1)
        range_actions.addWidget(button("Compare saved capture…", self.compare_spectrum))
        spectrum_layout.addLayout(range_actions)
        band_actions = FlowLayout()
        self.band_overlay = QCheckBox("Show band reference")
        self.band_overlay.setChecked(True)
        self.band_overlay.toggled.connect(lambda checked: self.spectrum.set_band_plan(self.spectrum.band_plan, checked))
        band_actions.addWidget(self.band_overlay)
        band_actions.addWidget(button("Band legend / import…", self.open_band_plan))

        spectrum_actions.addWidget(button("+", lambda: self.spectrum.zoom(0.75)))
        spectrum_actions.addWidget(button("−", lambda: self.spectrum.zoom(1.333333)))
        spectrum_actions.addWidget(button("Reset", self.spectrum.reset_view))
        spectrum_actions.addWidget(button("Expand chart", self.expand_spectrum))
        while spectrum_actions.count():
            band_actions.addWidget(spectrum_actions.takeAt(0).widget())
        spectrum_layout.addLayout(band_actions)
        spectrum_layout.addWidget(self.spectrum, 1)
        self.spectrum_readout = label("", "muted")
        self.spectrum.inspected.connect(self.spectrum_readout.setText)
        spectrum_layout.addWidget(self.spectrum_readout)
        for name, panel in [("Summary", self.summary), ("Hypotheses", self.hypotheses),
                            ("Findings", self.findings), ("Next tests", followup_panel),
                            ("Metrics", metrics_panel), ("Collector notes", self.notes), ("Spectrum", spectrum_panel), ("Collection", self.collection_table)]:
            self.tabs.addTab(panel, name)
        sdr_panel = QWidget()
        sdr_layout = QVBoxLayout(sdr_panel)
        from .report_viewer import OfflineReportBrowser
        self.sdr_report_view = OfflineReportBrowser()
        self.sdr_report_view.setOpenLinks(False)
        self.sdr_report_view.anchorClicked.connect(self.inspect_sdr_bin)
        self.sdr_report_view.setHtml("<p>No SDR capture evidence in this run.</p>")
        self.report_details = QCheckBox("Show technical details and sources")
        self.report_details.toggled.connect(self.render_sdr_report)
        sdr_layout.addWidget(self.report_details)
        sdr_layout.addWidget(self.sdr_report_view, 1)
        export_actions = FlowLayout()
        export_actions.addWidget(button("Export SDR HTML…", lambda: self.export_sdr_report("html")))
        export_actions.addWidget(button("Export SDR JSON…", lambda: self.export_sdr_report("json")))
        export_actions.addWidget(button("Export band CSV…", lambda: self.export_sdr_report("csv")))
        sdr_layout.addLayout(export_actions)
        self.tabs.addTab(sdr_panel, "SDR report")
        self.tabs.currentChanged.connect(self.compact_diagnostics)
        layout.addWidget(self.tabs, 1)
        self.add_scroll_page(widget)

    def build_history(self):
        widget, layout = page("Run history", "Reopen saved evidence or compare two snapshots from the same investigation.")
        actions = FlowLayout()
        self.history_offset = 0
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Search all runs: site, note, run ID, scenario or UTC date")
        self.history_search.setAccessibleName("Search saved runs")
        self.history_search.setClearButtonEnabled(True)
        layout.addWidget(self.history_search)
        self.history_timer = QTimer(self)
        self.history_timer.setSingleShot(True)
        self.history_timer.setInterval(250)
        self.history_timer.timeout.connect(self.search_history)
        self.history_search.textChanged.connect(lambda: self.history_timer.start())
        self.history_search.returnPressed.connect(self.search_history)
        actions.addWidget(button("Refresh", self.refresh_history))
        self.history_open = button("Open selected run", self.open_history, True)
        self.history_report = button("View report", self.view_history_report)
        self.history_compare = button("Compare to previous", self.compare_history)
        actions.addWidget(self.history_open)
        actions.addWidget(self.history_report)
        actions.addWidget(button("Open report…", self.open_report_file))
        actions.addWidget(self.history_compare)
        from .case_ui import show_cases
        actions.addWidget(button("Confirmed cases…", lambda: show_cases(self)))
        layout.addLayout(actions)
        self.history = table(["Run", "UTC", "Site", "Scenario", "Note"])
        self.history.itemActivated.connect(lambda *_: self.open_history())
        self.history.itemSelectionChanged.connect(self.update_history_actions)
        layout.addWidget(self.history, 2)
        self.history_empty = label("", "muted")
        layout.addWidget(self.history_empty)
        paging = QHBoxLayout()
        self.history_previous = button("Newer page", lambda: self.page_history(-200))
        self.history_next = button("Older page", lambda: self.page_history(200))
        self.history_count = label("", "muted")
        paging.addWidget(self.history_previous)
        paging.addWidget(self.history_next)
        paging.addWidget(self.history_count)
        paging.addStretch()
        layout.addLayout(paging)
        self.comparison = QPlainTextEdit()
        self.comparison.setReadOnly(True)
        self.comparison.setPlaceholderText("Comparison uses the preceding saved run at the same site and scenario. Numeric deltas describe change; they do not automatically mean improvement.")
        layout.addWidget(self.comparison, 1)
        self.add_scroll_page(widget)

    def build_tools(self):
        widget, layout = page("Tools & readiness", "Inspect local dependencies and supported modem families before field work.")
        actions = FlowLayout()
        for title, action in [("Check readiness", "doctor"), ("List serial ports", "ports"),
                              ("Modem driver matrix", "drivers"), ("Engine self-test", "selftest")]:
            actions.addWidget(button(title, lambda checked=False, a=action: self.start_job(a)))
        layout.addLayout(actions)
        layout.addWidget(button("Verify evidence ZIP…", self.verify_evidence))
        layout.addWidget(button("Recover interrupted captures", lambda: self.start_job("recover")))
        sdr_actions = FlowLayout()
        sdr_actions.addWidget(button("Discover HackRF", lambda: self.start_job("hackrf_info")))
        capture = button("Capture selected preset", self.capture_preset, True)
        self.capture_button = capture
        capture.setToolTip("Receive-only capture using the settings below. RF amplifier and antenna power stay off.")
        sdr_actions.addWidget(capture)
        sdr_actions.addWidget(label("Receive-only • RF amplifier and antenna power off", "muted"))
        layout.addLayout(sdr_actions)
        from .rf_workflow import PRESETS, BIN_WIDTHS
        preset_form = QFormLayout()
        self.rf_preset = QComboBox()
        self.rf_preset.addItems(PRESETS)
        self.rf_sweeps = QSpinBox()
        self.rf_sweeps.setRange(1, 20)
        self.rf_sweeps.setValue(3)
        self.rf_bins = QComboBox()
        for width in BIN_WIDTHS:
            self.rf_bins.addItem(f"{width // 1000} kHz", width)
        self.rf_bins.setCurrentIndex(3)
        self.rf_lna, self.rf_vga = QComboBox(), QComboBox()
        for value in range(0, 41, 8):
            self.rf_lna.addItem(f"{value} dB", value)
        for value in range(0, 63, 2):
            self.rf_vga.addItem(f"{value} dB", value)
        self.rf_lna.setCurrentIndex(2)
        self.rf_vga.setCurrentIndex(10)
        for title, control in [("Receive band", self.rf_preset), ("Sweep count", self.rf_sweeps),
                               ("Requested bin width", self.rf_bins), ("LNA gain", self.rf_lna), ("VGA gain", self.rf_vga)]:
            control.setAccessibleName(title)
            preset_form.addRow(title, control)
        layout.addLayout(preset_form)
        layout.addWidget(label("Smaller bins resolve finer frequency detail and produce more data. Record antenna and placement changes when comparing captures. These controls apply to Capture selected preset; diagnostic SDR sweeps use Settings.", "muted"))
        layout.addWidget(label("Readiness can query hardware enabled in Settings. Serial-port listing does not open ports. Additional CLI commands remain available for targeted modem, Starlink, SDR and path tests.", "muted"))
        layout.addWidget(button("Check selected diagnostic prerequisites", self.check_selected_readiness))
        self.readiness_caption = label("No selected-test check yet. Results are snapshots; recheck after changing settings or devices.", "muted")
        layout.addWidget(self.readiness_caption)
        self.readiness_table = table(["Prerequisite", "State", "Details / next action"])
        self.readiness_table.setMinimumHeight(200)
        layout.addWidget(self.readiness_table)
        layout.addWidget(button("Open settings", lambda: self.nav.setCurrentRow(4)))
        self.tool_output = QPlainTextEdit()
        self.tool_output.setReadOnly(True)
        self.tool_output.setPlaceholderText("Choose a check above. Missing optional hardware does not prevent offline analysis.")
        layout.addWidget(self.tool_output, 1)
        layout.addWidget(button("Cancel running task", self.cancel_task))
        self.add_scroll_page(widget)

    def verify_evidence(self):
        source, _ = QFileDialog.getOpenFileName(self, "Verify evidence bundle", "", "ZIP archive (*.zip)")
        if source:
            self.start_job("verify", input=source)

    def build_settings(self):
        widget, layout = page("Settings", "Configure targets, hardware and storage. Existing CLI configuration is supported.")
        self.settings_location = label("", "muted")
        layout.addWidget(self.settings_location)
        layout.addWidget(label("Connection settings apply to your next diagnostic. Saving never starts a test. Site and scenario are selected on Diagnostics; receive presets are in Tools.", "muted"))
        self.settings_tabs = QTabWidget()
        self.settings_tabs.setUsesScrollButtons(True)
        self.settings_tabs.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.settings_tabs.setMinimumHeight(355)
        layout.addWidget(self.settings_tabs, 1)
        network = QWidget()
        network_layout = QVBoxLayout(network)
        network_layout.setContentsMargins(18, 18, 18, 18)
        network_layout.setSpacing(16)
        network_layout.addWidget(label("Network test targets", "section"))
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.network_fields = {}
        for key, title in (("public_ping_target", "Ping target"), ("dns_test_host", "DNS test host"), ("iperf3_server", "Throughput server (optional)")):
            field = QLineEdit(getattr(self.config, key) or "")
            field.setAccessibleName(title)
            field.setPlaceholderText("Hostname or IP address")
            self.network_fields[key] = field
            form.addRow(title, field)
        self.throughput_port = QSpinBox()
        self.throughput_port.setRange(1, 65535)
        self.throughput_port.setValue(self.config.iperf3_port)
        self.throughput_port.setAccessibleName("Throughput server port")
        form.addRow("Throughput port", self.throughput_port)
        network_layout.addLayout(form)
        network_layout.addWidget(label("Use hostnames or IP addresses without URL prefixes. Leave the throughput server blank to disable its configuration.", "muted"))
        network_layout.addStretch()
        self.settings_tabs.addTab(network, "Network")
        from .hardware_settings import HardwareSettings
        self.hardware_settings = HardwareSettings(self.settings_tabs, self.config)
        self.settings_feedback = label("All connection settings are saved together.", "muted")
        layout.addWidget(self.settings_feedback)
        actions = FlowLayout()
        self.save_connections = button("Save connection settings", self.save_network_settings, True)
        actions.addWidget(self.save_connections)
        actions.addWidget(button("Reload saved settings", self.reload_settings))
        actions.addWidget(button("Open data folder", self.open_data_folder))
        layout.addLayout(actions)
        advanced = QWidget()
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.setContentsMargins(18, 18, 18, 18)
        self.settings_tabs.addTab(advanced, "Advanced JSON")
        advanced_layout.addWidget(label("Adapter commands run as your user when their collector is used. Save connection edits before editing JSON. Each save protects unsaved edits in the other editor.", "muted"))
        advanced_layout.addWidget(button("Save advanced JSON", self.save_settings))
        self.config_editor = QPlainTextEdit(json.dumps(self.config.to_dict(), indent=2))
        self.config_editor.setAccessibleName("Configuration JSON")
        self.config_editor.setMinimumHeight(180)
        advanced_layout.addWidget(self.config_editor)
        self.sync_network_settings()
        for field in self.network_fields.values():
            field.textChanged.connect(self.update_settings_feedback)
        self.throughput_port.valueChanged.connect(self.update_settings_feedback)
        for field in self.hardware_settings.fields.values():
            signal = field.currentIndexChanged if isinstance(field, QComboBox) else field.valueChanged if isinstance(field, QSpinBox) else field.textChanged
            signal.connect(self.update_settings_feedback)
        self.config_editor.textChanged.connect(self.update_settings_feedback)
        self.add_scroll_page(widget)

    def effective_config(self):
        cfg = core.AppConfig.from_dict(self.config.to_dict())
        cfg.site_id = self.site.text().strip() or "default"
        cfg.scenario = self.scenario.currentData()
        return cfg

    def selected_followup(self):
        index = self.next_tests.currentRow()
        tests = (self.payload or {}).get('report', {}).get('next_tests', [])
        return tests[index] if self.next_tests.selectedItems() and 0 <= index < len(tests) else None

    def select_followup(self):
        from .followup import guidance, details
        test = self.selected_followup()
        self.followup_details.setPlainText(details(test) if test else '')
        self.prepare_followup_button.setEnabled(bool(test and guidance(test.get('test_id', ''))[0]) and self.process is None)

    def prepare_followup(self):
        from .followup import guidance
        test = self.selected_followup()
        if not test or self.process is not None:
            return
        flags = guidance(test.get('test_id', ''))[0]
        if not flags:
            return
        for key, control in self.flags.items():
            control.setChecked(key in flags)
        self.show_setup.setChecked(True)
        self.pages.widget(1).ensureWidgetVisible(self.show_setup)
        self.statusBar().showMessage('Follow-up options prepared. Review site, scenario, settings and targets, then press Run. No acquisition started.')

    def check_selected_readiness(self):
        if self.process is not None:
            self.statusBar().showMessage("Wait for the current task or cancel it before checking readiness.")
            return
        self.nav.setCurrentRow(3)
        self.readiness_caption.setText("Checking selected prerequisites… No acquisition or connectivity tests will run.")
        self.readiness_table.setRowCount(0)
        self.start_job('readiness', options={key: control.isChecked() for key, control in self.flags.items()})

    def run_diagnostic(self):
        options = {key: check.isChecked() for key, check in self.flags.items()}
        options["active"] = options["active"] or options["guided"]
        if options["throughput"] and not self.config.iperf3_server:
            self.error("Set iperf3_server in Settings before enabling throughput.")
            return
        self.start_job("run", options=options)

    def update_run_plan(self):
        parts = ["Host and link snapshot"]
        active = self.flags["active"].isChecked() or self.flags["guided"].isChecked()
        if active:
            parts.append(f"ping {self.config.public_ping_target} and DNS {self.config.dns_test_host}")
        for key, title in (("cellular", "read-only modem telemetry"), ("starlink", "Starlink telemetry"), ("sdr", "receive-only SDR sweep")):
            if self.flags[key].isChecked():
                parts.append(title)
        if self.flags["throughput"].isChecked():
            parts.append(f"throughput to {self.config.iperf3_server or 'an unconfigured server (set it in Settings)'}")
        if self.flags["guided"].isChecked():
            parts.append("one guided follow-up cycle")
        self.run_plan.setText("This run: " + "; ".join(parts) + ".")

    def selected_capture_settings(self):
        return {"preset": self.rf_preset.currentText(), "sweeps": self.rf_sweeps.value(),
                "bin_width_hz": self.rf_bins.currentData(), "lna_gain_db": self.rf_lna.currentData(),
                "vga_gain_db": self.rf_vga.currentData()}

    def capture_preset(self):
        self.start_job("run", options={"sdr": True}, capture_settings=self.selected_capture_settings())

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
        if action == "run":
            self.last_run_request = json.loads(json.dumps(extra))
        preset = extra.pop("capture_settings", None)
        if preset:
            from .rf_workflow import apply_preset
            apply_preset(cfg, **preset)
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
        self.progress_buffer = b""
        process.readyReadStandardOutput.connect(self.read_progress)
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

    def read_progress(self):
        if self.process is None:
            return
        self.progress_buffer += bytes(self.process.readAllStandardOutput())
        while b"\n" in self.progress_buffer:
            line, self.progress_buffer = self.progress_buffer.split(b"\n", 1)
            try:
                event = json.loads(line)
                if isinstance(event, dict) and event.get("event") == "collection" and not self.cancelled:
                    self.statusBar().showMessage(f"{event['source']}: {event['status'].replace('_', ' ')}")
            except (ValueError, KeyError, AttributeError):
                pass
        self.progress_buffer = self.progress_buffer[-65536:]

    def update_task_status(self, message):
        if self.process is not None:
            self.task_status.setText(message)

    def set_busy(self, busy):
        from .followup import guidance
        test = self.selected_followup()
        self.prepare_followup_button.setEnabled(not busy and bool(test and guidance(test.get("test_id", ""))[0]))
        self.task_banner.setVisible(busy)
        self.task_cancel.setEnabled(busy)
        self.site.setEnabled(not busy)
        self.scenario.setEnabled(not busy)
        for control in self.flags.values():
            control.setEnabled(not busy)
        self.run_button.setEnabled(not busy)
        self.import_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.cancel_button.setVisible(busy)
        self.retry_button.setEnabled(not busy and bool(getattr(self, "last_run_request", None)))
        self.retry_button.setVisible(not busy and bool(getattr(self, "last_run_request", None)))
        self.progress.setVisible(busy)
        self.pages.widget(4).setEnabled(not busy)
        self.survey_page.set_busy(busy)
        for control in (self.capture_button, self.rf_preset, self.rf_sweeps, self.rf_bins, self.rf_lna, self.rf_vga):
            control.setEnabled(not busy)

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
                self.statusBar().showMessage("Task cancelled. Recover interrupted captures from Tools to reopen saved partial evidence.")
            elif result_path.exists():
                obj = json.loads(result_path.read_text(encoding="utf-8"))
                if not obj["ok"]:
                    self.error(obj["error"])
                elif "readiness" in obj["result"]:
                    check = obj['result']['readiness']
                    fill(self.readiness_table, [[r['item'], r['state'], r['detail']] for r in check['rows']])
                    self.readiness_caption.setText(f"Snapshot checked {check['checked_utc']} • Site: {check['site_id']} • Scenario: {check['scenario']} • Selected: {', '.join(check['selected']) or 'passive only'}. Recheck after changing settings or devices.")
                    self.nav.setCurrentRow(3)
                    self.statusBar().showMessage('Prerequisite check complete. Review missing and untested items; acquisition has not started.')
                elif "survey" in obj["result"]:
                    self.survey_page.show_session(obj["result"]["survey"], obj["result"]["survey_path"])
                    self.nav.setCurrentRow(5)
                    self.statusBar().showMessage("Survey " + obj["result"]["survey"]["status"] + " • Evidence saved locally")
                elif "report" in obj["result"]:
                    self.display_payload(obj["result"])
                    self.nav.setCurrentRow(1)
                    if obj["result"].get("sweeps"):
                        self.tabs.setCurrentIndex(6)
                    self.statusBar().showMessage("Partial collection • Review Collection tab • Evidence saved locally"
                        if obj["result"].get("collection", {}).get("status") in ("partial", "interrupted") else "Diagnostic complete • Evidence saved locally")
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
            self.survey_page.refresh()

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
        self.task_cancel.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.statusBar().showMessage("Cancelling task… Partial evidence can be recovered from Tools.")
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
        self.next_tests.clearSelection()
        self.next_tests.setCurrentCell(-1, -1)
        self.select_followup()

        from .acquisition import collection_summary
        collection = payload.get("collection", {})
        sources = collection.get("metric_sources", {})
        self.summary.setPlainText(collection_summary(collection) + "\n\n" + self.summary.toPlainText())
        fill(self.collection_table, [[r["source"], "Yes" if r["required"] else "Optional", r["status"],
                                     r["duration_s"], "\n".join(r.get("missing_measurements", [])) or "None recorded", "\n".join(r["notes"])]
                                    for r in collection.get("collectors", [])])
        fill(self.metrics, [[k, json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v,
                             " → ".join(sources.get(k, [])) or "Not recorded"] for k, v in sorted(payload["metrics"].items())])
        self.filter_metrics()
        self.notes.setPlainText("\n".join(payload.get("notes", [])) or "No collector notes recorded.")
        self.export_button.setEnabled(bool(payload.get("evidence_zip")))
        self.view_report_button.setEnabled(bool(payload.get("evidence_zip") or payload.get("artifact_dir")))
        self.sweep_selector.blockSignals(True)
        self.sweep_selector.clear()
        for sweep in payload.get("sweeps", []):
            self.sweep_selector.addItem(sweep["label"], sweep)
        self.sweep_selector.blockSignals(False)
        self.select_sweep()
        self.refresh_sdr_report()
        self.compact_diagnostics(self.tabs.currentIndex())

    def filter_metrics(self):
        query = self.metric_search.text().strip().casefold()
        visible = 0
        for row in range(self.metrics.rowCount()):
            matches = any(query in self.metrics.item(row, column).text().casefold()
                          for column in range(self.metrics.columnCount()))
            self.metrics.setRowHidden(row, not matches)
            visible += matches
        total = self.metrics.rowCount()
        self.metric_count.setText(f"{visible} of {total} measurements" if visible or not query
                                  else "No matching measurements. Clear the filter to see all values.")

    def compare_spectrum(self):
        from .rf_workflow import compare_sweeps
        after = self.sweep_selector.currentData()
        if not after or not self.payload:
            self.error("Open a saved spectrum before comparing captures.")
            return
        choices = []
        candidates = self.history_rows
        if self.config.db_path.exists():
            store = core.VeilbreakerStore(self.config.db_path)
            try:
                candidates = [dict(r) for r in store.list_runs(site_id=self.payload.get("site_id"), limit=200)]
            finally:
                store.close()
        for row in candidates:
            if row["run_id"] == self.payload["run_id"] or row["site_id"] != self.payload.get("site_id"):
                continue
            if not row.get("artifact_dir"):
                continue
            try:
                folder = Path(row["artifact_dir"])
                collection_file = folder / "collection.json"
                if collection_file.exists() and json.loads(collection_file.read_text(encoding="utf-8")).get("status") == "interrupted":
                    continue
                summaries = json.loads((folder / "sdr_summaries.json").read_text(encoding="utf-8"))
                for sweep in summaries:
                    if (sweep["min_mhz"], sweep["max_mhz"]) == (after["min_mhz"], after["max_mhz"]):
                        choices.append((row, sweep))
            except (OSError, ValueError, KeyError):
                continue
        if not choices:
            self.error("No other saved capture at this site covers the same frequency range. Repeat the preset after your change, then compare.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Veilbreaker • Before / after spectrum")
        layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        body = QVBoxLayout(content)
        selector = QComboBox()
        selector.setAccessibleName("Before capture")
        for row, sweep in choices:
            selector.addItem(f"{row['ts_utc']} • {row['run_id']} • {sweep['label']}")
        body.addWidget(label(f"After: {self.payload['run_id']} • {after['label']}"))
        body.addWidget(label("Choose the before capture. Compare only when antenna, cable and placement are consistent, or their change is your experiment.", "muted"))
        body.addWidget(selector)
        output = label("", "muted")
        body.addWidget(output)
        view = SpectrumView()
        view.set_band_plan(self.spectrum.band_plan, self.spectrum.show_bands)
        body.addWidget(view, 1)
        readout = label("", "muted")
        view.inspected.connect(readout.setText)
        body.addWidget(readout)
        result = {}
        def refresh():
            result.clear()
            view.load_sweep(after)
            row, before = choices[selector.currentIndex()]
            try:
                if self.payload.get("collection", {}).get("status") == "interrupted":
                    raise ValueError("The current capture is interrupted. Repeat it before comparing.")
                comparison = compare_sweeps(before, after, json.loads(row["metrics_json"]).get("sdr_serial"), self.payload["metrics"].get("sdr_serial"))
                comparison.update(before_run_id=row["run_id"], after_run_id=self.payload["run_id"], site_id=row["site_id"])
                result.update(comparison)
                view.set_reference(before)
                peak = result["largest_increase"]
                output.setText(f"{result['bin_count']} aligned bins • Median change {result['median_delta_db']:+.2f} dB • Largest increase {peak['delta_db']:+.2f} dB at {peak['frequency_mhz']:.3f} MHz. Relative power, not calibrated dBm or proof of interference.")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                output.setText(f"Comparison unavailable: {exc}")
            save.setEnabled(bool(result))
        def export():
            target, _ = QFileDialog.getSaveFileName(dialog, "Save spectrum comparison", "spectrum-comparison.json", "JSON (*.json)")
            if target:
                try:
                    Path(target).write_text(json.dumps(result, indent=2), encoding="utf-8")
                except OSError as exc:
                    self.error(str(exc))
        controls = QHBoxLayout()
        controls.addWidget(button("Zoom in", lambda: view.zoom(0.75)))
        controls.addWidget(button("Zoom out", lambda: view.zoom(1.333333)))
        controls.addWidget(button("Reset", view.reset_view))
        save = button("Save comparison…", export)
        controls.addWidget(save)
        controls.addWidget(button("Close", dialog.close))
        body.addLayout(controls)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        selector.currentIndexChanged.connect(refresh)
        refresh()
        self.comparison_dialog = dialog
        dialog.showMaximized()

    def select_sweep(self, *_):
        self.spectrum.load_sweep(self.sweep_selector.currentData())

    def open_band_plan(self):
        from .bandplan_ui import BandPlanDialog
        self.band_plan_dialog = BandPlanDialog(self)
        self.band_plan_dialog.show()

    def apply_band_plan(self, plan):
        from .bandplan import validate_plan
        from .recovery import atomic_json
        plan = validate_plan(plan)
        atomic_json(self.config.root / 'band-plan.json', plan)
        self.spectrum.set_band_plan(plan, self.band_overlay.isChecked())
        for dialog_name in ('spectrum_dialog', 'comparison_dialog'):
            dialog = getattr(self, dialog_name, None)
            if dialog:
                for view in dialog.findChildren(SpectrumView):
                    view.set_band_plan(plan, self.band_overlay.isChecked())
        self.refresh_sdr_report()

    def refresh_sdr_report(self):
        from .sdr_report import build_sdr_report, report_html
        payload = self.payload or {}
        metadata = {k: payload[k] for k in ('run_id', 'site_id', 'scenario', 'timestamp', 'collection') if k in payload}
        self.sdr_report_data = build_sdr_report(payload.get('sweeps', []), metadata, self.spectrum.band_plan)
        self.render_sdr_report()

    def render_sdr_report(self, *_):
        from .sdr_report import report_html
        if not hasattr(self, 'sdr_report_data'):
            return
        self.sdr_report_view.setHtml(report_html(self.sdr_report_data, interactive=True, technical=self.report_details.isChecked()))

    def inspect_sdr_bin(self, url):
        """Navigate only to a bin from the current report; never dispatch external links."""
        parts = url.toString().split(':')
        if len(parts) != 3 or parts[0] not in ('sdr-bin', 'sdr-band'):
            return
        try:
            range_index, rank = int(parts[1]), int(parts[2])
            if range_index < 0 or rank < 0 or range_index >= self.sweep_selector.count():
                return
            if parts[0] == 'sdr-band':
                band = self.sdr_report_data['ranges'][range_index]['band_summaries'][rank]
                self.sweep_selector.setCurrentIndex(range_index)
                if self.spectrum.points:
                    self.spectrum.set_bounds(band['inspected_min_mhz'], band['inspected_max_mhz'])
                    self.tabs.setCurrentIndex(6)
                return
            point = self.sdr_report_data['ranges'][range_index]['strongest_bins'][rank]
        except (ValueError, IndexError, KeyError, AttributeError):
            return
        self.sweep_selector.setCurrentIndex(range_index)
        view = self.spectrum
        if not view.points:
            return
        frequency = point['frequency_mhz']
        low, high = view.full_bounds
        span = max((high-low)*0.05, (high-low)/len(view.points)*4)
        view.set_bounds(frequency-span/2, frequency+span/2)
        view.cursor = min(view.points, key=lambda sample: abs(sample[0]-frequency))
        view.inspected.emit(f"{frequency:.3f} MHz • Maximum {point['maximum_db']:.1f} relative dB • Median {point['median_db']:.1f} relative dB • Reference: " + ('; '.join(point['expected_uses']) or 'No reference entry'))
        self.tabs.setCurrentIndex(6)
        view.update()

    def export_sdr_report(self, format):
        from .sdr_report import report_html
        self.refresh_sdr_report()
        path, _ = QFileDialog.getSaveFileName(self, 'Export SDR diagnostic report', f'sdr-report.{format}', f'{format.upper()} (*.{format})')
        if not path:
            return
        try:
            target = Path(path)
            if target.suffix.lower() != '.' + format:
                target = target.with_suffix('.' + format)
            if format == 'csv':
                from .band_summary import band_csv
                content = band_csv(self.sdr_report_data)
            else:
                content = report_html(self.sdr_report_data) if format == 'html' else json.dumps(self.sdr_report_data, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
            target.write_text(content, encoding='utf-8', newline='')
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'SDR report export failed', str(exc))

    def search_history(self):
        self.history_timer.stop()
        self.history_offset = 0
        self.refresh_history()

    def page_history(self, change):
        self.history_offset = max(0, self.history_offset + change)
        self.refresh_history()

    def refresh_history(self):
        total = 0
        if not self.config.db_path.exists():
            self.history_offset = 0
            self.history_rows = []
        else:
            try:
                store = core.VeilbreakerStore(self.config.db_path)
                try:
                    rows, total = store.search_runs(self.history_search.text(), offset=self.history_offset)
                    if self.history_offset and not rows:
                        self.history_offset = 0
                        rows, total = store.search_runs(self.history_search.text())
                    self.history_rows = [dict(r) for r in rows]
                finally:
                    store.close()
            except Exception as exc:
                self.statusBar().showMessage(f"Could not read history: {exc}")
                return
        self.history.clearSelection()
        self.history.setCurrentCell(-1, -1)
        self.comparison.clear()
        fill(self.history, [[r["run_id"], r["ts_utc"], r["site_id"], r["scenario"], r["note"] or ""] for r in self.history_rows])
        self.history_previous.setEnabled(self.history_offset > 0)
        self.history_next.setEnabled(self.history_offset + len(self.history_rows) < total)
        first = self.history_offset + 1 if self.history_rows else 0
        self.history_count.setText(f"{first}–{self.history_offset + len(self.history_rows)} of {total} matching runs")
        self.history_empty.setText("No matching runs. Try another site, note or date, or clear the search."
                                   if self.history_search.text().strip() else
                                   "No saved runs yet. Run a diagnostic or import metrics to build your history.")
        self.history_empty.setVisible(total == 0)
        self.update_history_actions()
        self.overview_status.setText(f"Saved evidence: {self.config.root}")

    def update_history_actions(self):
        selected = bool(self.history.selectedItems())
        self.history_open.setEnabled(selected)
        self.history_report.setEnabled(selected)
        self.history_compare.setEnabled(selected)

    def selected_run(self):
        row = self.history.currentRow()
        return self.history_rows[row] if self.history.selectedItems() and 0 <= row < len(self.history_rows) else None

    def open_history(self):
        row = self.selected_run()
        if not row:
            self.statusBar().showMessage("Select a saved run first.")
            return
        self.display_saved_run(row)

    def open_report_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open saved report', str(self.config.reports_dir), 'Reports and evidence (*.html *.htm *.zip)')
        if path:
            self.show_report_file(path)

    def show_report_file(self, path):
        from .report_viewer import ReportViewer
        try:
            viewer = ReportViewer(self, path)
        except (OSError, ValueError) as exc:
            self.error(f'Could not open report: {exc}')
            return
        self.report_viewer = viewer
        viewer.showMaximized()

    def view_history_report(self):
        row = self.selected_run()
        if not row:
            return
        pack = self.config.reports_dir / f"{row['run_id']}_evidence.zip"
        self.show_report_file(pack if pack.exists() else Path(row.get('artifact_dir') or self.config.artifacts_dir / row['run_id']))

    def view_current_report(self):
        if not self.payload:
            return
        pack = self.payload.get('evidence_zip')
        folder = self.payload.get('artifact_dir') or self.config.artifacts_dir / self.payload['run_id']
        self.show_report_file(Path(pack) if pack and Path(pack).exists() else Path(folder))

    def display_saved_run(self, row):
        pack = self.config.reports_dir / f"{row['run_id']}_evidence.zip"
        notes = Path(row["artifact_dir"]) / "collector_notes.txt" if row.get("artifact_dir") else None
        sweep_file = Path(row["artifact_dir"]) / "sdr_summaries.json" if row.get("artifact_dir") else None
        collection_file = Path(row["artifact_dir"]) / "collection.json" if row.get("artifact_dir") else None
        collection = {}
        if collection_file and collection_file.exists():
            try:
                collection = json.loads(collection_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.error("Saved collection details could not be read. The diagnostic report is still available.")
        self.display_payload({"collection": collection, "report": json.loads(row["report_json"]), "metrics": json.loads(row["metrics_json"]),
                              "run_id": row["run_id"], "site_id": row["site_id"],
                              "artifact_dir": row.get("artifact_dir"),
                              "notes": notes.read_text(encoding="utf-8", errors="replace").splitlines() if notes and notes.exists() else [],
                              "evidence_zip": str(pack) if pack.exists() else None,
                              "sweeps": json.loads(sweep_file.read_text(encoding="utf-8")) if sweep_file and sweep_file.exists() else []})
        self.nav.setCurrentRow(1)

    def compare_history(self):
        row = self.selected_run()
        if not row:
            self.statusBar().showMessage("Select a saved run first.")
            return
        store = core.VeilbreakerStore(self.config.db_path)
        try:
            previous = store.preceding_run(row)
            older = dict(previous) if previous else None
        finally:
            store.close()
        if not older:
            self.comparison.setPlainText("No preceding run for this site and scenario.")
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

    def sync_network_settings(self):
        for key, field in self.network_fields.items():
            field.setText(getattr(self.config, key) or "")
        self.throughput_port.setValue(self.config.iperf3_port)
        self.hardware_settings.sync(self.config)
        self.config_editor.setPlainText(json.dumps(self.config.to_dict(), indent=2))
        self.connection_snapshot = self.connection_values()
        self.settings_location.setText(f"Configuration: {core.default_config_path()}\nData: {self.config.root}")
        self.update_settings_feedback()

    def connection_values(self):
        return {"network": {key: field.text() for key, field in self.network_fields.items()},
                "port": self.throughput_port.value(), "hardware": self.hardware_settings.values()}

    def update_settings_feedback(self):
        if not hasattr(self, "connection_snapshot"):
            return
        dirty = self.connection_values() != self.connection_snapshot
        try:
            advanced_dirty = json.loads(self.config_editor.toPlainText()) != self.config.to_dict()
        except ValueError:
            advanced_dirty = True
        self.settings_feedback.setText("Unsaved connection changes · Save connection settings to apply."
                                       if dirty else "Connection settings match the saved configuration.")
        if advanced_dirty:
            self.settings_feedback.setText(self.settings_feedback.text() + " Advanced JSON has unsaved edits.")

    def save_network_settings(self):
        from .settings_form import apply_network_settings, apply_hardware_settings
        try:
            raw = json.loads(self.config_editor.toPlainText())
            if raw != self.config.to_dict():
                raise ValueError("Save or reload your advanced JSON edits before saving connection settings")
            cfg = apply_network_settings(raw, self.network_fields["public_ping_target"].text(),
                                         self.network_fields["dns_test_host"].text(),
                                         self.network_fields["iperf3_server"].text(), self.throughput_port.value())
            cfg = apply_hardware_settings(cfg.to_dict(), self.hardware_settings.values())
            self.persist_settings(cfg, update_context=False)
        except (OSError, ValueError, TypeError) as exc:
            self.error(f"Settings were not saved: {exc}")

    def persist_settings(self, cfg, update_context=True):
        from .recovery import atomic_json
        destination = core.default_config_path()
        destination.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(destination, cfg.to_dict())
        self.config = cfg
        self.sync_network_settings()
        if update_context:
            self.site.setText(cfg.site_id)
            self.scenario.setCurrentIndex(self.scenario.findData(cfg.scenario))
        self.update_run_plan()
        self.refresh_history()
        self.survey_page.refresh()
        self.statusBar().showMessage(f"Settings saved: {destination}")

    def save_settings(self):
        try:
            cfg = core.AppConfig.from_dict(json.loads(self.config_editor.toPlainText()))
            if self.connection_values() != self.connection_snapshot:
                raise ValueError("Save or reload your connection edits before saving advanced JSON")
            if not isinstance(cfg.data_dir, str) or not cfg.data_dir.strip():
                raise ValueError("data_dir must be a nonempty path")
            if cfg.scenario not in core.SCENARIO_OVERRIDES:
                raise ValueError("Unknown scenario")
            self.persist_settings(cfg)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            self.error(f"Settings were not saved: {exc}")

    def reload_settings(self):
        try:
            self.config = core.load_config(None)
            self.sync_network_settings()
            self.site.setText(self.config.site_id)
            self.scenario.setCurrentIndex(self.scenario.findData(self.config.scenario))
            self.update_run_plan()
            self.refresh_history()
            self.survey_page.refresh()
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
        for index, name in enumerate(["overview", "diagnostics", "history", "tools", "settings", "surveys"]):
            window.nav.setCurrentRow(index)
            QTest.qWait(80)
            app.processEvents()
            if not window.grab().save(str(target / f"{name}.png")):
                raise RuntimeError("Could not save GUI screenshot")
        assert window.metrics.rowCount() == len(demo_payload()["metrics"])
        assert not window.export_button.isEnabled()
        window.close()
    (target / "gui-smoke.json").write_text(json.dumps({"passed": True, "version": __version__, "pages": 6}), encoding="utf-8")
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
