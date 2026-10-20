"""Exercise pairing cleanup in a real Qt event loop, isolated from the test runner."""
import os
import subprocess
import sys
import unittest


class PairingLifetimeTests(unittest.TestCase):
    def test_repeated_pairing_survives_deferred_worker_destruction(self):
        script = r'''
import faulthandler, gc, sys, tempfile, time
faulthandler.enable()
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from veilbreaker.gui import MainWindow
from veilbreaker.core import AppConfig
from veilbreaker import android_usb_ui as ui
app = QApplication([])
temp = tempfile.TemporaryDirectory()
window = MainWindow(AppConfig(data_dir=temp.name))
mode = sys.argv[1]
def pair(path, serial, show_code, cancelled):
    show_code('123456')
    time.sleep(.01)
    if mode == 'failure':
        raise ValueError('Phone unavailable')
    if mode == 'cancel':
        while not cancelled():
            time.sleep(.005)
    return dict(token='a'*32, cellular=True, location=False)
ui.pair_connection = pair
original_exec = ui.AndroidUsbDialog.exec
def auto_exec(dialog):
    dialog.devices.addItem('Test phone', 'ABC')
    dialog.devices.setCurrentIndex(1)
    QTimer.singleShot(0, dialog.use.click)
    if mode != 'success':
        QTimer.singleShot(30, dialog.reject)
    return original_exec(dialog)
ui.AndroidUsbDialog.exec = auto_exec
completed = 0
def connect():
    global completed
    window.configure_android_usb()
    if mode == 'success':
        assert window.android_live['cellular'] is True
    else:
        assert getattr(window, 'android_live', None) is None
    gc.collect()
    completed += 1
    if completed < 10:
        QTimer.singleShot(10, connect)
    else:
        QTimer.singleShot(50, app.quit)
QTimer.singleShot(0, connect)
QTimer.singleShot(10000, app.quit)
app.exec()
assert completed == 10, completed
window.close()
temp.cleanup()
print('Pairing cleanup passed')
'''
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
        for mode in ('success', 'failure', 'cancel'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, '-c', script, mode], env=env,
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('Pairing cleanup passed', result.stdout)
