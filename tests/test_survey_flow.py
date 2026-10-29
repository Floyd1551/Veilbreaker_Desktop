import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from veilbreaker import core, survey, jobs


class SurveyFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cfg = core.AppConfig(data_dir=self.temp.name, site_id='Field site')
        self.cfg.iperf3_server = 'saved.example'
        self.path = survey.create_survey(self.cfg, 'Walk', [dict(label='North', options={'throughput': True})])['survey_path']

    def test_saved_settings_worker_and_context(self):
        from veilbreaker.survey_flow import next_point_context
        before = Path(self.path).read_bytes()
        context = next_point_context(self.cfg, self.path)
        self.cfg.iperf3_server = 'unrelated.example'
        def check(config, options):
            self.assertEqual(config.iperf3_server, 'saved.example')
            self.assertTrue(options['throughput'])
            self.assertEqual(config.root, self.cfg.root)
            return {'rows': [], 'checked_utc': 'now'}
        with patch('veilbreaker.readiness.check_selected', side_effect=check):
            result = jobs.execute(dict(action='survey_readiness', config=self.cfg.to_dict(), survey_path=self.path))['survey_readiness']
        self.assertEqual(result['context'], context['context'])
        self.assertNotIn('saved.example', json.dumps(result))
        self.assertEqual(Path(self.path).read_bytes(), before)

    def test_legacy_snapshot_and_missing_snapshot(self):
        from veilbreaker.survey_flow import check_next_readiness
        data = json.loads(Path(self.path).read_text())
        data['steps'][0].pop('settings')
        Path(self.path).write_text(json.dumps(data))
        with patch('veilbreaker.readiness.check_selected', return_value={'rows': []}):
            check_next_readiness(self.cfg, self.path)
        (Path(self.path).parent/'settings'/Path(self.path).name).unlink()
        with self.assertRaisesRegex(ValueError, 'settings snapshot'):
            check_next_readiness(self.cfg, self.path)

    def test_changed_settings_and_closed_survey(self):
        from veilbreaker.survey_flow import next_point_context
        first = next_point_context(self.cfg, self.path)
        data = json.loads(Path(self.path).read_text())
        data['steps'][0]['settings']['iperf3_server'] = 'changed.example'
        Path(self.path).write_text(json.dumps(data))
        self.assertNotEqual(first['context'], next_point_context(self.cfg, self.path)['context'])
        survey.set_lifecycle(self.cfg, self.path, True)
        with self.assertRaisesRegex(ValueError, 'Reopen'):
            next_point_context(self.cfg, self.path)


class SurveyFlowGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from veilbreaker.gui import MainWindow
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cfg = core.AppConfig(data_dir=self.temp.name)
        self.window = MainWindow(self.cfg)
        self.addCleanup(self.window.close)
        self.window.error = lambda message: self.fail(message)
        self.page = self.window.survey_page
        saved = survey.create_survey(self.cfg, 'Walk', [dict(label='North')])
        self.path = saved['survey_path']
        self.page.show_session(saved['survey'], self.path)

    def test_labels_dispatch_and_cancel_state(self):
        flow = self.page.flow
        self.assertIn('North', flow.summary.text())
        self.assertIn('Capture next point', self.page.continue_button.text())
        with patch.object(self.window, 'start_job') as start:
            flow.check_readiness()
            start.assert_called_once_with('survey_readiness', survey_path=str(self.path))
        self.page.set_busy(False)
        self.assertIn('not completed', flow.caption.text())
        session = survey.update_survey(self.cfg, self.path, {'manual': False})
        self.page.show_session(session, self.path)
        self.assertIn('remaining', self.page.continue_button.text())

    def test_observation_editor_opens_with_selected_point(self):
        self.page.results.selectRow(0)
        run=self.page.session['steps'][0]['run_id']
        with patch('veilbreaker.survey_observations_ui.ObservationsDialog') as editor:
            self.page.open_observations()
            editor.assert_called_once_with(self.window,self.cfg,self.path,run)
            editor.return_value.exec.assert_called_once()

    def test_stale_readiness_and_completed_state(self):
        from veilbreaker.survey_flow import check_next_readiness
        flow = self.page.flow
        result = check_next_readiness(self.cfg, self.path)
        flow.request_context = result['context']
        flow.accept(result)
        self.assertGreater(flow.rows.rowCount(), 0)
        session = survey.update_survey(self.cfg, self.path, {'manual': False})
        self.page.show_session(session, self.path)
        flow.accept(result)
        self.assertEqual(flow.rows.rowCount(), 0)
        session = survey.set_lifecycle(self.cfg, self.path, True)
        self.page.show_session(session, self.path)
        self.assertFalse(flow.check_button.isEnabled())
        self.assertIn('completed', flow.summary.text().lower())

    def test_real_worker_returns_to_survey(self):
        import time
        from PySide6.QtTest import QTest
        self.window.nav.setCurrentRow(3)
        self.page.show_session(survey.read_session(self.cfg, self.path), self.path)
        self.page.flow.check_readiness()
        deadline = time.monotonic() + 20
        while self.window.process is not None and time.monotonic() < deadline:
            QTest.qWait(25)
        self.assertIsNone(self.window.process)
        self.assertEqual(self.window.nav.currentRow(), 3)
        self.assertGreater(self.page.flow.rows.rowCount(), 0)
        self.assertFalse(self.page.flow.pending)
        self.assertIn('Checked ', self.page.flow.caption.text())

    def test_failed_point_review_does_not_rerun(self):
        data = json.loads(Path(self.path).read_text())
        data['steps'][0]['status'] = 'failed'
        data['steps'][0]['error'] = 'Receiver disconnected'
        data['status'] = 'partial'
        Path(self.path).write_text(json.dumps(data))
        self.page.show_session(survey.read_session(self.cfg, self.path), self.path)
        self.page.flow.review_latest()
        self.assertIn('Receiver disconnected', self.page.status.text())
        self.assertFalse(self.page.continue_button.isEnabled())
        self.assertEqual(self.page.results.currentRow(), 0)

    def test_narrow_detail_with_readiness(self):
        from PySide6.QtTest import QTest
        from veilbreaker.survey_flow import check_next_readiness
        self.window.nav.setCurrentRow(3)
        self.page.show_session(survey.read_session(self.cfg, self.path), self.path)
        self.window.resize(760, 640)
        self.window.show()
        result = check_next_readiness(self.cfg, self.path)
        self.page.flow.request_context = result['context']
        self.page.flow.accept(result)
        QTest.qWait(100)
        self.assertEqual(self.window.pages.widget(3).horizontalScrollBar().maximum(), 0)

    def test_worker_cleanup_reloads_failed_point(self):
        self.window.active_survey_path = self.path
        data = json.loads(Path(self.path).read_text())
        data['steps'][0]['status'] = 'failed'
        data['steps'][0]['error'] = 'Capture stopped'
        data['status'] = 'partial'
        Path(self.path).write_text(json.dumps(data))
        self.window.cleanup_job()
        self.assertEqual(self.page.session['steps'][0]['status'], 'failed')
        self.assertTrue(self.page.flow.review_button.isEnabled())
