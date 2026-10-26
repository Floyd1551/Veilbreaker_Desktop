"""Offline toolbox workspace: calculations, address planning and field references."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel, QLineEdit,
                              QPushButton, QTextBrowser, QComboBox, QApplication)
from .rf_tools_ui import RFToolsDialog
from .network_tools import inspect_subnet
from .toolbox_reference import REFERENCES


class ToolboxPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        heading = QLabel('Tools')
        heading.setObjectName('title')
        layout.addWidget(heading)
        caption = QLabel('Offline calculations and field references. Equipment controls are under Configuration.')
        caption.setWordWrap(True)
        layout.addWidget(caption)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        self.calculators = RFToolsDialog(self, embedded=True)
        self.calculators.setMinimumHeight(900)
        tabs.addTab(self.calculators, 'RF calculators')
        network = QWidget()
        form = QVBoxLayout(network)
        title = QLabel('IPv4 / IPv6 subnet inspector')
        title.setObjectName('section')
        form.addWidget(title)
        help_text = QLabel('Enter an address with its prefix. This performs address arithmetic only; it does not scan the network.')
        help_text.setWordWrap(True)
        form.addWidget(help_text)
        self.address = QLineEdit('192.168.1.20/24')
        self.address.setAccessibleName('IP address and prefix')
        form.addWidget(self.address)
        inspect = QPushButton('Inspect subnet')
        inspect.clicked.connect(self.inspect)
        self.address.returnPressed.connect(self.inspect)
        form.addWidget(inspect)
        self.subnet_output = QTextBrowser()
        form.addWidget(self.subnet_output)
        self.copy_subnet = QPushButton('Copy subnet details')
        self.copy_subnet.setEnabled(False)
        self.copy_subnet.clicked.connect(lambda: QApplication.clipboard().setText(self.subnet_output.toPlainText()))
        form.addWidget(self.copy_subnet)
        self.address.textChanged.connect(self.clear_subnet)
        tabs.addTab(network, 'Networking')
        reference = QWidget()
        ref_layout = QVBoxLayout(reference)
        self.reference_search = QLineEdit()
        self.reference_search.setPlaceholderText('Search RF, wireless or networking references…')
        self.reference_search.setAccessibleName('Find field reference')
        ref_layout.addWidget(self.reference_search)
        self.reference_list = QComboBox()
        self.reference_list.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.reference_list.setMinimumContentsLength(20)
        self.reference_list.setAccessibleName('Field reference article')
        ref_layout.addWidget(self.reference_list)
        self.reference_body = QTextBrowser()
        self.reference_body.setOpenExternalLinks(True)
        ref_layout.addWidget(self.reference_body)
        footer = QLabel('Original field notes · reviewed October 25, 2026 · source links require internet')
        footer.setWordWrap(True)
        ref_layout.addWidget(footer)
        self.reference_list.currentIndexChanged.connect(self.show_reference)
        self.reference_search.textChanged.connect(self.filter_references)
        tabs.addTab(reference, 'References & charts')
        self.filter_references('')

    def clear_subnet(self):
        self.subnet_output.clear()
        self.copy_subnet.setEnabled(False)

    def inspect(self):
        self.clear_subnet()
        try:
            result = inspect_subnet(self.address.text())
        except ValueError as exc:
            self.subnet_output.setPlainText(str(exc))
            return
        self.subnet_output.setPlainText('\n\n'.join(f'{key}: {value}' for key, value in result.items()))
        self.copy_subnet.setEnabled(True)

    def filter_references(self, query):
        self.reference_list.blockSignals(True)
        self.reference_list.clear()
        for title, body in REFERENCES:
            if query.strip().casefold() in (title + body).casefold():
                self.reference_list.addItem(title, body)
        self.reference_list.blockSignals(False)
        self.show_reference()

    def show_reference(self):
        self.reference_body.setHtml(self.reference_list.currentData() or '')
