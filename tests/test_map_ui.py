import os,tempfile,unittest,json
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from unittest.mock import patch
from pathlib import Path
from veilbreaker.map_data import build_map_data
from test_map_data import fix
from veilbreaker.map_sources import load_run_map_data,load_survey_map_data
from veilbreaker.map_ui import MapWindow
from PySide6.QtWidgets import QApplication

class SourcesTests(unittest.TestCase):
    def test_missing_bad_and_old_runs(self):
        with tempfile.TemporaryDirectory() as d:
            from veilbreaker.core import AppConfig
            config=AppConfig(data_dir=d)
            rows={'good':dict(report_json=json.dumps({'normalized_metrics':{'location_report':[fix()]}}),artifact_dir=''), 'bad':dict(report_json='{',artifact_dir='')}
            with patch('veilbreaker.map_sources.core.VeilbreakerStore') as store:
                store.return_value.get_run.side_effect=lambda key:rows.get(key)
                self.assertEqual(load_run_map_data(config,'gone')['counts']['mapped'],0)
                p=Path(d)/'survey.json';p.write_text(json.dumps({'steps':[{'run_id':'bad'},{'run_id':'good'},{'run_id':'gone'}]}),encoding='utf-8')
                model=load_survey_map_data(config,p)
                self.assertEqual(model['counts']['mapped'],1);self.assertTrue(model['warnings'])

class MapUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_native_fallback_selection_filters_and_export(self):
        model=build_map_data([dict(run_id='r',label='<script>',locations=[fix(),fix(fix_age_ms=11000),fix(latitude_deg=89)])])
        opened=[];w=MapWindow(None,model,opened.append,enable_web=False,restore_pack=False)
        try:
            self.assertEqual(len(w.visible_features()),1)
            w.bridge.selectFeature('unknown');self.assertIsNone(w.selected)
            w.bridge.selectFeature('p0');w.open_diagnostic();self.assertEqual(opened,['r'])
            w.run_filter.setCurrentIndex(1);w.questionable.setChecked(True)
            self.assertEqual(len(w.visible_features()),3)
            self.assertIn('<script>',w.table.item(0,0).text())
            self.assertIn('unavailable',w.renderer_status.text().lower())
        finally:w.close()
    def test_external_navigation_and_missing_pack(self):
        from veilbreaker.map_web import LocalRequests
        from PySide6.QtCore import QUrl
        gate=LocalRequests('http://127.0.0.1:1234/token/')
        for url in ('https://example.com','file:///C:/Windows/win.ini','http://127.0.0.1:1234/other/'):
            self.assertFalse(gate.permitted(QUrl(url)))
        self.assertTrue(gate.permitted(QUrl('http://127.0.0.1:1234/token/index.html')))
        w=MapWindow(None,build_map_data([]),lambda _:None,enable_web=False,restore_pack=False)
        try:
            with self.assertRaises(OSError):w.load_pack('missing-unavailable-map.pmtiles',persist=False)
            self.assertIsNone(w.server.pack)
        finally:w.close()
    def test_empty_model_closes_service(self):
        w=MapWindow(None,build_map_data([]),lambda _:None,enable_web=False,restore_pack=False)
        w.close();self.assertIsNone(w.server.http)
