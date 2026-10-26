"""Survey planning and comparison UI; acquisition remains in the worker."""
import json
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QSpinBox, QComboBox, QCheckBox, QFileDialog, QHeaderView, QPlainTextEdit, QDialog, QInputDialog, QFrame, QMessageBox
from .gui import label, button, table, fill
from .survey_templates import save_template, load_template
from . import core
from .survey import list_sessions, read_session, export_session, update_point_notes
from .widgets import FlowLayout


class SurveyPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.steps = []
        self.session = None
        self.session_path = None
        self.session_cache = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.addWidget(label("Site surveys", "title"))
        layout.addWidget(label("Group up to 20 named diagnostics. Choose test flags on Diagnostics, then add steps here. Site and scenario come from Diagnostics when the survey is saved.", "muted"))
        outer = layout
        self.back_button = button('Back to surveys', self.show_landing)
        outer.addWidget(self.back_button)
        self.landing = QWidget()
        self.detail = QWidget()
        self.landing_layout = QVBoxLayout(self.landing)
        outer.addWidget(self.landing)
        outer.addWidget(self.detail)
        self.adding_to_session = False
        self.builder = QFrame()
        self.builder.setObjectName('card')
        self.builder_toggle = QCheckBox("Plan a survey")
        self.builder_toggle.setChecked(False)
        self.builder_toggle.toggled.connect(self.builder.setVisible)
        outer.addWidget(self.builder_toggle)
        outer.addWidget(self.builder)
        layout = QVBoxLayout(self.builder)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        layout.addWidget(label("SURVEY PLAN", "eyebrow"))
        self.name = QLineEdit("Site survey")
        self.name.setMaxLength(100)
        self.name.setAccessibleName("Survey name")
        layout.addWidget(self.name)
        templates = FlowLayout()
        self.save_template_button = button("Save queue as template…", self.save_queue_template)
        self.load_template_button = button("Load template…", self.load_queue_template)
        templates.addWidget(self.save_template_button)
        templates.addWidget(self.load_template_button)
        layout.addLayout(templates)
        self.template_hint = label("Reuse a template or add points below. Test selections come from Diagnostics; each visit uses your current settings.", "muted")
        layout.addWidget(self.template_hint)
        add = QHBoxLayout()
        self.step_name = QLineEdit()
        self.step_name.setMaxLength(90)
        self.step_name.setPlaceholderText("Test or survey-point label")
        self.step_name.setAccessibleName("Test label")
        self.copies = QSpinBox()
        self.copies.setRange(1, 20)
        self.copies.setAccessibleName("Number of repeated tests to add")
        add.addWidget(self.step_name, 1)
        add.addWidget(label("Copies"))
        add.addWidget(self.copies)
        self.add_button = button("Add selected tests", self.add_steps)
        add.addWidget(self.add_button)
        layout.addLayout(add)
        self.queue = table(["Step", "Label", "Requested tests"])
        self.queue.setMinimumHeight(160)
        self.queue.setMaximumHeight(230)
        self.queue.hide()
        self.queue_hint = label("No points yet. Name your first point and choose Add selected tests.", "muted")
        layout.addWidget(self.queue_hint)
        layout.addWidget(self.queue)
        self.preset = QCheckBox("Use Tools receive preset for SDR steps")
        self.preset.setChecked(True)
        survey_options = FlowLayout()
        survey_options.addWidget(self.preset)
        self.manual = QCheckBox("Pause between tests (manual progression)")
        self.manual.setChecked(True)
        survey_options.addWidget(self.manual)
        layout.addLayout(survey_options)
        actions = FlowLayout()
        self.remove_button = button("Remove selected step", self.remove_step)
        self.start_button = button("Save survey", self.start, True)
        self.start_button.setEnabled(False)
        self.remove_button.setEnabled(False)
        self.queue.itemSelectionChanged.connect(self.update_queue_actions)
        self.rename_button = button("Rename point…", self.rename_queued_point)
        self.move_up_button = button("Move up", lambda: self.move_queued_point(-1))
        self.move_down_button = button("Move down", lambda: self.move_queued_point(1))
        for control in (self.rename_button,self.move_up_button,self.move_down_button):
            control.setEnabled(False)
            control.hide()
            actions.addWidget(control)
        self.remove_button.hide()
        actions.addWidget(self.remove_button)
        layout.addLayout(actions)
        start_actions = QHBoxLayout()
        start_actions.addWidget(self.start_button)
        start_actions.addWidget(label("Pause mode lets you move to the next point before continuing.", "muted"), 1)
        layout.addLayout(start_actions)
        layout = self.landing_layout
        layout.addWidget(button('New survey', self.new_survey, True))
        layout.addWidget(button('Trash / restore', self.window.open_trash))
        layout.addWidget(label("Saved surveys", "section"))
        self.session_search = QLineEdit()
        self.session_search.setAccessibleName("Search survey sessions")
        self.session_search.setPlaceholderText("Find surveys by name, site, point, ID or UTC date")
        self.session_search.setClearButtonEnabled(True)
        self.session_filter = QComboBox()
        self.session_filter.setAccessibleName("Survey session state")
        self.session_filter.addItems(["All states", "Open", "Completed", "paused", "partial", "interrupted", "running"])
        layout.addWidget(self.session_search)
        layout.addWidget(self.session_filter)
        self.session_count = label("", "muted")
        layout.addWidget(self.session_count)
        self.session_search.textChanged.connect(self.filter_sessions)
        self.session_filter.currentTextChanged.connect(self.filter_sessions)
        saved = FlowLayout()
        self.saved = QComboBox()
        self.saved.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.saved.setMinimumContentsLength(16)
        self.saved.setAccessibleName("Saved survey sessions")
        saved.addWidget(self.saved)
        saved.addWidget(button("Refresh sessions", self.refresh))
        self.open_session_button = button("Open session", self.open_session)
        saved.addWidget(self.open_session_button)
        self.saved.currentIndexChanged.connect(lambda: self.open_session_button.setEnabled(bool(self.saved.currentData())))
        self.saved.hide()
        self.open_session_button.hide()
        layout.addLayout(saved)
        self.session_list = table(['Survey', 'Site', 'Lifecycle', 'Tests complete / total', 'Updated UTC'])
        self.session_list.itemActivated.connect(self.open_listing)
        self.session_list.itemClicked.connect(self.open_listing)
        layout.addWidget(self.session_list)
        layout = QVBoxLayout(self.detail)
        detail_actions = FlowLayout()
        self.configure_button = button('Configure / attributes', self.configure_session)
        self.add_tests_button = button('Add new tests', self.add_to_session)
        self.add_existing_button = button('Add existing diagnostics', self.add_existing)
        self.complete_button = button('Complete survey', self.toggle_complete)
        self.delete_survey_button = button('Delete survey', self.delete_session)
        for control in (self.configure_button,self.add_tests_button,self.add_existing_button,self.complete_button,self.delete_survey_button): detail_actions.addWidget(control)
        layout.addLayout(detail_actions)
        self.attributes = label('', 'muted')
        layout.addWidget(self.attributes)
        self.status = label("No survey selected", "muted")
        layout.addWidget(self.status)
        self.compare_visit_button = button("Compare this visit with a baseline…", self.compare_visit)
        self.compare_visit_button.setEnabled(False)
        layout.addWidget(self.compare_visit_button)
        self.trend_button = button("Trends across visits…", self.show_trends)
        self.trend_button.setEnabled(False)
        layout.addWidget(self.trend_button)
        self.continue_button = button("Run next unrun test / continue session", self.continue_session, True)
        self.continue_button.setEnabled(False)
        layout.addWidget(self.continue_button)
        self.results = table(["Test", "Label", "Collection", "Assessment", "Run"])
        self.results.setMinimumHeight(170)
        layout.addWidget(self.results)
        self.open_run_button = button("Open selected diagnostic", self.open_run)
        self.open_run_button.setEnabled(False)
        layout.addWidget(self.open_run_button)
        self.results.itemActivated.connect(lambda *_: self.open_run())
        self.point_notes = QPlainTextEdit()
        self.point_notes.setAccessibleName("Selected point notes")
        self.point_notes.setPlaceholderText("Select a test above, then record location, antenna placement or conditions (up to 2000 characters).")
        self.point_notes.setMaximumHeight(85)
        self.point_notes.setEnabled(False)
        layout.addWidget(self.point_notes)
        self.save_notes = button("Save selected point notes", self.save_point_notes)
        self.save_notes.setEnabled(False)
        layout.addWidget(self.save_notes)
        self.results.itemSelectionChanged.connect(self.select_point)
        self.comparison = table(["Metric"])
        self.comparison.setMinimumHeight(220)
        layout.addWidget(self.comparison)
        layout.addWidget(label("— means not observed, never zero. Compare equivalent tests and receiver settings. Each run keeps its original evidence; varying test selections or antenna placement affect comparability.", "muted"))
        self.export_button = button("Export survey and all available evidence…", self.export)
        self.export_button.setEnabled(False)
        layout.addWidget(self.export_button)
        self.report_button = button("View survey report / save HTML…", self.view_report)
        self.report_button.setEnabled(False)
        layout.addWidget(self.report_button)
        report_actions = FlowLayout()
        for control in (self.report_button, self.export_button, self.compare_visit_button, self.trend_button):
            layout.removeWidget(control)
            report_actions.addWidget(control)
        self.map_button = button('Survey map', self.view_map)
        report_actions.addWidget(self.map_button)
        report_actions.addWidget(button('Place points / floor plans…', self.place_points))
        self.imagery_button = button('Prepare report map…', self.prepare_report_map)
        report_actions.addWidget(self.imagery_button)
        layout.insertLayout(3, report_actions)
        from .survey_flow_ui import SurveyFlowPanel
        self.flow = SurveyFlowPanel(self)
        layout.removeWidget(self.continue_button)
        self.flow.body.addWidget(self.continue_button)
        layout.insertWidget(0, self.flow)
        self.refresh()
        self.show_landing()

    def save_queue_template(self):
        from .survey_templates import validate_template
        try:
            validate_template({"format": "veilbreaker-survey-template", "version": 1,
                               "name": self.name.text(), "steps": self.steps, "manual": self.manual.isChecked()})
            path, _ = QFileDialog.getSaveFileName(self, "Save survey template", "survey-template.json", "Survey template (*.json)")
            if path:
                save_template(path, self.name.text(), self.steps, self.manual.isChecked())
                self.template_hint.setText("Template saved. It contains no captured results, point notes or device settings.")
        except (OSError, ValueError) as exc:
            self.window.error(str(exc))

    def load_queue_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load survey template", "", "Survey template (*.json)")
        if not path:
            return
        try:
            value = load_template(path)
            self.steps = value["steps"]
            self.name.setText(value["name"])
            self.manual.setChecked(value["manual"])
            self.update_queue()
            self.landing.hide(); self.detail.hide(); self.back_button.show()
            self.builder_toggle.setChecked(True); self.builder.show()
            self.template_hint.setText("Template loaded into the queue; no tests started. Review every test, current site/scenario, targets and SDR settings, then Save survey. Run next starts acquisition from survey details.")
            QTimer.singleShot(0, lambda: self.window.pages.widget(5).ensureWidgetVisible(self.queue))
        except (OSError, ValueError) as exc:
            self.window.error(str(exc))

    def add_steps(self):
        if len(self.steps) + self.copies.value() > 20:
            self.window.error("A survey can contain at most 20 tests. Remove steps before adding more.")
            return
        options = {key: box.isChecked() for key, box in self.window.flags.items()}
        options["active"] = options["active"] or options["guided"]
        name = self.step_name.text().strip() or "Test"
        used = {s["label"] for s in self.steps}
        number = len(self.steps)+1
        for _ in range(self.copies.value()):
            while f"{name} {number}" in used:
                number += 1
            point = f"{name} {number}"
            used.add(point)
            self.steps.append({"label": point, "options": dict(options)})
            number += 1
        self.update_queue()

    def remove_step(self):
        index = self.queue.currentRow()
        if 0 <= index < len(self.steps):
            self.steps.pop(index)
        self.update_queue()

    def update_queue(self):
        self.queue_hint.setText(f"{len(self.steps)} of 20 points planned. Select a point to rename, reorder or remove it." if self.steps else "No points yet. Name your first point and choose Add selected tests.")
        self.queue.setVisible(bool(self.steps))
        for control in (self.rename_button, self.move_up_button, self.move_down_button, self.remove_button):
            control.setVisible(bool(self.steps))
        self.queue.clearSelection()
        self.queue.setCurrentCell(-1, -1)
        fill(self.queue, [[i, s["label"], ", ".join(k for k, v in s["options"].items() if v) or "Passive host/network"] for i, s in enumerate(self.steps, 1)])
        self.update_queue_actions()

    def update_queue_actions(self):
        idle = self.window.process is None
        self.start_button.setEnabled(idle and bool(self.steps))
        selected = idle and bool(self.queue.selectedItems())
        self.remove_button.setEnabled(selected)
        self.rename_button.setEnabled(selected)
        self.move_up_button.setEnabled(selected and self.queue.currentRow() > 0)
        self.move_down_button.setEnabled(selected and self.queue.currentRow() < len(self.steps)-1)

    def set_busy(self, busy):
        for control in (self.configure_button,self.add_tests_button,self.add_existing_button,self.complete_button,self.delete_survey_button):
            control.setEnabled(not busy and bool(self.session) and self.session.get('status')!='running')
        if self.session and len(self.session['steps']) >= 20:
            self.add_tests_button.setEnabled(False); self.add_existing_button.setEnabled(False)
        if self.session and self.session.get('lifecycle')=='completed':
            self.configure_button.setEnabled(False); self.add_tests_button.setEnabled(False); self.add_existing_button.setEnabled(False)
        for control in (self.name, self.step_name, self.copies, self.add_button, self.remove_button, self.start_button, self.preset, self.manual, self.save_template_button, self.load_template_button):
            control.setEnabled(not busy)
        self.continue_button.setEnabled(not busy and self.can_continue())
        self.point_notes.setEnabled(not busy and bool(self.session) and self.session.get("status") != "running" and self.results.currentRow() >= 0)
        self.save_notes.setEnabled(self.point_notes.isEnabled())
        self.update_queue_actions()
        self.flow.refresh(busy)

    def start(self):
        from .survey import validate_steps, create_survey, append_steps
        try:
            steps = validate_steps(self.steps)
            cfg = core.AppConfig.from_dict(self.window.config.to_dict())
            cfg.site_id = self.window.site.text().strip() or cfg.site_id
            cfg.scenario = self.window.scenario.currentData()
            if self.preset.isChecked() and any(step['options']['sdr'] for step in steps):
                settings = self.window.selected_capture_settings()
                from .rf_workflow import apply_preset
                apply_preset(cfg, **settings)
            if self.adding_to_session:
                session = append_steps(cfg, self.session_path, steps)
                self.show_session(session, self.session_path)
            else:
                result = create_survey(cfg, self.name.text().strip(), steps, self.manual.isChecked())
                self.show_session(result['survey'], result['survey_path'])
            self.steps = []
            self.update_queue()
            self.refresh()
        except (OSError, ValueError) as exc: self.window.error(str(exc))

    def show_landing(self):
        self.landing.show(); self.detail.hide(); self.builder.hide()
        self.builder_toggle.hide(); self.back_button.hide()
        self.adding_to_session = False
        self.refresh()

    def new_survey(self):
        self.adding_to_session = False
        self.steps = []; self.update_queue()
        self.name.setEnabled(True); self.name.setText('Site survey')
        self.start_button.setText('Save survey')
        self.landing.hide(); self.detail.hide(); self.back_button.show()
        self.builder_toggle.setChecked(True); self.builder.show()

    def add_to_session(self):
        if not self.session or self.window.process is not None: return
        self.new_survey()
        self.adding_to_session = True
        self.name.setText(self.session['name']); self.name.setEnabled(False)
        self.start_button.setText('Add tests to survey')
        self.queue_hint.setText(str(20-len(self.session['steps'])) + ' test slots remain. Adding tests does not start collection.')

    def add_existing(self):
        if not self.session or self.window.process is not None: return
        from .survey_existing_ui import ExistingDiagnosticsDialog
        from .survey import attach_existing_runs
        try:
            dialog = ExistingDiagnosticsDialog(self.window.config, self.session, self)
            if dialog.exec() != QDialog.DialogCode.Accepted: return
            self.show_session(attach_existing_runs(self.window.config, self.session_path, dialog.selected_ids()), self.session_path)
            self.refresh(); self.window.refresh_history()
        except (OSError, ValueError) as exc: self.window.error(str(exc))

    def open_listing(self, *_):
        index = self.session_list.currentRow()
        if 0 <= index < len(self.visible_sessions):
            path, session = self.visible_sessions[index]
            self.show_session(session, str(path))

    def configure_session(self):
        if not self.session or self.window.process is not None: return
        from .survey import update_survey
        dialog = QDialog(self); dialog.setWindowTitle('Survey attributes and future tests')
        body = QVBoxLayout(dialog)
        body.addWidget(label('Site: ' + self.session['site_id'] + ' — fixed for this survey'))
        name = QLineEdit(self.session['name']); body.addWidget(name)
        notes = QPlainTextEdit(self.session.get('notes','')); body.addWidget(notes)
        manual = QCheckBox('Pause between tests'); manual.setChecked(self.session.get('manual',True)); body.addWidget(manual)
        settings = QCheckBox('Apply current Settings to unrun tests only'); body.addWidget(settings)
        body.addWidget(button('Save', dialog.accept)); body.addWidget(button('Cancel', dialog.reject))
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        try:
            changes = dict(name=name.text(), notes=notes.toPlainText(), manual=manual.isChecked())
            if settings.isChecked(): changes['settings'] = self.window.config.to_dict()
            self.show_session(update_survey(self.window.config,self.session_path,changes), self.session_path)
            self.refresh()
        except (OSError,ValueError) as exc: self.window.error(str(exc))

    def toggle_complete(self):
        if not self.session or self.window.process is not None: return
        from .survey import set_lifecycle
        completed = self.session.get('lifecycle') != 'completed'
        pending = sum(step['status'] in ('planned','not_run') for step in self.session['steps'])
        if completed and QMessageBox.question(self,'Complete survey?',f'Complete this survey with {pending} unrun tests? Unrun and failed measurements remain identified; results are not changed to success.') != QMessageBox.StandardButton.Yes: return
        try:
            self.show_session(set_lifecycle(self.window.config,self.session_path,completed), self.session_path)
            self.refresh()
        except (OSError,ValueError) as exc: self.window.error(str(exc))

    def delete_session(self):
        if not self.session or self.window.process is not None: return
        from .library import trash_survey, run_dependencies
        owned = 0
        store = core.VeilbreakerStore(self.window.config.db_path)
        try:
            for step in self.session['steps']:
                deps = run_dependencies(self.window.config, step['run_id'], store)
                if store.get_run(step['run_id']) and not deps['cases'] and not any(owner != self.session['survey_id'] for owner in deps['surveys']):
                    owned += 1
        finally: store.close()
        dialog = QDialog(self); dialog.setWindowTitle('Move survey to Trash')
        body = QVBoxLayout(dialog)
        body.addWidget(label('Remove '+self.session['name']+'? By default its tests remain in the test library. Shared/case evidence is preserved.'))
        include = QCheckBox(f'Also remove up to {owned} exclusively owned saved tests'); body.addWidget(include)
        body.addWidget(button('Move to Trash',dialog.accept)); body.addWidget(button('Cancel',dialog.reject))
        if dialog.exec()!=QDialog.DialogCode.Accepted: return
        try:
            trash_survey(self.window.config,self.session_path,include.isChecked())
            self.window.refresh_history()
            if include.isChecked() and self.window.payload and any(step['run_id']==self.window.payload['run_id'] for step in self.session['steps']): self.window.clear_workspace()
            self.session=None; self.session_path=None; self.show_landing()
        except (OSError,ValueError) as exc: self.window.error(str(exc))

    def refresh(self):
        self.session_cache = list_sessions(self.window.config)
        self.filter_sessions()

    def filter_sessions(self):
        from .survey_plans import session_matches
        selected = self.saved.currentData()
        self.saved.clear()
        self.visible_sessions = []
        state = self.session_filter.currentText()
        for path, session in self.session_cache:
            lifecycle = session.get('lifecycle', 'completed' if session['status']=='complete' else 'open')
            if state in ('Open','Completed') and lifecycle != state.lower(): continue
            if state not in ('All states','Open','Completed') and session['status'] != state: continue
            if session_matches(session,self.session_search.text(),'All states'):
                self.visible_sessions.append((path,session))
                self.saved.addItem(f"{session['name']} • {session['site_id']} • {session['status']} • {session['created_utc']}", str(path))
        fill(self.session_list, [[v['name'],v['site_id'],v.get('lifecycle','open'),str(sum(s['status']=='complete' for s in v['steps']))+' / '+str(len(v['steps'])),v.get('edit_history',[{}])[-1].get('timestamp',v['created_utc'])] for _,v in self.visible_sessions])
        index = self.saved.findData(selected)
        if index >= 0:
            self.saved.setCurrentIndex(index)
        self.open_session_button.setEnabled(bool(self.saved.currentData()))
        self.session_count.setText(f"{self.saved.count()} of {len(self.session_cache)} saved surveys")

    def rename_queued_point(self):
        from .survey_plans import rename_point
        index = self.queue.currentRow()
        if not 0 <= index < len(self.steps):
            return
        name, accepted = QInputDialog.getText(self,"Rename survey point","Point label",text=self.steps[index]["label"])
        if accepted:
            try:
                self.steps = rename_point(self.steps,index,name)
                self.update_queue()
                self.queue.selectRow(index)
            except ValueError as exc:
                self.window.error(str(exc))

    def move_queued_point(self, direction):
        from .survey_plans import move_point
        index = self.queue.currentRow()
        try:
            self.steps = move_point(self.steps,index,direction)
            self.update_queue()
            self.queue.selectRow(index+direction)
        except ValueError as exc:
            self.window.error(str(exc))

    def open_session(self):
        path = self.saved.currentData()
        if path:
            try:
                self.show_session(read_session(self.window.config, path), path)
            except (OSError, ValueError, KeyError) as exc:
                self.window.error(str(exc))

    def show_session(self, session, path):
        self.session, self.session_path = session, path
        self.landing.hide(); self.builder.hide(); self.detail.show(); self.back_button.show()
        self.builder_toggle.hide()
        completed = session.get('lifecycle', 'completed' if session['status']=='complete' else 'open')=='completed'
        self.complete_button.setText('Reopen survey' if completed else 'Complete survey')
        self.add_tests_button.setEnabled(not completed and len(session['steps'])<20)
        self.add_existing_button.setEnabled(not completed and len(session['steps'])<20)
        self.configure_button.setEnabled(not completed)
        self.attributes.setText('Lifecycle: '+('Completed' if completed else 'Open')+' | Scenario: '+session.get('scenario','Not recorded')+' | '+session.get('notes',''))
        self.results.clearSelection()
        self.results.setCurrentCell(-1, -1)
        self.compare_visit_button.setEnabled(True)
        self.trend_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.report_button.setEnabled(True)
        self.builder_toggle.setChecked(False)
        self.continue_button.setEnabled(self.window.process is None and self.can_continue())
        self.point_notes.clear()
        self.status.setText(f"{session['name']} • Site {session['site_id']} • {session['status']} • {len(session['steps'])} tests")
        fill(self.results, [[i, s["label"], s["status"], s.get("assessment", s.get("error", "—")), s["run_id"]] for i, s in enumerate(session["steps"], 1)])
        QTimer.singleShot(0, lambda: self.window.pages.widget(5).ensureWidgetVisible(self.continue_button if self.can_continue() else self.comparison))
        self.select_point()
        self.flow.refresh(self.window.process is not None)
        steps = session["steps"]
        keys = sorted({k for s in steps for k in s.get("metrics", {})})
        self.comparison.setVisible(bool(keys))
        self.comparison.setColumnCount(len(steps) + 1)
        self.comparison.setHorizontalHeaderLabels(["Metric", *[s["label"] for s in steps]])
        fill(self.comparison, [[k, *[json.dumps(s["metrics"][k], ensure_ascii=False) if k in s.get("metrics", {}) else "—" for s in steps]] for k in keys])
        self.comparison.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.comparison.setColumnWidth(0, 210)
        for index in range(1, len(steps) + 1):
            self.comparison.setColumnWidth(index, 135)

    def can_continue(self):
        return bool(self.session and self.session.get("status") != "running" and self.session.get("lifecycle") != "completed" and
                    any(s["status"] in ("planned", "not_run") for s in self.session["steps"]))

    def continue_session(self):
        if self.can_continue():
            self.window.start_job("survey_resume", survey_path=str(self.session_path))

    def select_point(self):
        index = self.results.currentRow()
        valid = bool(self.session and 0 <= index < len(self.session["steps"]))
        self.open_run_button.setEnabled(valid and self.session["steps"][index].get("status") in ("complete", "partial", "interrupted"))
        editable = valid and self.session.get("status") != "running" and self.window.process is None
        self.point_notes.setEnabled(editable)
        self.save_notes.setEnabled(editable)
        self.point_notes.setPlainText(self.session["steps"][index].get("notes", "") if valid else "")

    def save_point_notes(self):
        index = self.results.currentRow()
        if not self.session_path or index < 0:
            return
        try:
            session = update_point_notes(self.window.config, self.session_path, index, self.point_notes.toPlainText())
            self.show_session(session, self.session_path)
            self.results.selectRow(index)
            self.status.setText("Point notes saved. Re-export the survey to include the updated notes.")
        except (OSError, ValueError, KeyError) as exc:
            self.window.error(str(exc))

    def open_run(self):
        if not self.session:
            return
        index = self.results.currentRow()
        if not 0 <= index < len(self.session["steps"]):
            return
        store = core.VeilbreakerStore(self.window.config.db_path)
        try:
            row = store.get_run(self.session["steps"][index]["run_id"])
            if row:
                self.window.display_saved_run(dict(row))
            else:
                self.window.error("This step has no saved diagnostic. Recover interrupted captures in Tools if available.")
        finally:
            store.close()

    def view_map(self):
        if not self.session_path: return
        from .map_sources import load_survey_map_data
        try: self.window.show_map(load_survey_map_data(self.window.config, self.session_path))
        except (OSError, ValueError, KeyError) as exc: self.window.error(str(exc))

    def place_points(self):
        if not self.session_path:
            return
        from .survey_spatial_ui import SpatialDialog
        try:
            SpatialDialog(self.window, self.window.config, self.session_path).exec()
        except (OSError, ValueError, KeyError) as exc:
            self.window.error(str(exc))

    def prepare_report_map(self):
        if not self.session_path:
            self.window.error('Open a survey before preparing its map.')
            return
        from .survey_imagery_ui import SurveyImageryDialog
        try:
            SurveyImageryDialog(self.window, self.window.config, self.session_path).exec()
        except (OSError, ValueError, KeyError) as exc:
            self.window.error(str(exc))

    def view_report(self):
        if not self.session_path:
            return
        from .report_viewer import ReportViewer
        from .survey_report import report_html
        from .survey_imagery import report_context
        from .cell_context import saved_context_html
        try:
            session = read_session(self.window.config, self.session_path)
            self.report_viewer = ReportViewer(self.window, self.session_path,
                reports=[('survey_report.html', report_html(session, report_context(self.window.config,self.session_path), saved_context_html(self.window.config,self.session_path)).encode('utf-8'))])
            self.report_viewer.showMaximized()
        except (OSError, ValueError, KeyError) as exc:
            self.window.error(str(exc))

    def export(self):
        if not self.session_path:
            self.window.error("Open a survey session before exporting")
            return
        target, _ = QFileDialog.getSaveFileName(self, "Export survey evidence", self.session["survey_id"] + ".zip", "ZIP archive (*.zip)")
        if target:
            try:
                export_session(self.window.config, self.session_path, target)
                self.status.setText(f"Survey evidence exported to {target}")
            except (OSError, ValueError, KeyError) as exc:
                self.window.error(str(exc))

    def compare_visit(self):
        if not self.session_path:
            self.window.error("Open the current survey visit first")
            return
        from .survey_compare import compare_saved_visits
        from .recovery import atomic_json
        class ComparisonDialog(QDialog):
            def reject(inner):
                if persist():
                    super().reject()
        dialog = ComparisonDialog(self)
        dialog.setWindowTitle("Compare survey visits")
        dialog.resize(1100, 650)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label("Baseline visit", "title"))
        choice = QComboBox()
        choice.setAccessibleName("Baseline survey visit")
        for path, session in list_sessions(self.window.config):
            if str(path) != str(self.session_path) and session["site_id"] == self.session["site_id"]:
                choice.addItem(f"{session['name']} • {session['created_utc']} • {session['status']}", str(path))
        layout.addWidget(choice)
        summary = label("Select a baseline. Points match by exact label, regardless of queue order.", "muted")
        layout.addWidget(summary)
        rows = table(["Point", "Metric", "Baseline", "Current", "Change", "Notes"])
        layout.addWidget(rows, 1)
        layout.addWidget(label("Change = current − baseline; it does not mean better or worse. Missing values stay unknown. Matching settings cannot verify identical antennas, hardware or conditions. Use spectrum comparison for RF evidence.", "muted"))
        from .comparison_report import load_notes, save_notes, report_html
        from .report_viewer import ReportViewer
        notes = QPlainTextEdit()
        notes.setAccessibleName("Change between survey visits")
        notes.setPlaceholderText("What changed? Antenna placement, equipment, configuration or conditions (up to 2000 characters). Notes save automatically when you leave the field, switch baseline, view or export.")
        notes.setMaximumHeight(85)
        layout.addWidget(notes)
        result = {}
        annotation = {}
        def persist():
            if not result:
                return True
            try:
                if notes.toPlainText() != annotation.get('notes', ''):
                    annotation.update(save_notes(self.window.config.root, result['baseline']['survey_id'], result['current']['survey_id'], notes.toPlainText()))
                return True
            except (OSError, ValueError) as exc:
                self.window.error(str(exc))
                return False
        previous_focus_out = notes.focusOutEvent
        def save_on_blur(event):
            persist()
            previous_focus_out(event)
        notes.focusOutEvent = save_on_blur
        def refresh():
            if not persist():
                choice.blockSignals(True)
                choice.setCurrentIndex(choice.findData(result.get('_baseline_path')))
                choice.blockSignals(False)
                return

            result.clear()
            rows.setRowCount(0)
            export_button.setEnabled(False)
            report_button.setEnabled(False)
            notes.setEnabled(False)
            notes.clear()
            annotation.clear()
            if not choice.currentData():
                summary.setText("No other saved visits for this site. Run the same template on another visit, then compare here.")
                return
            try:
                result.update(compare_saved_visits(self.window.config, choice.currentData(), self.session_path))
                annotation.update(load_notes(self.window.config.root, result['baseline']['survey_id'], result['current']['survey_id']))
                result['_baseline_path'] = choice.currentData()
                notes.setPlainText(annotation['notes'])
                notes.setEnabled(True)
                def display(value):
                    return "—" if value is None else json.dumps(value, ensure_ascii=False)
                fill(rows, [[r["point"], r["metric"], display(r["baseline"]), display(r["current"]), display(r["delta"]), r["notes"]] for r in result["rows"]])
                rows.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                for index, width in enumerate((140, 170, 135, 135, 100, 290)):
                    rows.setColumnWidth(index, width)
                summary.setText(f"Current: {result['current']['name']} • {result['current']['created_utc']} | Settings: " + ("match" if result["settings_match"] else "different or unavailable; changes withheld"))
                export_button.setEnabled(True)
                report_button.setEnabled(True)
            except (OSError, ValueError, KeyError) as exc:
                result.clear()
                summary.setText(str(exc))
        def snapshot():
            return {**{k: v for k, v in result.items() if not k.startswith('_')}, 'change_notes': notes.toPlainText(), 'change_notes_updated_utc': annotation.get('updated_utc')}
        def view_comparison():
            if result and persist():
                viewer = ReportViewer(dialog, 'Survey visit comparison', reports=[('visit_comparison.html', report_html(result, notes.toPlainText(), annotation.get('updated_utc')).encode('utf-8'))])
                viewer.exec()
        def export_comparison():
            if not persist():
                return
            target, _ = QFileDialog.getSaveFileName(dialog, "Export visit comparison", "visit-comparison.json", "JSON (*.json)")
            if target:
                try:
                    atomic_json(Path(target), snapshot())
                    summary.setText("Comparison exported; original survey evidence is unchanged.")
                except OSError as exc:
                    self.window.error(str(exc))
        report_button = button("View comparison report / save HTML…", view_comparison)
        layout.addWidget(report_button)
        export_button = button("Export comparison JSON…", export_comparison)
        layout.addWidget(export_button)
        choice.currentIndexChanged.connect(refresh)
        refresh()
        dialog.exec()
        persist()

    def show_trends(self):
        if self.session_path:
            from .trend_ui import TrendDialog
            try:
                TrendDialog(self.window, self.session_path).exec()
            except (OSError, ValueError, KeyError) as exc:
                self.window.error(str(exc))
