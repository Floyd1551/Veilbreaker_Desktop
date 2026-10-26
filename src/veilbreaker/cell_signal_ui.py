"""Standalone cellular signal interpretation panel for field reference."""
from html import escape

from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QLabel,
                               QLineEdit, QPushButton, QTextBrowser, QVBoxLayout, QWidget)

from .cell_signal_tools import METRICS, interpret_signal


class CellSignalPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel('Cellular signal interpreter')
        title.setObjectName('section')
        layout.addWidget(title)
        caption = QLabel('Enter only metrics your phone or modem exposes for one cell at one time. Blank means unavailable; zero is a real value. This standalone guide does not import or alter diagnostic evidence.')
        caption.setWordWrap(True)
        layout.addWidget(caption)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.radio = QComboBox()
        self.radio.addItems(('LTE', 'NR'))
        self.radio.setAccessibleName('Signal radio technology')
        form.addRow('Radio', self.radio)
        self.inputs = {}
        for key in ('rsrp', 'rsrq', 'sinr'):
            entry = QLineEdit()
            self.inputs[key] = entry
            entry.textChanged.connect(self.invalidate)
            form.addRow(key.upper(), entry)
        layout.addLayout(form)
        self.form = form
        self.calculate_button = QPushButton('Interpret entered metrics')
        self.calculate_button.clicked.connect(self.interpret)
        layout.addWidget(self.calculate_button)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.result = QTextBrowser()
        self.result.setAccessibleName('Cellular signal explanation and next checks')
        self.result.setOpenExternalLinks(True)
        layout.addWidget(self.result, 1)
        self.copy_button = QPushButton('Copy interpretation')
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.result.toPlainText()))
        layout.addWidget(self.copy_button)
        self.radio.currentTextChanged.connect(self.change_radio)
        self.change_radio()

    def change_radio(self, *_):
        for key, label, source_key, _ in METRICS[self.radio.currentText()]:
            widget = self.inputs[key]
            widget.clear()
            widget.setAccessibleName(f'{label} ({source_key})')
            self.form.labelForField(widget).setText(label)
        self.invalidate()

    def invalidate(self, *_):
        self.result.clear()
        self.status.clear()
        self.copy_button.setEnabled(False)

    def interpret(self):
        self.invalidate()
        try:
            output = interpret_signal(self.radio.currentText(),
                                      {key: widget.text().strip() for key, widget in self.inputs.items()})
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        lines = ['<h3>Entered signal metrics</h3>',
                 '<p><b>Operator-entered interpretation — not captured evidence.</b></p>',
                 '<table border="1" cellspacing="0" cellpadding="6"><tr><th>Metric</th><th>Entered value</th><th>Broad guidance</th><th>Meaning</th></tr>']
        for row in output['rows']:
            cells = (row['label'], f"{row['value']:g} {row['unit']}", row['guidance'], row['meaning'])
            lines.append('<tr>' + ''.join('<td>' + escape(value) + '</td>' for value in cells) + '</tr>')
        lines.append('</table>')
        if output['missing']:
            lines.append('<p>Unavailable: ' + escape(', '.join(output['missing'])) + '. These are omitted, not zero.</p>')
        pattern = output['pattern']
        limits = output['thresholds']
        power_label = 'RSRP' if output['radio'] == 'LTE' else 'SS-RSRP'
        lines.extend((f"<h3>{escape(pattern['title'])}</h3>",
                      f"<p>{escape(pattern['explanation'])}</p>",
                      f"<p><b>Next check:</b> {escape(pattern['next'])}</p>",
                      f"<p><b>Default guide cutoffs:</b> {power_label} ≥ {limits['rsrp_good_dbm']:g} dBm is relatively strong; "
                      f"{power_label} ≤ {limits['rsrp_fair_dbm']:g} dBm is low; "
                      f"SINR &lt; {limits['sinr_fair_db']:g} dB is low; "
                      f"SINR ≥ {limits['sinr_good_db']:g} dB is comparatively good; "
                      f"RSRQ ≤ {limits['rsrq_fair_db']:g} dB is low. These are Veilbreaker field guidance thresholds, not service guarantees.</p>",
                      f"<p><b>Method:</b> {escape(output['method'])}</p>",
                      f"<p><b>Limits:</b> {escape(output['limitations'])}</p>",
                      '<p>Definitions: <a href="https://developer.android.com/reference/android/telephony/CellSignalStrengthLte">'
                      'Android LTE measurements</a> and <a href="https://developer.android.com/reference/android/telephony/CellSignalStrengthNr">'
                      'Android NR measurements</a>. Links require internet; this interpretation works offline.</p>'))
        self.result.setHtml(''.join(lines))
        self.status.setText('Interpretation uses broad field guidance. Preserve the original device reading separately.')
        self.copy_button.setEnabled(True)
