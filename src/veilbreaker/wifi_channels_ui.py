"""Wi-Fi channel comparison panel with a clearly schematic frequency diagram."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .wifi_channels import BANDS, channels, inspect_pair


class ChannelDiagram(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.setMinimumHeight(190)
        self.setAccessibleName('Schematic comparison of two nominal 20 MHz Wi-Fi channels')

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#101b2a'))
        if not self.data:
            return
        first, second = self.data['first'], self.data['second']
        left = min(first['lower_mhz'], second['lower_mhz']) - 5
        right = max(first['upper_mhz'], second['upper_mhz']) + 5
        width = max(1, self.width() - 96)
        x = lambda mhz: 48 + width * (mhz - left) / (right - left)
        painter.setPen(QPen(QColor('#8ea9bb')))
        painter.drawLine(48, 145, self.width() - 48, 145)
        for row, item, color in ((0, first, '#35c9d0'), (1, second, '#af83ed')):
            y = 33 + row * 55
            painter.fillRect(int(x(item['lower_mhz'])), y,
                             max(1, int(x(item['upper_mhz']) - x(item['lower_mhz']))), 28, QColor(color))
            painter.setPen(QColor('#edf5fa'))
            painter.drawText(48, y - 5, f"Channel {item['channel']} · {item['center_mhz']} MHz")
            painter.drawText(int(x(item['center_mhz'])) - 20, 166, str(item['center_mhz']))
        painter.setPen(QColor('#8ea9bb'))
        painter.drawText(48, self.height() - 5, 'Schematic 20 MHz footprints · not a measured spectrum')


class WifiChannelsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        heading = QLabel('Wi-Fi channel inspector')
        heading.setObjectName('section')
        layout.addWidget(heading)
        description = QLabel('Compare two nominal 20 MHz channel footprints across 2.4, 5 or 6 GHz. This is offline channel arithmetic, not a scan or an authorization to operate.')
        description.setWordWrap(True)
        layout.addWidget(description)
        controls = QHBoxLayout()
        self.band = QComboBox()
        self.band.addItems(BANDS)
        self.band.setAccessibleName('Wi-Fi band')
        self.first = QComboBox()
        self.first.setAccessibleName('First Wi-Fi channel')
        self.second = QComboBox()
        self.second.setAccessibleName('Second Wi-Fi channel')
        for widget in (self.band, self.first, self.second):
            controls.addWidget(widget)
        layout.addLayout(controls)
        self.diagram = ChannelDiagram(self)
        layout.addWidget(self.diagram)
        self.result = QLabel()
        self.result.setWordWrap(True)
        layout.addWidget(self.result)
        source = QLabel(
            'Planning reference · reviewed October 26, 2026: '
            '<a href="https://wireless.docs.kernel.org/en/latest/en/developers/documentation/channellist.html">'
            'Linux Wireless channel list</a>, '
            '<a href="https://wireless.docs.kernel.org/en/latest/en/users/documentation/bluetooth-coexistence.html">'
            '2.4 GHz channel footprints</a>, '
            '<a href="https://docs.fcc.gov/public/attachments/FCC-24-125A1_Rcd.pdf">'
            'FCC 6 GHz band order</a>. Review current local rules, device capabilities and DFS/AFC '
            'requirements before deployment. Links require internet; calculations work offline.')
        source.setWordWrap(True)
        source.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        source.setOpenExternalLinks(True)
        layout.addWidget(source)
        layout.addStretch()
        self.band.currentTextChanged.connect(self._load_channels)
        self.first.currentIndexChanged.connect(self.refresh)
        self.second.currentIndexChanged.connect(self.refresh)
        self._load_channels()

    def _load_channels(self, *_):
        options = channels(self.band.currentText())
        for combo in (self.first, self.second):
            combo.blockSignals(True)
            combo.clear()
            for channel in options:
                combo.addItem(str(channel), channel)
            combo.blockSignals(False)
        self.second.setCurrentIndex(min(1, len(options) - 1))
        self.refresh()

    def refresh(self, *_):
        if self.first.currentData() is None or self.second.currentData() is None:
            return
        data = inspect_pair(self.band.currentText(), self.first.currentData(), self.second.currentData())
        self.diagram.set_data(data)
        self.result.setText(
            f"Channel {data['first']['channel']}: {data['first']['center_mhz']} MHz; "
            f"channel {data['second']['channel']}: {data['second']['center_mhz']} MHz. "
            f"Center separation {data['center_separation_mhz']} MHz; "
            f"nominal overlap {data['nominal_overlap_mhz']} MHz. {data['limitations']}")
