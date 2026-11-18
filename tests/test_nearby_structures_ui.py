import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QLabel
from veilbreaker.core import AppConfig
from veilbreaker.nearby_structures_ui import NearbyStructuresDialog, receiver_endpoint_context, _search_job, _verify_job
from veilbreaker.regional_packs import RegionalPackStore


def receiver(**changes):
    row = dict(id='p0', run_id='run-1', label='Point A', observation_id='obs-1',
               latitude_deg=34.7, longitude_deg=-86.6, source='phone', fix_age_ms=500,
               quality=dict(qualified=True, label='Qualified GPS', reasons=[]), renderable=True)
    row.update(changes)
    return row


def candidate():
    return dict(structure_id='ASR-101', owner='Example', height_agl_m=50, lat=34.71, lon=-86.59,
                distance_m=1450, bearing_deg=40, reference_kind='physical structure',
                verification='Physical structure reference; serving relationship unverified',
                pack_id='a'*32, pack_name='Example pack', source='FCC', source_date='2026-10-25',
                license='Public domain', sha256='b'*64, bounds_wgs84=[-87, 34, -86, 35], coverage_note='Partial')


class NearbyStructureUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_endpoint_keeps_manual_placement_distinct_and_does_not_mutate_input(self):
        row = receiver(manual=True, source='operator', observation_id='Operator placement',
                       placed_utc='2026-11-18T12:00:00Z', quality={'qualified': False, 'label': 'Manual placement'})
        before = copy.deepcopy(row)
        context = receiver_endpoint_context(row, candidate())
        self.assertEqual(context['observation']['position_source'], 'operator_map_placement')
        self.assertEqual(context['observation']['location']['source'], 'operator')
        self.assertEqual(context['candidate']['selection_method'], 'operator_selected')
        self.assertEqual(row, before)

    def test_rejects_unqualified_gps_and_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            receiver_endpoint_context(receiver(quality={'qualified': False}), candidate())
        with self.assertRaises(ValueError):
            receiver_endpoint_context(receiver(latitude_deg=float('nan')), candidate())
        with self.assertRaises(ValueError):
            receiver_endpoint_context(receiver(manual=True, source='phone', quality={'qualified': False}), candidate())

    def test_network_provider_is_not_described_as_gps(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = receiver(source='phone', provider='network')
            dialog = NearbyStructuresDialog(None, AppConfig(data_dir=tmp), row)
            try:
                labels = ' '.join(label.text() for label in dialog.findChildren(QLabel))
                self.assertIn('Qualified recorded location', labels)
                self.assertIn('network', labels)
                self.assertIn('phone', labels)
                self.assertNotIn('Qualified GPS fix', labels)
                self.assertEqual(receiver_endpoint_context(row, candidate())['observation']['position_source'], 'qualified_location')
            finally:
                dialog.close()

    def test_receiver_snapshot_preserves_fix_provenance_for_stale_checks(self):
        row = receiver(provider='gps', fix_utc='2026-11-18T12:00:00Z',
                       received_utc='2026-11-18T12:00:01Z', horizontal_accuracy_m=4.2,
                       fix_age_ms=500, mock=False)
        snapshot = receiver_endpoint_context(row, candidate())['map_receiver']
        for key in ('source', 'provider', 'fix_utc', 'received_utc',
                    'horizontal_accuracy_m', 'fix_age_ms', 'mock'):
            self.assertEqual(snapshot[key], row[key])
        self.assertNotIn('received_utc', receiver_endpoint_context(receiver(), candidate())['map_receiver'])

    def test_result_selection_is_explicit_and_search_results_show_limitations(self):
        with tempfile.TemporaryDirectory() as tmp:
            seen = []
            dialog = NearbyStructuresDialog(None, AppConfig(data_dir=tmp), receiver(), on_map=lambda r, c: seen.append((r, c)))
            try:
                self.assertFalse(dialog.map_button.isEnabled())
                dialog.job_ready({'kind': 'search', 'result': {'candidates': [candidate()], 'packs': [],
                                  'total_matches': 1, 'truncated': False, 'warnings': ['Incomplete coverage']}})
                self.assertEqual(dialog.table.rowCount(), 1)
                self.assertIn('Incomplete coverage', dialog.status.text())
                self.assertEqual(seen, [])
                dialog.table.selectRow(0)
                self.assertTrue(dialog.map_button.isEnabled())
                with patch.object(dialog, 'start_job') as start:
                    dialog.show_selected()
                    self.assertTrue(start.called)
                self.assertEqual(seen, [])
            finally:
                dialog.close()

    def test_report_and_export_require_accepted_assessment(self):
        with tempfile.TemporaryDirectory() as tmp:
            dialog = NearbyStructuresDialog(None, AppConfig(data_dir=tmp), receiver())
            try:
                self.assertFalse(dialog.report_button.isEnabled())
                self.assertFalse(dialog.export_button.isEnabled())
            finally:
                dialog.close()

    def test_real_search_and_verify_detect_changed_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'structures.geojson'
            source.write_text(json.dumps({'type': 'FeatureCollection', 'features': [
                {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-86.6, 34.7]},
                 'properties': {'structure_id': 'point', 'height_agl_m': 50}}]}), encoding='utf-8')
            store = RegionalPackStore(root / 'regional-packs')
            pack = store.install_local('structures', source, {'name': 'test', 'source': 'registry',
                'source_date': '2026-11-18', 'license': 'public', 'bounds_wgs84': [-87, 34, -86, 35]}, lambda: False)
            results = _search_job(root / 'regional-packs', 34.7, -86.6, 10, lambda: False, lambda _: None)['result']
            item = results['candidates'][0]
            verified = _verify_job(root / 'regional-packs', item, 'map', lambda: False, lambda _: None)
            self.assertEqual(verified['candidate']['structure_id'], 'point')
            path = store.data_path(pack['pack_id'])
            path.write_bytes(path.read_bytes().replace(b'point', b'other'))
            with self.assertRaises(ValueError):
                _verify_job(root / 'regional-packs', item, 'map', lambda: False, lambda _: None)

    def test_explicit_selection_map_callback_has_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            seen = []
            row = receiver(source_kind='mobile', mobile_capture_id='capture-1', mobile_survey_sha256='c'*64)
            dialog = NearbyStructuresDialog(None, AppConfig(data_dir=tmp), row, on_map=lambda r, c: seen.append((r, c)))
            try:
                context = receiver_endpoint_context(row, candidate())
                self.assertEqual(context['map_receiver']['mobile_capture_id'], 'capture-1')
                self.assertEqual(context['map_receiver']['mobile_survey_sha256'], 'c'*64)
                self.assertFalse(context['map_receiver']['manual'])
                dialog.job_ready({'kind': 'verified', 'candidate': candidate(), 'action': 'map'})
                self.assertEqual(seen[0][0], row)
                self.assertEqual(seen[0][1]['selection_method'], 'operator_selected')
            finally:
                dialog.close()

    def test_failed_survey_save_keeps_assessment_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            def reject(_):
                raise ValueError('Survey changed')
            dialog = NearbyStructuresDialog(None, AppConfig(data_dir=tmp), receiver(), on_assessment=reject)
            try:
                with patch('veilbreaker.path_assessment_ui.PathAssessmentDialog') as assessment_dialog:
                    assessment_dialog.return_value.exec.return_value = True
                    assessment_dialog.return_value.assessment = {'example': 'assessment'}
                    dialog.job_ready({'kind': 'verified', 'candidate': candidate(), 'action': 'assess'})
                self.assertEqual(dialog.assessment, {'example': 'assessment'})
                self.assertIn('Survey changed', dialog.status.text())
                self.assertTrue(dialog.export_button.isEnabled())
                self.assertTrue(dialog.save_button.isEnabled())
                dialog.on_assessment = lambda _: 'Saved on retry'
                dialog.save_assessment()
                self.assertIn('Saved on retry', dialog.status.text())
                self.assertFalse(dialog.save_button.isEnabled())
            finally:
                dialog.close()


if __name__ == '__main__':
    unittest.main()
