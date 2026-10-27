"""Reusable discovery cards for the offline engineering workbench."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout

from .ui_icons import ui_icon


class ToolCard(QFrame):
    activated = Signal(str)

    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.setObjectName('card')
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedWidth(280)
        self.setAccessibleName(record.title)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self.category_icon = QLabel()
        icon_name = {'RF': 'sdr', 'Cellular': 'cellular', 'Wi-Fi': 'network',
                     'Networking': 'network', 'Fiber & Power': 'tools',
                     'References': 'evidence'}.get(record.category, 'tools')
        self.category_icon.setPixmap(ui_icon(icon_name).pixmap(24, 24))
        self.category_icon.setAccessibleName(record.category + ' category')
        header.addWidget(self.category_icon)
        meta = QLabel(f'{record.category.upper()} · {record.kind.upper()}')
        meta.setObjectName('eyebrow')
        header.addWidget(meta, 1)
        layout.addLayout(header)
        title = QLabel(record.title)
        title.setObjectName('section')
        title.setWordWrap(True)
        layout.addWidget(title)
        purpose = QLabel(record.description)
        purpose.setWordWrap(True)
        purpose.setMaximumHeight(66)
        layout.addWidget(purpose)
        tabbed = record.kind in ('calculator', 'reference')
        self.open_button = QPushButton('Open tab' if tabbed else 'Open')
        self.open_button.setIcon(ui_icon('tools' if tabbed else icon_name))
        self.open_button.setAccessibleName('Open ' + record.title + (' in tab' if tabbed else ''))
        self.open_button.clicked.connect(lambda: self.activated.emit(record.record_id))
        layout.addWidget(self.open_button)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit(self.record.record_id)
            event.accept()
            return
        super().keyPressEvent(event)
