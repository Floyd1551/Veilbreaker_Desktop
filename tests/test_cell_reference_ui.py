import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import time
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from veilbreaker.core import AppConfig
from veilbreaker.cell_reference_ui import CellReferenceDialog,import_job
from functools import partial
from test_cell_reference import HEADER,ROW,META

class ReferenceUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_import_and_activation_and_cancel(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=AppConfig(data_dir=tmp);source=Path(tmp)/'test.csv';source.write_text(HEADER+ROW)
            dialog=CellReferenceDialog(None,cfg)
            dialog.start_job(partial(import_job,dialog.root,source,META))
            deadline=time.monotonic()+5
            while dialog.worker is not None and time.monotonic()<deadline:
                self.app.processEvents();time.sleep(.01)
            self.assertIsNone(dialog.worker);self.assertEqual(dialog.datasets.count(),1)
            dialog.activate();self.assertIn('Active',dialog.datasets.currentText())
            dialog.deactivate();self.assertNotIn('Active',dialog.datasets.currentText())
            def slow(cancelled,progress):
                while not cancelled():time.sleep(.005)
                raise ValueError('cancelled')
            dialog.start_job(slow);dialog.reject()
            while dialog.worker is not None and time.monotonic()<deadline:
                self.app.processEvents();time.sleep(.01)
            self.assertIsNone(dialog.worker)

    def test_parent_map_close_defers_running_job(self):
        from PySide6.QtGui import QCloseEvent
        from PySide6.QtCore import Qt
        from veilbreaker.map_ui import MapWindow
        from veilbreaker.map_data import build_map_data
        with tempfile.TemporaryDirectory() as tmp:
            cfg=AppConfig(data_dir=tmp)
            window=MapWindow(None,build_map_data([]),lambda _:None,enable_web=False,restore_pack=False,config=cfg)
            window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,False)
            dialog=CellReferenceDialog(window,cfg)
            def slow(cancelled,progress):
                while not cancelled():time.sleep(.005)
                time.sleep(.1)
                raise ValueError('cancelled')
            dialog.start_job(slow)
            event=QCloseEvent()
            try:
                window.closeEvent(event)
                self.assertFalse(event.isAccepted())
            finally:
                if dialog.worker:dialog.worker.cancelled.set()
                deadline=time.monotonic()+3
                while dialog.worker is not None and time.monotonic()<deadline:
                    self.app.processEvents();time.sleep(.01)
                window.close()
