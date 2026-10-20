"""USB pairing with on-phone approval; no manually entered credentials."""
import os
from pathlib import Path
import shutil
import threading
from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QPushButton
from .android_usb import list_devices, pair_connection


class PairWorker(QThread):
    code = Signal(str)
    paired = Signal(object)
    failed = Signal(str)

    def __init__(self, path, serial, parent):
        super().__init__(parent)
        self.path, self.serial = path, serial
        self.cancelled = threading.Event()

    def run(self):
        try:
            token = pair_connection(self.path, self.serial, self.code.emit, self.cancelled.is_set)
            if not self.cancelled.is_set(): self.paired.emit(token)
        except Exception:
            self.failed.emit('Connection not approved or unavailable. Stop and reconnect in Companion 0.3+, keep it visible, and try again.')


class AndroidUsbDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.phone_inputs = {'cellular': True, 'location': False}
        self.dismiss_pending = False
        self.accept_pending = False
        self.setWindowTitle('Live Android USB input')
        self.resize(620, 420)
        layout = QVBoxLayout(self)
        help_text = QLabel('Connect by USB and approve USB debugging on your phone. In Companion 0.3 or newer, select a SIM and tap Connect to Veilbreaker. Then connect below and approve the matching code on the phone.')
        help_text.setWordWrap(True); layout.addWidget(help_text)
        layout.addWidget(QLabel('ADB executable'))
        candidates = [Path.home()/'Downloads/platform-tools-latest-windows/platform-tools/adb.exe', Path(os.environ.get('LOCALAPPDATA',''))/'Android/Sdk/platform-tools/adb.exe']
        default = shutil.which('adb') or next((str(p) for p in candidates if p.is_file()), 'adb')
        self.path = QLineEdit(default); layout.addWidget(self.path)
        self.refresh_button = QPushButton('Refresh USB devices'); layout.addWidget(self.refresh_button)
        self.devices = QComboBox(); self.devices.addItem('Choose an authorized USB device...', None); layout.addWidget(self.devices)
        # Existing caller clears this transient credential holder after dispatch.
        self.token = QLineEdit(self); self.token.hide()
        self.duration = QSpinBox(); self.duration.setRange(5, 300); self.duration.setValue(30); self.duration.setSuffix(' seconds'); layout.addWidget(self.duration)
        self.code_label = QLabel('No code to type. A matching code will appear here and on the phone.'); self.code_label.setWordWrap(True); layout.addWidget(self.code_label)
        self.message = QLabel('Refresh and explicitly select a device.'); self.message.setWordWrap(True); layout.addWidget(self.message)
        self.use = QPushButton('Connect and use as input'); layout.addWidget(self.use)
        self.refresh_button.clicked.connect(self.refresh)
        self.use.clicked.connect(self.choose)
        cancel = QPushButton('Cancel'); cancel.clicked.connect(self.reject); layout.addWidget(cancel)

    def refresh(self):
        self.devices.clear(); self.devices.addItem('Choose an authorized USB device...', None)
        try:
            for device in list_devices(self.path.text().strip()):
                self.devices.addItem(device['serial'] + ' - ' + device['state'], device['serial'] if device['state'] == 'device' else None)
            self.message.setText('Select an authorized USB device. On Windows, connect only one USB phone while selecting.')
        except Exception:
            self.message.setText('ADB unavailable. Install official Android platform-tools or enter its full executable path.')

    def choose(self):
        if self.worker is not None: return
        if not self.devices.currentData():
            self.message.setText('Select an authorized USB device first.'); return
        self.dismiss_pending = self.accept_pending = False
        self.token.clear()
        for control in (self.path, self.devices, self.duration, self.refresh_button, self.use): control.setEnabled(False)
        self.worker = PairWorker(self.path.text().strip(), self.devices.currentData(), self)
        # Use a QObject receiver, not a lambda retaining this dialog: the latter
        # can crash PySide during deferred worker deletion and cyclic collection.
        self.worker.code.connect(self.show_pairing_code)
        self.worker.paired.connect(self.paired)
        self.worker.failed.connect(self.message.setText)
        self.worker.finished.connect(self.finished_pairing)
        self.message.setText('Waiting for approval on your phone...')
        self.worker.start()

    @Slot(str)
    def show_pairing_code(self, value):
        self.code_label.setText('Confirm on the phone: ' + value)

    @Slot(object)
    def paired(self, token):
        if not self.dismiss_pending:
            self.token.setText(token['token'])
            self.phone_inputs = {key: token[key] for key in ('cellular', 'location')}
            self.accept_pending = True

    @Slot()
    def finished_pairing(self):
        worker, self.worker = self.worker, None
        if worker: worker.deleteLater()
        for control in (self.path, self.devices, self.duration, self.refresh_button, self.use): control.setEnabled(True)
        if self.dismiss_pending: super().reject()
        elif self.accept_pending: super().accept()

    def reject(self):
        if self.worker is not None:
            self.dismiss_pending = True
            self.worker.cancelled.set()
            self.message.setText('Cancelling connection...')
            return
        self.token.clear()
        super().reject()

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore(); self.reject()
        else: super().closeEvent(event)

    def selection(self):
        return dict(adb_path=self.path.text().strip(), serial=self.devices.currentData(), token=self.token.text(), duration_s=self.duration.value(), **self.phone_inputs)
