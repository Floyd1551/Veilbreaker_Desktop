import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from veilbreaker import core, survey, library

class ExistingDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cfg = core.AppConfig(data_dir=self.temp.name)
        app = core.VeilbreakerApplication(self.cfg)
        with patch.object(app, 'collect_passive', return_value=({'latency_ms': 12}, [])):
            app.run(run_id='existing-test')
        app.close()
        self.path = survey.create_survey(self.cfg, 'Survey', [{}])['survey_path']

    def test_link_preserves_evidence_and_populates_comparison(self):
        evidence = self.cfg.reports_dir / 'existing-test_evidence.zip'
        before = evidence.read_bytes()
        result = survey.attach_existing_runs(self.cfg, self.path, ['existing-test'])
        self.assertEqual(result['steps'][-1]['metrics']['latency_ms'], 12)
        self.assertEqual(result['steps'][-1]['origin'], 'linked')
        self.assertEqual(evidence.read_bytes(), before)
        from veilbreaker.evidence import verify_bundle
        self.assertEqual(verify_bundle(survey.export_session(self.cfg, self.path))['status'], 'verified')
        library.trash_survey(self.cfg, self.path, include_owned_runs=True)
        store = core.VeilbreakerStore(self.cfg.db_path)
        try: self.assertIsNotNone(store.get_run('existing-test'))
        finally: store.close()

    def test_rejections_are_atomic(self):
        before = Path(self.path).read_bytes()
        for ids in ([], ['missing'], ['existing-test', 'missing'], ['existing-test'] * 2):
            with self.assertRaises(ValueError): survey.attach_existing_runs(self.cfg, self.path, ids)
            self.assertEqual(Path(self.path).read_bytes(), before)
        survey.attach_existing_runs(self.cfg, self.path, ['existing-test'])
        with self.assertRaises(ValueError): survey.attach_existing_runs(self.cfg, self.path, ['existing-test'])
        other = survey.create_survey(self.cfg, 'Closed', [{}])['survey_path']
        survey.set_lifecycle(self.cfg, other, True)
        with self.assertRaises(ValueError): survey.attach_existing_runs(self.cfg, other, ['existing-test'])
        full = survey.create_survey(self.cfg, 'Full', [{}] * 20)['survey_path']
        with self.assertRaises(ValueError): survey.attach_existing_runs(self.cfg, full, ['existing-test'])

    def test_picker_selection_and_existing_rows(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from veilbreaker.survey_existing_ui import ExistingDiagnosticsDialog
        app = QApplication.instance() or QApplication([])
        session = survey.read_session(self.cfg, self.path)
        dialog = ExistingDiagnosticsDialog(self.cfg, session)
        self.assertFalse(dialog.add.isEnabled())
        dialog.items.item(0).setCheckState(Qt.CheckState.Checked)
        self.assertEqual(dialog.selected_ids(), ['existing-test'])
        self.assertTrue(dialog.add.isEnabled())
        dialog.search.setText('no matching diagnostic'); dialog.restart()
        self.assertEqual(dialog.selected_ids(), ['existing-test'])
        session = survey.attach_existing_runs(self.cfg, self.path, dialog.selected_ids())
        dialog.close()
        linked = ExistingDiagnosticsDialog(self.cfg, session)
        self.assertFalse(linked.items.item(0).flags() & Qt.ItemFlag.ItemIsEnabled)
        linked.close()
