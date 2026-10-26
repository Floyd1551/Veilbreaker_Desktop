"""Cellular channel inspector in the offline Tools workspace."""
from PySide6.QtWidgets import (QComboBox, QFormLayout, QLabel, QLineEdit,
                               QPushButton, QTextBrowser, QVBoxLayout, QWidget)

from .cell_channel_tools import inspect_channel, nr_mhz_to_arfcn


class CellChannelPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        heading = QLabel('Cellular channel inspector')
        heading.setObjectName('section')
        layout.addWidget(heading)
        caption = QLabel('Look up possible LTE/NR bands from a channel number. NR uses the global frequency raster. Results are reference context, not measured cells or carrier attribution.')
        caption.setWordWrap(True)
        layout.addWidget(caption)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.radio = QComboBox()
        self.radio.addItems(('LTE', 'NR'))
        self.radio.setAccessibleName('Cellular radio technology')
        form.addRow('Radio', self.radio)
        self.channel = QLineEdit('6300')
        self.channel.setAccessibleName('EARFCN or NR-ARFCN')
        form.addRow('Channel number', self.channel)
        layout.addLayout(form)
        button = QPushButton('Inspect channel')
        button.clicked.connect(self.inspect)
        self.channel.returnPressed.connect(self.inspect)
        layout.addWidget(button)
        self.result = QTextBrowser()
        self.result.setAccessibleName('Channel frequency and candidate bands')
        layout.addWidget(self.result, 1)
        reverse = QFormLayout()
        reverse.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.frequency = QLineEdit()
        self.frequency.setPlaceholderText('Example: 3500')
        self.frequency.setAccessibleName('NR frequency in MHz')
        reverse.addRow('NR center frequency (MHz)', self.frequency)
        layout.addLayout(reverse)
        reverse_button = QPushButton('Find NR-ARFCN')
        reverse_button.clicked.connect(self.reverse_lookup)
        self.frequency.returnPressed.connect(self.reverse_lookup)
        layout.addWidget(reverse_button)
        self.reverse_result = QLabel()
        self.reverse_result.setWordWrap(True)
        layout.addWidget(self.reverse_result)
        source = QLabel('Offline references: bundled AOSP channel-band candidate table (version shown in result); 3GPP TS 38.104 NR global frequency raster. Band candidates can overlap and may differ from what a modem reports.')
        source.setWordWrap(True)
        layout.addWidget(source)
        self.radio.currentTextChanged.connect(self.clear)
        self.channel.textChanged.connect(self.clear)
        self.frequency.textChanged.connect(self.clear_reverse)

    def clear(self, *_):
        self.result.clear()

    def clear_reverse(self, *_):
        self.reverse_result.clear()

    def inspect(self):
        self.clear()
        try:
            raw = self.channel.text().strip()
            if not raw.isascii() or not raw.isdecimal():
                raise ValueError('Enter a nonnegative whole channel number.')
            channel = int(raw)
            info = inspect_channel(self.radio.currentText(), channel)
        except (ValueError, TypeError) as exc:
            self.result.setPlainText(str(exc) if str(exc) else 'Enter a whole channel number.')
            return
        prefix = 'n' if info['radio'] == 'NR' else 'B'
        bands = ', '.join(prefix + str(band) for band in info['bands']) or 'No candidate in bundled table'
        frequency = (f"{info['center_mhz']:.6f}".rstrip('0').rstrip('.') + ' MHz'
                     if info['center_mhz'] is not None else 'Not computed for LTE without a band-specific offset')
        self.result.setPlainText(
            f"{info['radio']} channel {channel}\nGlobal raster frequency: {frequency}\n"
            f"Candidate bands: {bands}\nEvidence class: {info['kind']}\n"
            f"Reference version: {info['reference_version']}\nSource: {info['reference_source']}\n\n"
            f"Interpretation / limitations: {info['limitations']}")

    def reverse_lookup(self):
        self.clear_reverse()
        try:
            number = nr_mhz_to_arfcn(self.frequency.text().strip())
        except ValueError as exc:
            self.reverse_result.setText(str(exc))
            return
        self.radio.setCurrentText('NR')
        self.channel.setText(str(number))
        self.inspect()
        self.reverse_result.setText(f'NR-ARFCN {number} on the global raster. Band-specific validity is not assessed.')
