import json
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox
from veilbreaker.core import AppConfig
from veilbreaker.field_tools import calculate
from veilbreaker.survey import create_survey,read_session,set_lifecycle
from veilbreaker.survey_calculations_ui import CalculationsDialog


class CalculationsUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_attach_saved_snapshot_view_and_remove(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);made=create_survey(cfg,'Walk',[{'label':'Lobby'}]);path=made['survey_path']
            run=made['survey']['steps'][0]['run_id'];source=Path(folder)/'fspl.json'
            source.write_text(json.dumps(calculate('fspl',{'frequency':5800,'distance':2})),encoding='utf-8')
            dialog=CalculationsDialog(None,cfg,path,run)
            try:
                dialog.notes.setText('Donor route');dialog.attach_file(source)
                self.assertEqual(dialog.table.rowCount(),1)
                self.assertEqual(read_session(cfg,path)['calculations'][0]['run_id'],run)
                dialog.table.selectRow(0)
                self.assertIn('Calculated estimate',dialog.details.toPlainText())
                self.assertIn('Donor route',dialog.details.toPlainText())
                with patch('veilbreaker.survey_calculations_ui.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):dialog.remove()
                self.assertEqual(dialog.table.rowCount(),0)
                self.assertTrue(read_session(cfg,path)['calculations'][0]['deleted_utc'])
                dialog.resize(760,650);dialog.show();self.app.processEvents()
                self.assertLessEqual(dialog.width(),760);self.assertLessEqual(dialog.height(),700)
                for widget in (dialog.point,dialog.notes,dialog.attach_button,dialog.remove_button):
                    self.assertLessEqual(widget.mapTo(dialog,widget.rect().bottomRight()).x(),dialog.width())
                    self.assertLessEqual(widget.mapTo(dialog,widget.rect().bottomRight()).y(),dialog.height())
            finally:dialog.close()

    def test_completed_survey_prevents_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);made=create_survey(cfg,'Walk',[{}]);path=made['survey_path']
            set_lifecycle(cfg,path,True);dialog=CalculationsDialog(None,cfg,path)
            try:self.assertFalse(dialog.attach_button.isEnabled());self.assertIn('Reopen',dialog.status.text())
            finally:dialog.close()

    def test_survey_page_opens_editor_at_selected_point(self):
        from veilbreaker.gui import MainWindow
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);made=create_survey(cfg,'Walk',[{'label':'Lobby'}]);window=MainWindow(cfg)
            try:
                page=window.survey_page;page.show_session(made['survey'],made['survey_path']);page.results.selectRow(0)
                run=made['survey']['steps'][0]['run_id']
                with patch('veilbreaker.survey_calculations_ui.CalculationsDialog') as editor:
                    page.open_calculations()
                    editor.assert_called_once_with(window,cfg,made['survey_path'],run)
                    editor.return_value.exec.assert_called_once()
            finally:window.close()
