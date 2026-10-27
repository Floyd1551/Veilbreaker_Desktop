"""In-app management of regional terrain and structure reference packs."""
from functools import partial

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPushButton,
                               QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from .background_dialog import JobDialog
from .regional_pack_download import download_and_install
from .regional_packs import RegionalPackStore
from .usgs_terrain_catalog import search_terrain_products


def _install_job(root, kind, path, metadata, cancelled, progress):
    return {'installed': RegionalPackStore(root).install_local(kind, path, metadata, cancelled, progress)}


def _download_job(root, kind, url, metadata, checksum, cancelled, progress):
    return {'installed': download_and_install(RegionalPackStore(root), kind, url, metadata, cancelled,
                                              progress, expected_sha256=checksum or None)}


def _verify_job(root, pack_id, cancelled, progress):
    return {'verified': RegionalPackStore(root).verify(pack_id, cancelled), 'pack_id': pack_id}


def _search_usgs_job(bounds, cancelled, progress):
    return {'catalog': search_terrain_products(bounds, cancelled, progress)}


class RegionalPacksDialog(JobDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.store = RegionalPackStore(config.root / 'regional-packs')
        self.rows = []
        self.setWindowTitle('Regional terrain and structure packs')
        self.resize(980, 760)
        layout = QVBoxLayout(self)
        introduction = QLabel('Prepare local data before field work. Terrain is bare earth; structure records are references, not serving-cell or carrier identification.')
        introduction.setWordWrap(True)
        layout.addWidget(introduction)
        self.workspace_tabs = QTabWidget()
        installed_page = QWidget()
        installed_layout = QVBoxLayout(installed_page)
        prepare_page = QWidget()
        prepare_layout = QVBoxLayout(prepare_page)
        self.workspace_tabs.addTab(installed_page, 'Installed packs')
        self.workspace_tabs.addTab(prepare_page, 'Add / download')
        layout.addWidget(self.workspace_tabs, 1)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Kind', 'Pack', 'WGS84 bounds', 'Source / date', 'Size', 'Status'])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.select_pack)
        installed_layout.addWidget(self.table, 2)
        self.details = QLabel('Select a pack for its full provenance and checksum.')
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        self.details.setWordWrap(True)
        installed_layout.addWidget(self.details)
        existing = QHBoxLayout()
        self.verify_button = QPushButton('Verify SHA-256')
        self.verify_button.clicked.connect(self.verify_selected)
        self.remove_button = QPushButton('Remove pack…')
        self.remove_button.clicked.connect(self.remove_selected)
        self.records_button = QPushButton('View records')
        self.records_button.clicked.connect(self.show_structure_records)
        for button in (self.verify_button, self.remove_button, self.records_button):
            existing.addWidget(button)
        installed_layout.addLayout(existing)
        self.structures_table = QTableWidget(0, 4)
        self.structures_table.setHorizontalHeaderLabels(['Structure ID', 'Longitude', 'Latitude', 'Owner / height'])
        self.structures_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.structures_table.setMaximumHeight(180)
        self.structures_table.hide()
        installed_layout.addWidget(self.structures_table)
        form = QFormLayout()
        self.kind = QComboBox()
        self.kind.addItem('Terrain · GeoTIFF', 'terrain')
        self.kind.addItem('Physical structures · GeoJSON', 'structures')
        self.name = QLineEdit()
        self.source = QLineEdit()
        self.license = QLineEdit()
        self.date = QLineEdit()
        self.datum = QLineEdit()
        self.units = QComboBox()
        self.units.addItems(['Select elevation units', 'm', 'ft', 'us-ft'])
        self.bounds = QLineEdit()
        self.bounds.setPlaceholderText('west, south, east, north · WGS84 degrees')
        self.huntsville_button = QPushButton('Huntsville, AL area')
        self.huntsville_button.clicked.connect(self.use_huntsville_area)
        self.url = QLineEdit()
        self.url.setPlaceholderText('https://provider.example/region.tif (URL query is not saved)')
        self.checksum = QLineEdit()
        self.checksum.setPlaceholderText('Optional published SHA-256')
        for label, widget in [('Data class', self.kind), ('Pack name', self.name), ('Source / provider', self.source),
                              ('License / terms', self.license), ('Source data date', self.date),
                              ('Terrain vertical datum', self.datum), ('Terrain elevation units', self.units),
                              ('Area bounds / structure extent', self.bounds), ('HTTPS download URL', self.url),
                              ('Expected checksum', self.checksum)]:
            form.addRow(label, widget)
        prepare_layout.addLayout(form)
        prepare_layout.addWidget(self.huntsville_button)
        catalog_row = QHBoxLayout()
        self.search_button = QPushButton('Find USGS terrain for area')
        self.search_button.clicked.connect(self.search_usgs)
        self.products = QComboBox()
        self.products.setAccessibleName('USGS terrain products for area')
        self.products.setMinimumContentsLength(25)
        self.products.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.use_product_button = QPushButton('Use selected product')
        self.use_product_button.clicked.connect(self.use_product)
        prepare_layout.addWidget(self.search_button)
        catalog_row.addWidget(self.products, 1)
        catalog_row.addWidget(self.use_product_button)
        prepare_layout.addLayout(catalog_row)
        hint = QLabel('Structure bounds are declared by the dataset provider and do not prove completeness. Terrain bounds are read from the raster; no-data gaps may remain. Downloads contact only the URL you choose.')
        hint.setWordWrap(True)
        prepare_layout.addWidget(hint)
        actions = QHBoxLayout()
        self.import_button = QPushButton('Import local file…')
        self.import_button.clicked.connect(self.import_local)
        self.download_button = QPushButton('Download and install URL')
        self.download_button.clicked.connect(self.download)
        self.close_button = QPushButton('Close')
        self.close_button.clicked.connect(self.reject)
        for button in (self.import_button, self.download_button, self.close_button):
            actions.addWidget(button)
        prepare_layout.addLayout(actions)
        prepare_layout.addStretch(1)
        self.status = QLabel('No regional data pack selected. Existing maps and diagnostics remain available.')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.controls = [self.table, self.verify_button, self.remove_button, self.records_button,
                         self.kind, self.name, self.source, self.license, self.date, self.datum,
                         self.units, self.bounds, self.url, self.checksum, self.import_button,
                         self.download_button, self.search_button, self.products, self.use_product_button]
        self.controls.append(self.huntsville_button)
        self.kind.currentIndexChanged.connect(self.update_kind)
        self.refresh()
        self.update_kind()

    def update_kind(self):
        terrain = self.kind.currentData() == 'terrain'
        self.datum.setEnabled(terrain)
        self.units.setEnabled(terrain)
        self.search_button.setEnabled(terrain)
        self.products.setEnabled(terrain)
        self.use_product_button.setEnabled(terrain and self.products.count() > 0)

    def metadata(self):
        value = dict(name=self.name.text().strip(), source=self.source.text().strip(),
                     license=self.license.text().strip(), source_date=self.date.text().strip())
        if self.kind.currentData() == 'terrain':
            value.update(vertical_datum=self.datum.text().strip(), units=self.units.currentText())
        else:
            try:
                value['bounds_wgs84'] = self._entered_bounds()
            except ValueError as exc:
                raise ValueError('Enter structure bounds as west, south, east, north.') from exc
        return value

    def _entered_bounds(self):
        return [float(piece.strip()) for piece in self.bounds.text().split(',')]

    @Slot()
    def use_huntsville_area(self):
        self.bounds.setText('-87.2, 34.3, -86.2, 35.2')
        self.status.setText('Huntsville, AL and surrounding area selected as a search area. Installed product coverage must be checked separately.')

    @Slot()
    def search_usgs(self):
        if self.kind.currentData() != 'terrain':
            return
        try:
            bounds = self._entered_bounds()
        except ValueError:
            self.status.setText('Enter search bounds as west, south, east, north in WGS84 degrees.')
            return
        self.start_job(partial(_search_usgs_job, bounds))

    @Slot()
    def use_product(self):
        item = self.products.currentData()
        if not isinstance(item, dict):
            return
        self.kind.setCurrentIndex(self.kind.findData('terrain'))
        self.name.setText(item['title'])
        self.source.setText(item['source'])
        self.license.setText(item['license'])
        self.date.setText(item['source_date'])
        self.url.setText(item['url'])
        self.checksum.clear()
        self.datum.clear()
        self.units.setCurrentIndex(0)
        self.status.setText('USGS product selected. Confirm its vertical datum and elevation units from the product metadata before downloading. Product date is not the download date.')

    def refresh(self, selected_id=None):
        self.rows = self.store.list_packs()
        self.table.setRowCount(len(self.rows))
        for i, row in enumerate(self.rows):
            bounds = row.get('bounds_wgs84')
            values = [row.get('kind', 'Unknown'), row.get('name', 'Unnamed'),
                      ', '.join(f'{v:.4f}' for v in bounds) if bounds else 'Unknown',
                      f"{row.get('source', 'Unknown')} · {row.get('source_date', 'Unknown')}",
                      f"{row.get('bytes', 0) / 1024 / 1024:.1f} MiB", row['status']]
            for column, value in enumerate(values):
                self.table.setItem(i, column, QTableWidgetItem(value))
            if selected_id and row['pack_id'] == selected_id:
                self.table.selectRow(i)
        if not selected_id and self.rows:
            self.table.selectRow(0)
        self.select_pack()

    def selected(self):
        index = self.table.currentRow()
        return self.rows[index] if 0 <= index < len(self.rows) else None

    def select_pack(self):
        row = self.selected()
        self.structures_table.hide()
        if not row:
            self.details.setText('Select a pack for its full provenance and checksum.')
            self.verify_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.records_button.setEnabled(False)
            return
        if row.get('kind') == 'unknown':
            self.details.setText('Manifest unavailable. This folder is not usable as a regional pack.')
        else:
            self.details.setText('\n'.join((
                f"{row['name']} · {row['kind']} · {row['status']}",
                f"Source: {row['source']} · source date: {row['source_date']} · terms: {row['license']}",
                f"WGS84 bounds: {row['bounds_wgs84']} · {row['coverage_note']}",
                f"SHA-256: {row['sha256']} · installed: {row['imported_utc']}",
                f"Download origin: {row.get('download_origin', 'Local import')} · {row.get('download_integrity', 'computed SHA-256')}",
                'No serving-cell or carrier identity is inferred from a physical structure.'
                if row['kind'] == 'structures' else
                f"CRS: {row['crs']} · vertical datum: {row['vertical_datum']} · units: {row['units']}")))
        self.verify_button.setEnabled(row.get('kind') in ('terrain', 'structures'))
        self.remove_button.setEnabled(row.get('kind') in ('terrain', 'structures'))
        self.records_button.setEnabled(row.get('kind') == 'structures' and row['status'] == 'available')

    @Slot()
    def import_local(self):
        kind = self.kind.currentData()
        try:
            metadata = self.metadata()
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        chosen, _ = QFileDialog.getOpenFileName(self, 'Import regional data pack', '',
                                               'GeoTIFF (*.tif *.tiff)' if kind == 'terrain' else 'GeoJSON (*.geojson *.json)')
        if chosen:
            self.start_job(partial(_install_job, self.store.root, kind, chosen, metadata))

    @Slot()
    def download(self):
        try:
            metadata = self.metadata()
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        if not self.url.text().strip():
            self.status.setText('Enter an explicit HTTPS pack URL.')
            return
        self.start_job(partial(_download_job, self.store.root, self.kind.currentData(),
                               self.url.text().strip(), metadata, self.checksum.text().strip()))

    @Slot()
    def verify_selected(self):
        if row := self.selected():
            self.start_job(partial(_verify_job, self.store.root, row['pack_id']))

    @Slot()
    def remove_selected(self):
        row = self.selected()
        if not row:
            return
        if QMessageBox.question(self, 'Remove regional pack',
                                f"Delete installed {row['name']} pack data? Existing survey evidence is unchanged.") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.store.remove(row['pack_id'])
            self.refresh()
            self.status.setText('Installed pack removed. Existing reports and original source files are unchanged.')
        except (OSError, ValueError) as exc:
            self.status.setText(str(exc))

    @Slot()
    def show_structure_records(self):
        row = self.selected()
        if not row or row.get('kind') != 'structures':
            return
        try:
            records = self.store.query_structures(row['pack_id'], row['bounds_wgs84'], limit=200)
        except (OSError, ValueError) as exc:
            self.status.setText(str(exc))
            return
        self.structures_table.setRowCount(len(records))
        for i, record in enumerate(records):
            fields = [record['structure_id'], f"{record['lon']:.6f}", f"{record['lat']:.6f}",
                      f"{record.get('owner') or 'Owner unknown'} · {record.get('height_agl_m', 'height unknown')} m AGL"]
            for j, value in enumerate(fields):
                self.structures_table.setItem(i, j, QTableWidgetItem(value))
        self.structures_table.show()
        self.status.setText(f'Showing {len(records)} structure references (up to 200). No serving-cell association is implied.')

    @Slot(object)
    def job_ready(self, result):
        if self.closing:
            return
        if row := result.get('installed'):
            self.refresh(row['pack_id'])
            self.status.setText(f"Installed {row['name']} · {row['bytes'] / 1024 / 1024:.1f} MiB · SHA-256 {row['sha256']}.")
        elif catalog := result.get('catalog'):
            self.products.clear()
            for item in catalog['products']:
                text = f"{item['title']} · {item['bytes'] / 1024 / 1024:.0f} MiB · {item['source_date']}"
                self.products.addItem(text, item)
                self.products.setItemData(self.products.count() - 1,
                                          f"Reported bounds: {item['reported_bounds_wgs84']}", Qt.ItemDataRole.ToolTipRole)
            self.update_kind()
            self.status.setText(f"USGS returned {catalog['total']} products; showing {len(catalog['products'])} supported GeoTIFF downloads. Choose a product, then confirm datum and units. Historical products may appear.")
        elif 'verified' in result:
            self.status.setText('Pack SHA-256 matches its recorded bytes.' if result['verified'] else
                                'Pack SHA-256 does not match; do not use it for assessment.')

    @Slot(object)
    def job_progress(self, value):
        self.status.setText(f"Transferred {value.get('bytes', 0) / 1024 / 1024:.1f} MiB…")
