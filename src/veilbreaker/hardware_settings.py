"""Connection forms only: editing these controls never opens a device."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QComboBox, QSpinBox


class HardwareSettings:
    def __init__(self, tabs, config):
        self.fields = {}
        specs = [
            ("Cellular", "Read-only modem connection. Choose Cellular on Diagnostics to collect. Automatic discovery only probes likely modem ports.", [
                ("cellular.port", "Serial port", "text", "auto, COM5 or /dev/ttyUSB2"),
                ("cellular.driver", "Modem driver", "choice", [("Automatic", "auto"), ("Generic 3GPP", "generic_3gpp"), ("Sierra EM9", "sierra_em9"), ("Quectel RM5xx / RG5xx", "quectel_rm5xx")]),
                ("cellular.backend", "Collection backend", "choice", [("Automatic", "auto"), ("Serial AT", "serial"), ("External JSON adapter", "json")]),
            ], "Blank serial port uses automatic discovery. Adapter commands, baud rate, raw responses and device identifiers remain in Advanced JSON."),
            ("Starlink", "Read telemetry from the terminal management endpoint. Choose Starlink on Diagnostics to collect.", [
                ("starlink.host", "Terminal host", "text", "192.168.100.1"),
                ("starlink.port", "Management port", "port", None),
                ("starlink.backend", "Collection backend", "choice", [("Automatic", "auto"), ("External grpcurl", "grpcurl"), ("Python integration", "python")]),
            ], "Frozen packages use separately installed grpcurl. Location collection stays at its existing setting in Advanced JSON."),
            ("HackRF", "Choose the receiver and local host tools used for receive-only SDR acquisition.", [
                ("sdr.tools_dir", "Host tools folder", "text", "Blank: discover installed tools"),
                ("sdr.serial", "Receiver serial", "text", "Blank: use the available receiver"),
            ], "Receive presets, gains and sweep controls are in Tools & readiness. Diagnostic sweep ranges and power settings remain in Advanced JSON. Saving does not change them."),
        ]
        for title, introduction, fields, hint in specs:
            panel = QWidget()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(16)
            for text in (introduction,):
                note = QLabel(text)
                note.setWordWrap(True)
                note.setObjectName("muted")
                layout.addWidget(note)
            form = QFormLayout()
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            for key, name, kind, values in fields:
                if kind == "choice":
                    control = QComboBox()
                    for caption, value in values:
                        control.addItem(caption, value)
                elif kind == "port":
                    control = QSpinBox()
                    control.setRange(1, 65535)
                else:
                    control = QLineEdit()
                    control.setPlaceholderText(values)
                    control.setClearButtonEnabled(True)
                control.setAccessibleName(name)
                self.fields[key] = control
                form.addRow(name, control)
            layout.addLayout(form)
            note = QLabel(hint)
            note.setWordWrap(True)
            note.setObjectName("muted")
            layout.addWidget(note)
            layout.addStretch()
            tabs.addTab(panel, title)
        self.sync(config)

    def sync(self, config):
        for key, control in self.fields.items():
            section, name = key.split(".")
            value = getattr(getattr(config, section), name)
            if isinstance(control, QComboBox):
                index = control.findData(value)
                if index < 0:
                    control.addItem(str(value), value)
                    index = control.count() - 1
                control.setCurrentIndex(index)
            elif isinstance(control, QSpinBox):
                control.setValue(value)
            else:
                control.setText(value or "")

    def values(self):
        return {key: control.currentData() if isinstance(control, QComboBox)
                else control.value() if isinstance(control, QSpinBox) else control.text()
                for key, control in self.fields.items()}
