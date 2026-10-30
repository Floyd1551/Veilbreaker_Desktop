import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication, QMessageBox
from veilbreaker.core import AppConfig
from veilbreaker.survey import create_survey, read_session, set_lifecycle
from veilbreaker.survey_observations_ui import ObservationsDialog


class ObservationsUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_photo_actions_follow_selection_and_completion(self):
        from veilbreaker.survey_observations import add_observation
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);path=create_survey(cfg,'Test',[{}])['survey_path']
            add_observation(cfg,path,dict(run_id=None,category='Other',material='Unknown',description='Fixture',author=''))
            image=QImage(5,5,QImage.Format.Format_RGB32);image.fill(QColor('blue'))
            image_path=Path(folder)/'photo.png';image.save(str(image_path))
            dialog=ObservationsDialog(None,cfg,path)
            try:
                self.assertFalse(dialog.photo_button.isEnabled())
                dialog.table.selectRow(0)
                with patch('veilbreaker.survey_observations_ui.QFileDialog.getOpenFileName',return_value=(str(image_path),'')):
                    dialog.attach_photo()
                dialog.table.selectRow(0)
                self.assertTrue(dialog.view_photo_button.isEnabled())
                self.assertTrue(dialog.remove_photo_button.isEnabled())
                dialog.resize(760,650);dialog.show();self.app.processEvents()
                self.assertLessEqual(dialog.width(),760)
                set_lifecycle(cfg,path,True);dialog.refresh();dialog.table.selectRow(0)
                self.assertTrue(dialog.view_photo_button.isEnabled())
                self.assertFalse(dialog.photo_button.isEnabled())
                self.assertFalse(dialog.remove_photo_button.isEnabled())
            finally:dialog.close()

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

    def test_edit_selected_and_cancel_leave_provenance_intact(self):
        from veilbreaker.survey_observations import add_observation
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);made=create_survey(cfg,'Test',[{'label':'Lobby'}]);path=made['survey_path']
            first=add_observation(cfg,path,dict(run_id=None,category='Other',material='Unknown',description='Original',author=''))
            dialog=ObservationsDialog(None,cfg,path)
            try:
                dialog.table.selectRow(0);dialog.start_edit()
                self.assertEqual(dialog.description.toPlainText(),'Original')
                dialog.resize(760,650);dialog.show();self.app.processEvents()
                self.assertLessEqual(dialog.width(),760)
                for control in (dialog.add_button,dialog.edit_button,dialog.cancel_button,dialog.remove_button):
                    self.assertLessEqual(control.mapTo(dialog,control.rect().bottomRight()).x(),dialog.width())
                dialog.description.setPlainText('Discard me');dialog.cancel_edit()
                self.assertEqual(read_session(cfg,path)['observations'][0]['description'],'Original')
                dialog.table.selectRow(0);dialog.start_edit()
                dialog.description.setPlainText('Corrected');dialog.add()
                row=read_session(cfg,path)['observations'][0]
                self.assertEqual(row['description'],'Corrected')
                self.assertEqual(row['recorded_utc'],first['recorded_utc'])
                self.assertEqual(row['history'][0]['previous']['description'],'Original')
                self.assertIsNone(dialog.editing_id)
            finally:dialog.close()

    def test_edit_detects_change_since_open(self):
        from veilbreaker.survey_observations import add_observation, update_observation
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);made=create_survey(cfg,'Test',[{}]);path=made['survey_path']
            values=dict(run_id=None,category='Other',material='Unknown',description='Original',author='')
            first=add_observation(cfg,path,values)
            dialog=ObservationsDialog(None,cfg,path)
            try:
                dialog.table.selectRow(0);dialog.start_edit()
                update_observation(cfg,path,first['id'],dict(values,description='External update'),expected_revision=0)
                dialog.description.setPlainText('Stale update');dialog.add()
                self.assertIn('changed',dialog.status.text())
                self.assertEqual(read_session(cfg,path)['observations'][0]['description'],'External update')
                dialog.cancel_edit()
                dialog.table.selectRow(0);dialog.start_edit()
                self.assertEqual(dialog.description.toPlainText(),'External update')
                dialog.description.setPlainText('Reviewed update');dialog.add()
                self.assertEqual(read_session(cfg,path)['observations'][0]['description'],'Reviewed update')
            finally:dialog.close()

    def test_delete_rejects_a_stale_observation_and_refreshes(self):
        from veilbreaker.survey_observations import add_observation, update_observation
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);made=create_survey(cfg,'Test',[{}]);path=made['survey_path']
            values=dict(run_id=None,category='Other',material='Unknown',description='Original',author='')
            first=add_observation(cfg,path,values)
            dialog=ObservationsDialog(None,cfg,path)
            try:
                dialog.table.selectRow(0)
                update_observation(cfg,path,first['id'],dict(values,description='External update'),expected_revision=0)
                with patch('veilbreaker.survey_observations_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):
                    dialog.remove()
                self.assertIn('changed',dialog.status.text())
                self.assertEqual(dialog.table.item(0,3).text(),'External update')
                self.assertNotIn('deleted_utc',read_session(cfg,path)['observations'][0])
            finally:dialog.close()

    def test_operator_can_view_edit_history_even_after_survey_completion(self):
        from veilbreaker.survey_observations import add_observation,update_observation
        from PySide6.QtWidgets import QDialog
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);made=create_survey(cfg,'Test',[{'label':'Lobby'}]);path=made['survey_path']
            run=made['survey']['steps'][0]['run_id']
            values=dict(run_id=run,category='Obstruction',material='Concrete',description='First description',author='Field engineer')
            row=add_observation(cfg,path,values)
            update_observation(cfg,path,row['id'],dict(values,description='Corrected description'),expected_revision=0)
            set_lifecycle(cfg,path,True)
            dialog=ObservationsDialog(None,cfg,path)
            try:
                dialog.table.selectRow(0)
                self.assertTrue(dialog.history_button.isEnabled())
                with patch.object(QDialog,'exec',return_value=0):
                    dialog.view_history()
                detail=dialog.history_view.toPlainText()
                self.assertIn('First description',detail)
                self.assertIn('Corrected description',detail)
                self.assertIn('Lobby',detail)
            finally:dialog.close()
