import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox
from veilbreaker.core import AppConfig
from veilbreaker.survey import create_survey, read_session, set_lifecycle
from veilbreaker.survey_observations_ui import ObservationsDialog


class ObservationsUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_add_and_remove_observation_for_selected_point(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);made=create_survey(cfg,'Test',[{'label':'Lobby'}]);path=made['survey_path']
            run=made['survey']['steps'][0]['run_id']
            dialog=ObservationsDialog(None,cfg,path,run)
            try:
                dialog.category.setCurrentText('Obstruction')
                dialog.material.setCurrentText('Concrete')
                dialog.description.setPlainText('Pillar by entrance')
                dialog.add()
                self.assertEqual(dialog.table.rowCount(),1)
                self.assertEqual(read_session(cfg,path)['observations'][0]['run_id'],run)
                dialog.table.selectRow(0)
                with patch('veilbreaker.survey_observations_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):
                    dialog.remove()
                self.assertEqual(dialog.table.rowCount(),0)
                self.assertIsNotNone(read_session(cfg,path)['observations'][0]['deleted_utc'])
                dialog.resize(900,650);dialog.show();self.app.processEvents()
                self.assertLessEqual(dialog.width(),900)
                self.assertLessEqual(dialog.height(),700)
            finally:dialog.close()

    def test_completed_survey_remains_readable_but_not_editable(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);made=create_survey(cfg,'Test',[{}]);path=made['survey_path']
            set_lifecycle(cfg,path,True)
            dialog=ObservationsDialog(None,cfg,path)
            try:
                self.assertFalse(dialog.add_button.isEnabled())
                self.assertIn('Reopen',dialog.status.text())
            finally:dialog.close()
