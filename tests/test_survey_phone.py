import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from veilbreaker import core, survey, jobs
from veilbreaker.survey_flow import next_point_context


class SurveyPhoneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.cfg = core.AppConfig(data_dir=self.temp.name)
        self.path = survey.create_survey(self.cfg, 'Walk', [{}, {}], manual=False)['survey_path']
        self.context = next_point_context(self.cfg, self.path)['context']
        self.phone = dict(adb_path='adb', serial='ABC', token='a'*32, duration_s=5, cellular=True, location=True)

    def request(self):
        return dict(action='survey_phone', config=self.cfg.to_dict(), survey_path=self.path,
                    expected_context=self.context, options={'android_live': self.phone})

    def test_phone_stops_after_one_point_and_never_persists_credentials(self):
        with patch.object(core.VeilbreakerApplication, 'run', return_value=SimpleNamespace(collection={'status':'partial'})) as run:
            result = jobs.execute(self.request())
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.kwargs['android_live'], self.phone)
        self.assertEqual([s['status'] for s in result['survey']['steps']], ['partial','planned'])
        self.assertFalse(result['survey']['manual'])
        for p in Path(self.temp.name).rglob('*.json'):
            self.assertNotIn(self.phone['token'], p.read_text(encoding='utf-8'))
        self.assertNotIn(self.phone['token'], json.dumps(result))

    def test_changed_point_rejected_without_mutating_journal(self):
        data = json.loads(Path(self.path).read_text()); data['steps'][0]['settings']['site_id']='changed'
        Path(self.path).write_text(json.dumps(data)); before=Path(self.path).read_bytes()
        with self.assertRaisesRegex(ValueError, 'changed'):
            jobs.execute(self.request())
        self.assertEqual(Path(self.path).read_bytes(), before)

    def test_cancelled_before_start_does_not_attempt_point(self):
        marker=Path(self.temp.name)/'cancel'; marker.touch()
        request=self.request();request['cancel_path']=str(marker)
        before=Path(self.path).read_bytes()
        with self.assertRaisesRegex(ValueError,'cancelled'):
            jobs.execute(request)
        self.assertEqual(Path(self.path).read_bytes(),before)

    def test_invalid_phone_configuration_does_not_attempt_point(self):
        self.phone['duration_s']=301
        before=Path(self.path).read_bytes()
        with self.assertRaises(ValueError): jobs.execute(self.request())
        self.assertEqual(Path(self.path).read_bytes(),before)

    def test_actual_phone_evidence_is_saved_under_point(self):
        from veilbreaker.evidence import verify_bundle
        capture=json.loads(Path('examples/android-cellular-v1.json').read_text())
        capture['collection']['outcome']='partial'
        with patch.object(core.VeilbreakerApplication,'collect_passive',return_value=({},[])), patch('veilbreaker.android_usb.collect_session',return_value=capture):
            result=jobs.execute(self.request())
        point=result['survey']['steps'][0]
        self.assertEqual(point['status'],'partial')
        self.assertTrue((self.cfg.artifacts_dir/point['run_id']/'android-capture.json').exists())
        self.assertEqual(verify_bundle(result['evidence_zip'])['status'],'verified')

    def test_failure_message_cannot_persist_pairing_token(self):
        with patch.object(core.VeilbreakerApplication,'run',side_effect=RuntimeError(self.phone['token'])):
            result=jobs.execute(self.request())
        self.assertEqual(result['survey']['steps'][0]['status'],'failed')
        self.assertNotIn(self.phone['token'],Path(self.path).read_text())

    def test_completed_survey_rejects_phone_capture(self):
        survey.set_lifecycle(self.cfg,self.path,True)
        before=Path(self.path).read_bytes()
        with self.assertRaisesRegex(ValueError,'Reopen'):jobs.execute(self.request())
        self.assertEqual(Path(self.path).read_bytes(),before)


class SurveyPhoneGuiTests(unittest.TestCase):
    def test_pair_and_dispatch_from_survey(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication,QDialog
        from veilbreaker.gui import MainWindow
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            cfg=core.AppConfig(data_dir=tmp);window=MainWindow(cfg)
            try:
                saved=survey.create_survey(cfg,'Walk',[{},{}],manual=False)
                window.survey_page.show_session(saved['survey'],saved['survey_path'])
                with patch('veilbreaker.android_usb_ui.AndroidUsbDialog') as dialog, patch.object(window,'start_job') as start:
                    dialog.return_value.exec.return_value=QDialog.DialogCode.Accepted
                    selection=dict(adb_path='adb',serial='ABC',token='a'*32,duration_s=5,cellular=True,location=False)
                    dialog.return_value.selection.return_value=selection
                    window.survey_page.flow.capture_phone()
                    self.assertEqual(start.call_args.args,('survey_phone',))
                    self.assertEqual(start.call_args.kwargs['survey_path'],saved['survey_path'])
                    self.assertEqual(start.call_args.kwargs['options']['android_live'],selection)
                    dialog.return_value.token.clear.assert_called_once()
                self.assertIsNone(getattr(window,'android_live',None))
            finally:window.close();app.processEvents()
