import os,tempfile,unittest,json,sqlite3
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from unittest.mock import patch
from pathlib import Path
from veilbreaker.map_data import build_map_data
from test_map_data import fix
from veilbreaker.map_sources import load_run_map_data,load_survey_map_data
from veilbreaker.map_ui import MapWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton

class SourcesTests(unittest.TestCase):
    def test_live_single_cell_report_adds_read_only_measured_metric(self):
        with tempfile.TemporaryDirectory() as d:
            from veilbreaker.core import AppConfig
            from test_android_capture import fixture
            from veilbreaker.cellular_report import build_report
            config = AppConfig(data_dir=d)
            artifact = Path(d) / 'artifact'
            artifact.mkdir()
            (artifact / 'collection.json').write_text(json.dumps({'android': {'source_kind': 'live_android_usb'}}), encoding='utf-8')
            capture = fixture()
            capture['collection']['mode'] = 'session'
            row = dict(report_json=json.dumps({'normalized_metrics': {'location_report': [fix()],
                'android_cellular_report': build_report(capture)}}), metrics_json='{}', artifact_dir=str(artifact))
            with patch('veilbreaker.map_sources.core.VeilbreakerStore') as store:
                store.return_value.get_run.return_value = row
                model = load_run_map_data(config, 'live')
            self.assertEqual(model['run_metrics']['live']['live_phone_lte_rsrp'], -95)
            self.assertEqual(model['run_context']['live']['live_phone_lte_rsrp']['sources'], ['android_usb'])
            self.assertEqual(row['metrics_json'], '{}')

    def test_real_sqlite_row_exposes_saved_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            from veilbreaker.core import AppConfig
            config = AppConfig(data_dir=d)
            db = sqlite3.connect(':memory:')
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT ? AS report_json, ? AS metrics_json, ? AS artifact_dir',
                (json.dumps({'normalized_metrics': {'location_report': [fix()]}}),
                 json.dumps({'rsrp': -93}), '')).fetchone()
            with patch('veilbreaker.map_sources.core.VeilbreakerStore') as store:
                store.return_value.get_run.return_value = row
                model = load_run_map_data(config, 'sqlite-run')
            self.assertEqual(model['run_metrics']['sqlite-run'], {'rsrp': -93})
            db.close()

    def test_collection_file_adds_per_metric_source_and_time_without_changing_run(self):
        with tempfile.TemporaryDirectory() as d:
            from veilbreaker.core import AppConfig
            config = AppConfig(data_dir=d)
            artifact = Path(d) / 'artifact'
            artifact.mkdir()
            (artifact / 'collection.json').write_text(json.dumps({
                'metric_sources': {'rsrp': ['cellular_modem'], 'phone_lte_rsrp': ['android_input']},
                'collectors': [{'source': 'cellular_modem', 'started_utc': '2026-10-28T10:00:00Z', 'duration_s': 1.4}],
                'android': {'received_utc': '2026-10-28T09:59:58Z', 'age_ms': 800}}), encoding='utf-8')
            db = sqlite3.connect(':memory:')
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT ? AS report_json, ? AS metrics_json, ? AS artifact_dir',
                (json.dumps({'normalized_metrics': {'location_report': [fix()]}}),
                 json.dumps({'rsrp': -80, 'phone_lte_rsrp': -95}), str(artifact))).fetchone()
            with patch('veilbreaker.map_sources.core.VeilbreakerStore') as store:
                store.return_value.get_run.return_value = row
                model = load_run_map_data(config, 'combined')
            self.assertEqual(model['run_context']['combined']['rsrp']['sources'], ['cellular_modem'])
            self.assertEqual(model['run_context']['combined']['phone_lte_rsrp']['received_utc'], '2026-10-28T09:59:58Z')
            self.assertEqual(model['run_metrics']['combined']['rsrp'], -80)
            db.close()

    def test_live_multicell_capture_is_not_silently_reduced_to_one_phone_point(self):
        with tempfile.TemporaryDirectory() as d:
            from veilbreaker.core import AppConfig
            config = AppConfig(data_dir=d)
            artifact = Path(d) / 'artifact'
            artifact.mkdir()
            (artifact / 'collection.json').write_text(json.dumps({
                'android': {'source_kind': 'live_android_usb'},
                'metric_sources': {'phone_observation_count': ['android_usb']}}), encoding='utf-8')
            db = sqlite3.connect(':memory:')
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT ? AS report_json, ? AS metrics_json, ? AS artifact_dir',
                (json.dumps({'normalized_metrics': {'location_report': [fix()]}}),
                 json.dumps({'phone_observation_count': 3}), str(artifact))).fetchone()
            with patch('veilbreaker.map_sources.core.VeilbreakerStore') as store:
                store.return_value.get_run.return_value = row
                model = load_run_map_data(config, 'live')
            self.assertEqual(model['run_metrics'], {})
            self.assertTrue(any('session details are unavailable' in note for note in model['warnings']))
            db.close()

    def test_saved_run_metrics_follow_survey_map_without_changing_location_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            from veilbreaker.core import AppConfig
            config = AppConfig(data_dir=d)
            row = dict(report_json=json.dumps({'normalized_metrics': {'location_report': [fix()]}}),
                       metrics_json=json.dumps({'rsrp': -91, 'sinr': 8, 'wifi_rssi_dbm': None}), artifact_dir='')
            with patch('veilbreaker.map_sources.core.VeilbreakerStore') as store:
                store.return_value.get_run.return_value = row
                path = Path(d) / 'survey.json'
                path.write_text(json.dumps({'steps': [{'run_id': 'r'}]}), encoding='utf-8')
                model = load_survey_map_data(config, path)
            self.assertEqual(model['run_metrics']['r'], {'rsrp': -91, 'sinr': 8})
            self.assertEqual(model['features']['features'][0]['geometry']['coordinates'], [0, 0])

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

    def test_metric_selector_colors_only_representative_and_preserves_source_model(self):
        model=build_map_data([dict(run_id='a',locations=[fix(),fix(longitude_deg=1)]),
                              dict(run_id='b',locations=[fix(longitude_deg=2)])])
        model['run_metrics']={'a': {'rsrp': -110}, 'b': {'rsrp': -80}}
        w=MapWindow(None,model,lambda _:None,enable_web=False,restore_pack=False)
        try:
            w.metric_selector.setCurrentIndex(w.metric_selector.findData('rsrp'))
            self.assertGreaterEqual(w.source_filter.findData('__unattributed__'), 0)
            rendered=w.server.model['features']['features']
            self.assertEqual({f['id'] for f in rendered}, {'p0', 'p2'})
            self.assertNotEqual(rendered[0]['properties']['metric_color'], rendered[1]['properties']['metric_color'])
            self.assertNotIn('metric_color', model['features']['features'][0]['properties'])
            self.assertIn('relative', w.metric_legend.text().lower())
            self.assertFalse(w.metric_ramp.isHidden())
            self.assertEqual(w.table.horizontalHeaderItem(5).text(), 'Selected run metric')
            self.assertIn('RSRP -110 dBm', w.table.item(0,5).text())
            w.select_feature('p0')
            self.assertIn('RSRP -110 dBm', w.details.text())
            self.assertIn('run metric', w.details.text().lower())
            self.assertIn('Source unrecorded', w.details.text())
        finally:
            w.close()

    def test_missing_metric_is_gray_and_manual_placement_keeps_provenance(self):
        model=build_map_data([dict(run_id='a',locations=[fix()]),dict(run_id='b',locations=[])])
        model['run_metrics']={'a': {'sinr': 5}}
        from veilbreaker.survey_spatial import add_manual_features
        add_manual_features(model, {'placements': {'b': {'kind': 'geographic', 'latitude': 1,
            'longitude': 2, 'placed_utc': '2026-10-28T00:00:00Z'}}},
            [{'run_id': 'a', 'label': 'GPS scan'}, {'run_id': 'b', 'label': 'Manual scan'}])
        w=MapWindow(None,model,lambda _:None,enable_web=False,restore_pack=False)
        try:
            w.metric_selector.setCurrentIndex(w.metric_selector.findData('sinr'))
            rendered=w.server.model['features']['features']
            manual=next(f for f in rendered if f['properties'].get('manual'))
            self.assertNotIn('metric_color', manual['properties'])
            self.assertTrue(w.server.model['metric_mode'])
            w.select_feature(manual['id'])
            self.assertIn('Selected run metric unavailable', w.details.text())
            self.assertIn('Manual placement', w.details.text())
        finally:
            w.close()

    def test_single_observed_metric_uses_neutral_legend(self):
        model=build_map_data([dict(run_id='a',locations=[fix()])])
        model['run_metrics']={'a': {'rsrp': -90}}
        w=MapWindow(None,model,lambda _:None,enable_web=False,restore_pack=False)
        try:
            w.metric_selector.setCurrentIndex(w.metric_selector.findData('rsrp'))
            self.assertIn('single value', w.metric_legend.text().lower())
            self.assertIn('#52b7ca', w.metric_ramp.styleSheet())
        finally:
            w.close()

    def test_map_actions_fit_field_width(self):
        w=MapWindow(None,build_map_data([]),lambda _:None,enable_web=False,restore_pack=False)
        try:
            w.resize(760,640)
            w.show()
            QTest.qWait(30)
            for button in w.findChildren(QPushButton):
                if button.text() in ('Fit measurements', 'Import offline map…', 'Clear basemap', 'Export GeoJSON…'):
                    self.assertLessEqual(button.mapTo(w,button.rect().bottomRight()).x(),w.width(),button.text())
        finally:
            w.close()

    def test_metric_source_filter_changes_points_scale_and_capture_detail(self):
        model=build_map_data([dict(run_id='desktop',locations=[fix()]),
                              dict(run_id='phone',locations=[fix(longitude_deg=2)])])
        model['run_metrics']={'desktop': {'rsrp': -80}, 'phone': {'rsrp': -100}}
        model['run_context']={
            'desktop': {'rsrp': {'sources': ['cellular_modem'], 'started_utc': '2026-10-28T10:00:00Z', 'duration_s': 1.4}},
            'phone': {'rsrp': {'sources': ['android_import'], 'received_utc': '2026-10-28T09:58:00Z', 'age_ms': 100}},
        }
        w=MapWindow(None,model,lambda _:None,enable_web=False,restore_pack=False)
        try:
            w.metric_selector.setCurrentIndex(w.metric_selector.findData('rsrp'))
            self.assertGreaterEqual(w.source_filter.count(),3)
            w.source_filter.setCurrentIndex(w.source_filter.findData('cellular_modem'))
            self.assertEqual([f['properties']['run_id'] for f in w.visible_features()], ['desktop'])
            self.assertIn('single value -80 dBm', w.metric_legend.text())
            w.select_feature('p0')
            self.assertIn('Cellular modem', w.details.text())
            self.assertIn('Collector started 2026-10-28T10:00:00Z', w.details.text())
            w.source_filter.setCurrentIndex(w.source_filter.findData('android_import'))
            self.assertEqual([f['properties']['run_id'] for f in w.visible_features()], ['phone'])
            w.select_feature('p1')
            self.assertIn('Phone observation received 2026-10-28T09:58:00Z', w.details.text())
        finally:w.close()

    def test_attached_phone_lte_metric_has_distinct_selector_and_receipt_context(self):
        model=build_map_data([dict(run_id='combined',locations=[fix()])])
        model['run_metrics']={'combined': {'rsrp': -80, 'phone_lte_rsrp': -95}}
        model['run_context']={'combined': {
            'rsrp': {'sources': ['cellular_modem']},
            'phone_lte_rsrp': {'sources': ['android_input'], 'received_utc': '2026-10-28T09:58:00Z', 'age_ms': 100},
        }}
        w=MapWindow(None,model,lambda _:None,enable_web=False,restore_pack=False)
        try:
            w.metric_selector.setCurrentIndex(w.metric_selector.findData('phone_lte_rsrp'))
            self.assertIn('Phone LTE RSRP', w.metric_selector.currentText())
            w.select_feature('p0')
            self.assertIn('Phone LTE RSRP -95 dBm', w.details.text())
            self.assertIn('Phone observation received', w.details.text())
            self.assertNotIn('Cellular modem', w.details.text())
        finally:w.close()
