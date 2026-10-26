"""Independent article view for a closable Tools workspace tab."""
from PySide6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout, QWidget


class ReferenceArticle(QWidget):
    def __init__(self, title, markup, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName('section')
        heading.setWordWrap(True)
        layout.addWidget(heading)
        self.body = QTextBrowser()
        self.body.setAccessibleName(title + ' reference article')
        self.body.setOpenExternalLinks(True)
        self.body.setHtml(markup)
        layout.addWidget(self.body, 1)
