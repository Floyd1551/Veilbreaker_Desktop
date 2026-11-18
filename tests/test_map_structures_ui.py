import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from veilbreaker.core import AppConfig
from veilbreaker.map_data import build_map_data
from veilbreaker.map_ui import MapWindow
from veilbreaker.survey_spatial import add_manual_features
from test_map_data import fix


class MapStructureWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_requires_selected_qualified_or_manual_position(self):
        with tempfile.TemporaryDirectory() as folder:
            model = build_map_data([dict(run_id='one', locations=[fix()])])
            window = MapWindow(None, model, None, enable_web=False, restore_pack=False, config=AppConfig(data_dir=folder))
            try:
                self.assertFalse(window.structures_button.isEnabled())
                window.select_feature(model['rows'][0]['id'])
                self.assertTrue(window.structures_button.isEnabled())
                window.structures_button.click()
                self.assertEqual(window.structure_dialog.receiver['run_id'], 'one')
                self.assertFalse(window.structure_dialog.receiver.get('manual', False))
            finally:
                if getattr(window, 'structure_dialog', None): window.structure_dialog.close()
                window.close()

    def test_manual_placement_remains_operator_entered_and_overlay_distinct(self):
        with tempfile.TemporaryDirectory() as folder:
            model = build_map_data([dict(run_id='one', locations=[])])
            add_manual_features(model, {'placements': {'one': {'kind': 'geographic', 'latitude': 34.7,
                'longitude': -86.6, 'placed_utc': '2026-11-18T12:00:00Z'}}}, [{'run_id': 'one'}])
            window = MapWindow(None, model, None, enable_web=False, restore_pack=False, config=AppConfig(data_dir=folder))
            try:
                window.select_feature('manual-0')
                self.assertTrue(window.structures_button.isEnabled())
                receiver = window.selected.copy()
                window.show_structure_candidate(receiver, {'lat': 34.71, 'lon': -86.59})
                self.assertEqual(window.cell_overlay['kind'], 'physical_structure')
                self.assertTrue(window.cell_overlay['receiver_manual'])
                self.assertIn('operator', window.details.text().lower())
                self.assertIn('not', window.details.text().lower())
            finally: window.close()

    def test_bad_or_questionable_location_cannot_open_nearby_query(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = fix(); bad['mock'] = True
            model = build_map_data([dict(run_id='one', locations=[bad])])
            window = MapWindow(None, model, None, enable_web=False, restore_pack=False, config=AppConfig(data_dir=folder))
            try:
                window.questionable.setChecked(True)
                window.select_feature(model['rows'][0]['id'])
                self.assertFalse(window.structures_button.isEnabled())
            finally: window.close()


if __name__ == '__main__':
    unittest.main()
