"""Explicit development USB transport setup; credentials are never settings."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QPushButton
from .android_usb import list_devices

class AndroidUsbDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Live Android USB input')
        self.resize(620, 420)
        layout = QVBoxLayout(self)
        help_text = QLabel('Connect by USB, authorize USB debugging on your phone, select a SIM in Companion 0.2 or newer, and arm a USB session. Keep the companion visible. Enter its new token here. No Wi-Fi connection is used.')
        help_text.setWordWrap(True); layout.addWidget(help_text)
        layout.addWidget(QLabel('ADB executable (platform-tools path, or adb on PATH)'))
        self.path = QLineEdit('adb'); layout.addWidget(self.path)
        refresh = QPushButton('Refresh USB devices'); layout.addWidget(refresh)
        self.devices = QComboBox(); self.devices.addItem('Choose an authorized USB deviceâ€¦', None); layout.addWidget(self.devices)
        layout.addWidget(QLabel('Current companion token (used once; never saved in settings)'))
        self.token = QLineEdit(); self.token.setEchoMode(QLineEdit.EchoMode.Password); layout.addWidget(self.token)
        self.duration = QSpinBox(); self.duration.setRange(5, 300); self.duration.setValue(30); self.duration.setSuffix(' seconds'); layout.addWidget(self.duration)
        self.message = QLabel('Refresh and explicitly select a device.'); self.message.setWordWrap(True); layout.addWidget(self.message)
        use = QPushButton('Use live USB input'); layout.addWidget(use)
        refresh.clicked.connect(self.refresh)
        use.clicked.connect(self.choose)
        cancel = QPushButton('Cancel'); cancel.clicked.connect(self.reject); layout.addWidget(cancel)

    def refresh(self):
        self.devices.clear(); self.devices.addItem('Choose an authorized USB deviceâ€¦', None)
        try:
            for device in list_devices(self.path.text().strip()):
                self.devices.addItem(device['serial'] + ' Â· ' + device['state'], device['serial'] if device['state'] == 'device' else None)
            self.message.setText('Select an authorized USB device. If none appear, check cable, drivers and phone authorization. On Windows, connect only one USB phone while selecting.')
        except Exception:
            self.message.setText('ADB unavailable. Install official Android platform-tools or enter its full executable path.')

    def choose(self):
        import re
        if not self.devices.currentData() or not re.fullmatch('[a-f0-9]{32}', self.token.text().strip()):
            self.message.setText('Select an authorized device and enter the 32-character token shown by Companion.'); return
        self.accept()

    def selection(self):
        return dict(adb_path=self.path.text().strip(), serial=self.devices.currentData(), token=self.token.text().strip(), duration_s=self.duration.value())
