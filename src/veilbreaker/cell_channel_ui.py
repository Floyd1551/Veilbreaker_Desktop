"""Cellular channel inspector in the offline Tools workspace."""
from PySide6.QtWidgets import (QComboBox, QFormLayout, QLabel, QLineEdit,
                               QPushButton, QTextBrowser, QVBoxLayout, QWidget)

from .cell_channel_tools import LTE_DL_LOW_MHZ, inspect_channel, lte_mhz_to_earfcn, nr_mhz_to_arfcn


class CellChannelPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        heading = QLabel('Cellular channel inspector')
        heading.setObjectName('section')
        layout.addWidget(heading)
        caption = QLabel('Look up possible LTE/NR bands from a channel number. Selected LTE downlink bands use band-specific offsets; NR uses the global frequency raster. Results are reference context, not measured cells or carrier attribution.')
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
        self.reverse_mode = QComboBox()
        self.reverse_mode.addItems(('NR global raster', 'LTE downlink'))
        self.reverse_mode.setAccessibleName('Frequency to channel conversion mode')
        reverse.addRow('Frequency lookup', self.reverse_mode)
        self.reverse_band = QComboBox()
        for band in sorted(LTE_DL_LOW_MHZ):
            self.reverse_band.addItem('B' + str(band), band)
        self.reverse_band.setAccessibleName('LTE downlink band')
        reverse.addRow('LTE band', self.reverse_band)
        self.frequency = QLineEdit()
        self.frequency.setPlaceholderText('Example: 3500')
        self.frequency.setAccessibleName('Center frequency in MHz')
        reverse.addRow('Center frequency (MHz)', self.frequency)
        layout.addLayout(reverse)
        self.reverse_form = reverse
        reverse_button = QPushButton('Find channel number')
        reverse_button.clicked.connect(self.reverse_lookup)
        self.frequency.returnPressed.connect(self.reverse_lookup)
        layout.addWidget(reverse_button)
        self.reverse_result = QLabel()
        self.reverse_result.setWordWrap(True)
        layout.addWidget(self.reverse_result)
        source = QLabel('Offline references: bundled AOSP channel-band candidate table (version shown in result); AOSP / 3GPP TS 36.101 LTE downlink offsets; 3GPP TS 38.104 NR global frequency raster. Band candidates can overlap and may differ from what a modem reports.')
        source.setWordWrap(True)
        layout.addWidget(source)
        self.radio.currentTextChanged.connect(self.clear)
        self.channel.textChanged.connect(self.clear)
        self.frequency.textChanged.connect(self.clear_reverse)
        self.reverse_mode.currentTextChanged.connect(self._reverse_mode_changed)
        self.reverse_band.currentIndexChanged.connect(self.clear_reverse)
        self._reverse_mode_changed()

    def _reverse_mode_changed(self, *_):
        self.reverse_form.setRowVisible(self.reverse_band, self.reverse_mode.currentText() == 'LTE downlink')
        self.clear_reverse()

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
                     if info['center_mhz'] is not None else 'Not computed for this LTE band/channel')
        frequency_label = 'NR global raster frequency' if info['radio'] == 'NR' else 'LTE downlink center frequency'
        self.result.setPlainText(
            f"{info['radio']} channel {channel}\n{frequency_label}: {frequency}\n"
            f"Candidate bands: {bands}\nEvidence class: {info['kind']}\n"
            f"Reference version: {info['reference_version']}\nChannel source: {info['reference_source']}\n"
            f"Frequency source: {info['frequency_reference_source'] or 'NR global raster / not applicable'}\n"
            f"LTE offset review: {info['frequency_reference_reviewed'] or 'Not applicable'}\n\n"
            f"Interpretation / limitations: {info['limitations']}")

    def reverse_lookup(self):
        self.clear_reverse()
        try:
            if self.reverse_mode.currentText() == 'LTE downlink':
                number = lte_mhz_to_earfcn(self.reverse_band.currentData(), self.frequency.text().strip())
                radio = 'LTE'
            else:
                number = nr_mhz_to_arfcn(self.frequency.text().strip())
                radio = 'NR'
        except ValueError as exc:
            self.reverse_result.setText(str(exc))
            return
        self.radio.setCurrentText(radio)
        self.channel.setText(str(number))
        self.inspect()
        self.reverse_result.setText(
            f'LTE B{self.reverse_band.currentData()} downlink EARFCN {number}. Band and channel grid checked; deployment is not assessed.'
            if radio == 'LTE' else
            f'NR-ARFCN {number} on the global raster. Band-specific validity is not assessed.')
