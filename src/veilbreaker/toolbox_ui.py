"""Offline toolbox workspace: calculations, address planning and field references."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QLineEdit,
                              QPushButton, QTextBrowser, QComboBox, QApplication, QScrollArea, QTabBar)
from .rf_tools_ui import RFToolsDialog
from .network_tools import inspect_subnet
from .toolbox_reference import REFERENCES
from .tool_registry import CATEGORIES, build_registry, search_registry
from .tool_cards import ToolCard
from .wifi_channels_ui import WifiChannelsPanel
from .cell_channel_ui import CellChannelPanel
from .cell_signal_ui import CellSignalPanel
from .tool_workspace_ui import ReferenceArticle
from .paths import data_root
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
        config = getattr(parent, 'config', None)
        self.preset_path = (config.root if config is not None else data_root()) / 'tool-presets.json'
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
        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.setAccessibleName('Open Tools workspace tabs')
        self.workspace_tabs.setTabsClosable(True)
        self.workspace_tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.workspace_tabs.setUsesScrollButtons(True)
        layout.addWidget(self.workspace_tabs)
        self.tabs = QTabWidget(self.workspace_tabs)
        self.opened_tabs = {}
        self.calculators = RFToolsDialog(self, embedded=True, preset_path=self.preset_path)
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
        self.cell_channel = CellChannelPanel(self)
        self.tabs.addTab(self.cell_channel, 'Cellular channels')
        self.signal_guide = CellSignalPanel(self)
        self.tabs.addTab(self.signal_guide, 'Signal guide')
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
        footer = QLabel('Offline field notes · review each entry’s source and version before operational use · links require internet')
        footer.setWordWrap(True)
        ref_layout.addWidget(footer)
        self.reference_list.currentIndexChanged.connect(self.show_reference)
        self.reference_search.textChanged.connect(self.filter_references)
        self.tabs.addTab(reference, 'References & charts')
        self.workspace_tabs.addTab(self.tabs, 'Browse tools')
        self.workspace_tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.LeftSide, None)
        self.workspace_tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.workspace_tabs.tabCloseRequested.connect(self.close_workspace_tab)
        self.workspace_tabs.currentChanged.connect(self._workspace_tab_changed)
        self.filter_references('')
        self.global_search.textChanged.connect(self.refresh_discovery)
        self.global_search.textChanged.connect(self._show_browse_for_search)
        self.category_filter.currentTextChanged.connect(self.refresh_discovery)
        self.refresh_discovery()

    def _workspace_tab_changed(self, index):
        browsing = index == 0
        self.result_count.setVisible(browsing)
        self.discovery.setVisible(browsing)
        self.empty_state.setVisible(browsing and not self.result_cards)

    def _show_browse_for_search(self, *_):
        if self.workspace_tabs.currentIndex() != 0:
            self.workspace_tabs.setCurrentIndex(0)

    def refresh_discovery(self, *_):
        while self.discovery_layout.count():
            item = self.discovery_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        matches = search_registry(self.records, self.global_search.text(), self.category_filter.currentText())
        self.result_cards = []
        for record in matches:
            card = ToolCard(record, self.discovery_widget)
            card.activated.connect(self.open_record_tab)
            self.discovery_layout.addWidget(card)
            self.result_cards.append(card)
        self.result_count.setText(f'{len(matches)} result' + ('' if len(matches) == 1 else 's'))
        self.empty_state.setVisible(not matches and self.workspace_tabs.currentIndex() == 0)
        self.discovery_widget.updateGeometry()

    def open_record_tab(self, record_id):
        record = next((item for item in self.records if item.record_id == record_id), None)
        if record is None:
            return
        if record.kind not in ('calculator', 'reference'):
            self.activate_record(record_id)
            return
        existing = self.opened_tabs.get(record_id)
        if existing is not None:
            self.workspace_tabs.setCurrentWidget(existing)
            return
        if record.kind == 'calculator':
            widget = RFToolsDialog(self.workspace_tabs, embedded=True, preset_path=self.preset_path)
            widget.search.setText(record.title)
            if widget.selector.currentData() != record.target_id:
                widget.deleteLater()
                return
            widget.search.hide()
            widget.selector.hide()
        else:
            markup = next((body for title, body in REFERENCES if title == record.target_id), None)
            if markup is None:
                return
            widget = ReferenceArticle(record.title, markup, self.workspace_tabs)
        index = self.workspace_tabs.addTab(widget, record.title)
        self.workspace_tabs.setTabToolTip(index, record.title)
        self.opened_tabs[record_id] = widget
        self.workspace_tabs.setCurrentIndex(index)

    def close_workspace_tab(self, index):
        if index <= 0 or index >= self.workspace_tabs.count():
            return
        widget = self.workspace_tabs.widget(index)
        self.opened_tabs = {key: value for key, value in self.opened_tabs.items() if value is not widget}
        self.workspace_tabs.removeTab(index)
        widget.deleteLater()

    def activate_record(self, record_id):
        record = next((record for record in self.records if record.record_id == record_id), None)
        if record is None:
            return
        self.workspace_tabs.setCurrentIndex(0)
        if record.kind == 'calculator':
            self.tabs.setCurrentIndex(0)
            self.calculators.search.clear()
            index = self.calculators.selector.findData(record.target_id)
            if index >= 0:
                self.calculators.selector.setCurrentIndex(index)
        elif record.kind == 'inspector':
            if record.target_id == 'cell_channel':
                self.tabs.setCurrentWidget(self.cell_channel)
                self.cell_channel.channel.setFocus()
            elif record.target_id == 'signal_guide':
                self.tabs.setCurrentWidget(self.signal_guide)
                self.signal_guide.inputs['rsrp'].setFocus()
            else:
                self.tabs.setCurrentIndex(1)
                self.address.setFocus()
        elif record.kind == 'planner':
            self.tabs.setCurrentWidget(self.wifi_planner)
        elif record.kind == 'reference':
            self.tabs.setCurrentIndex(5)
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
