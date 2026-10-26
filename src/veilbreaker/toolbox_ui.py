"""Offline toolbox workspace: calculations, address planning and field references."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QLineEdit,
                              QPushButton, QTextBrowser, QComboBox, QApplication, QScrollArea)
from .rf_tools_ui import RFToolsDialog
from .network_tools import inspect_subnet
from .toolbox_reference import REFERENCES
from .tool_registry import CATEGORIES, build_registry, search_registry
from .tool_cards import ToolCard
from .wifi_channels_ui import WifiChannelsPanel
from .widgets import FlowLayout


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
        self.records = build_registry()
        filters = QHBoxLayout()
        self.global_search = QLineEdit()
        self.global_search.setPlaceholderText('Search tools and references: RSRP, Fresnel, dBm, subnet…')
        self.global_search.setAccessibleName('Search all tools and references')
        filters.addWidget(self.global_search, 1)
        self.category_filter = QComboBox()
        self.category_filter.addItems(('All', *CATEGORIES))
        self.category_filter.setAccessibleName('Tool category')
        filters.addWidget(self.category_filter)
        layout.addLayout(filters)
        self.result_count = QLabel()
        layout.addWidget(self.result_count)
        self.discovery = QScrollArea()
        self.discovery.setWidgetResizable(True)
        self.discovery.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.discovery.setMinimumHeight(170)
        self.discovery.setMaximumHeight(260)
        self.discovery_widget = QWidget()
        self.discovery_layout = FlowLayout(self.discovery_widget)
        self.discovery.setWidget(self.discovery_widget)
        layout.addWidget(self.discovery)
        self.empty_state = QLabel('No matching tools or references. Try a broader term or choose All categories.')
        self.empty_state.setWordWrap(True)
        layout.addWidget(self.empty_state)
        self.result_cards = []
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.calculators = RFToolsDialog(self, embedded=True)
        self.calculators.setMinimumHeight(900)
        self.tabs.addTab(self.calculators, 'Calculators')
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
        self.tabs.addTab(network, 'Networking')
        self.wifi_planner = WifiChannelsPanel(self)
        self.tabs.addTab(self.wifi_planner, 'Wi-Fi channels')
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
        self.tabs.addTab(reference, 'References & charts')
        self.filter_references('')
        self.global_search.textChanged.connect(self.refresh_discovery)
        self.category_filter.currentTextChanged.connect(self.refresh_discovery)
        self.refresh_discovery()

    def refresh_discovery(self, *_):
        while self.discovery_layout.count():
            item = self.discovery_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        matches = search_registry(self.records, self.global_search.text(), self.category_filter.currentText())
        self.result_cards = []
        for record in matches:
            card = ToolCard(record, self.discovery_widget)
            card.activated.connect(self.activate_record)
            self.discovery_layout.addWidget(card)
            self.result_cards.append(card)
        self.result_count.setText(f'{len(matches)} result' + ('' if len(matches) == 1 else 's'))
        self.empty_state.setVisible(not matches)
        self.discovery_widget.updateGeometry()

    def activate_record(self, record_id):
        record = next((record for record in self.records if record.record_id == record_id), None)
        if record is None:
            return
        if record.kind == 'calculator':
            self.tabs.setCurrentIndex(0)
            self.calculators.search.clear()
            index = self.calculators.selector.findData(record.target_id)
            if index >= 0:
                self.calculators.selector.setCurrentIndex(index)
        elif record.kind == 'inspector':
            self.tabs.setCurrentIndex(1)
            self.address.setFocus()
        elif record.kind == 'planner':
            self.tabs.setCurrentWidget(self.wifi_planner)
        elif record.kind == 'reference':
            self.tabs.setCurrentIndex(3)
            self.reference_search.clear()
            index = self.reference_list.findText(record.target_id)
            if index >= 0:
                self.reference_list.setCurrentIndex(index)

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
