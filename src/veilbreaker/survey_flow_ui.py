"""Next-point guidance; acquisition remains in the existing survey worker."""
from PySide6.QtWidgets import QWidget, QVBoxLayout
from .gui import label, button, table, fill
from .widgets import FlowLayout
from .survey_flow import next_point_context


class SurveyFlowPanel(QWidget):
    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.context = None
        self.request_context = None
        self.pending = False
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.addWidget(label('Prepare → Check → Capture → Review', 'section'))
        self.summary = label('', 'muted')
        self.body.addWidget(self.summary)
        actions = FlowLayout()
        self.check_button = button('Check next point readiness', self.check_readiness)
        self.review_button = button('Review latest attempted point', self.review_latest)
        actions.addWidget(self.check_button); actions.addWidget(self.review_button)
        self.body.addLayout(actions)
        self.caption = label('Readiness has not been checked.', 'muted')
        self.body.addWidget(self.caption)
        self.rows = table(['Prerequisite', 'State', 'Details / next action'])
        self.rows.setMaximumHeight(180)
        self.rows.hide()
        self.body.addWidget(self.rows)
        self.body.addWidget(label('Phone input: capture in Diagnostics, then use Add existing diagnostics here. Live phone collection is not queued. Readiness checks prerequisites, not device connectivity or signal.', 'muted'))

    def refresh(self, busy=False):
        session = self.page.session
        context = None
        message = 'Select a survey to prepare its next point.'
        if session:
            steps = session['steps']
            complete = sum(s['status'] == 'complete' for s in steps)
            prefix = f"{session['name']} · Site {session['site_id']} · {complete}/{len(steps)} tests complete. "
            if session.get('lifecycle') == 'completed':
                message = prefix + 'Survey completed. Review reports or reopen to add tests.'
            elif session.get('status') == 'running':
                message = prefix + 'Capture in progress. Review results when the worker finishes.'
            elif not self.page.can_continue():
                message = prefix + 'No unrun points remain. Review the report, compare/export, then complete the survey. Incomplete results remain identified.'
            else:
                try:
                    context = next_point_context(self.page.window.config, self.page.session_path)
                    names = {'active': 'Ping / DNS', 'guided': 'Guided checks', 'cellular': 'Serial modem', 'starlink': 'Starlink', 'sdr': 'HackRF receive', 'throughput': 'Throughput'}
                    inputs = ', '.join(names[k] for k,v in context['options'].items() if v) or 'Passive host observations'
                    mode = 'Manual: capture one point, then pause.' if context['manual'] else f"Batch: capture all {context['remaining']} remaining points."
                    message = prefix + f"Next: {context['label']} · {inputs}. {mode} Uses saved point settings."
                except (OSError, ValueError, KeyError) as exc:
                    message = prefix + str(exc)
        fingerprint = context['context'] if context else None
        if fingerprint != self.context:
            self.context = fingerprint
            self.request_context = None
            self.rows.setRowCount(0); self.rows.hide()
            self.caption.setText('Readiness has not been checked for this point/settings.')
        if not busy and self.pending:
            self.pending = False
            self.caption.setText('Readiness check not completed. Check again when ready.')
        self.summary.setText(message)
        self.check_button.setEnabled(not busy and context is not None)
        self.review_button.setEnabled(not busy and bool(session) and any(s['status'] in ('complete','partial','failed','interrupted') for s in session['steps']))
        self.page.continue_button.setText('Capture next point and pause' if not session or session.get('manual') else 'Capture remaining points')
        self.page.continue_button.setEnabled(not busy and context is not None)

    def check_readiness(self):
        if self.page.window.process is not None:
            return
        self.refresh()
        if not self.context:
            return
        self.request_context = self.context
        self.pending = True
        self.rows.setRowCount(0); self.rows.hide()
        self.caption.setText('Checking saved point prerequisites… No acquisition starts.')
        self.page.window.start_job('survey_readiness', survey_path=str(self.page.session_path))

    def accept(self, result):
        try:
            current = next_point_context(self.page.window.config, self.page.session_path)
        except (OSError, ValueError, KeyError, TypeError):
            return
        if self.page.detail.isHidden() or result['context'] != current['context'] or result['context'] != self.request_context:
            return
        self.pending = False
        check = result['check']
        fill(self.rows, [[r['item'],r['state'],r['detail']] for r in check['rows']])
        self.rows.show()
        self.caption.setText(f"Checked {check['checked_utc']} · Review missing/untested items. Recheck after changing equipment. Available does not mean connected.")

    def review_latest(self):
        if not self.page.session:
            return
        for index in range(len(self.page.session['steps'])-1, -1, -1):
            step = self.page.session['steps'][index]
            if step['status'] in ('complete','partial','failed','interrupted'):
                self.page.results.selectRow(index)
                if step['status'] in ('complete','partial','interrupted'):
                    self.page.open_run()
                else:
                    self.page.status.setText('Selected failed point: ' + step.get('error', 'No diagnostic report saved. Review notes and recovery tools.'))
                return
