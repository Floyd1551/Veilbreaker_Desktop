"""Reusable discovery cards for the offline engineering workbench."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout


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
        meta = QLabel(f'{record.category.upper()} · {record.kind.upper()}')
        meta.setObjectName('eyebrow')
        layout.addWidget(meta)
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
        self.open_button.setAccessibleName('Open ' + record.title + (' in tab' if tabbed else ''))
        self.open_button.clicked.connect(lambda: self.activated.emit(record.record_id))
        layout.addWidget(self.open_button)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit(self.record.record_id)
            event.accept()
            return
        super().keyPressEvent(event)
