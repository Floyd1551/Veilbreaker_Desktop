"""In-app management of regional terrain and structure reference packs."""
from functools import partial
import threading

from PySide6.QtCore import Qt, Slot, QStandardPaths
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
                               QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)
from pathlib import Path

from .background_dialog import JobDialog
from .regional_pack_download import download_and_install, download_terrain_batch, sanitized_source_url
from .regional_packs import RegionalPackStore
from .usgs_terrain_catalog import search_terrain_products, plan_terrain_products


def _install_job(root, kind, path, metadata, cancelled, progress):
    return {'installed': RegionalPackStore(root).install_local(kind, path, metadata, cancelled, progress)}


def _download_job(root, kind, url, metadata, checksum, cancelled, progress):
    return {'installed': download_and_install(RegionalPackStore(root), kind, url, metadata, cancelled,
                                              progress, expected_sha256=checksum or None)}


def _batch_job(root, products, datum, units, stop, cancelled, progress):
    return {'batch': download_terrain_batch(RegionalPackStore(root), products, datum, units,
                                           lambda: stop.is_set() or cancelled(), progress)}


class TerrainBatchReview(QDialog):
    """Review catalog products and their shared, operator-confirmed elevation metadata."""
    def __init__(self, parent, products, installed):
        super().__init__(parent)
        self.setWindowTitle('Review USGS terrain tiles')
        self.resize(750, 520)
        layout = QVBoxLayout(self)
        hint = QLabel('Select up to 20 tiles. Source dates and sizes are catalog estimates; raster extent and no-data are validated separately. Matching terrain packs are checksum-verified before they are skipped; conflicting datum or units stop the batch. Damaged packs are retained and a new copy is installed. Older redirected downloads may not record the original URL. Confirm datum and units from the source metadata for every selected tile.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.items = QListWidget()
        self.items.setAccessibleName('Terrain tiles to download')
        for product in products:
            origin = sanitized_source_url(product['url'])
            available = origin in installed
            item = QListWidgetItem(f"{product['title']} · {product.get('bytes', 0)/1024/1024:.0f} MiB · {product['source_date']}" + (' · Present; verify on download' if available else ''))
            item.setData(Qt.ItemDataRole.UserRole, product)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setToolTip(f"{product['source']} · {product['license']}\n{origin}\nReported bounds: {product.get('reported_bounds_wgs84', 'unknown')}")
            self.items.addItem(item)
        layout.addWidget(self.items, 1)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        form = QFormLayout()
        self.datum = QLineEdit()
        self.datum.setPlaceholderText('Confirm from source metadata, e.g. NAVD88')
        self.units = QComboBox()
        self.units.addItems(['Select elevation units', 'm', 'ft', 'us-ft'])
        form.addRow('Vertical datum', self.datum)
        form.addRow('Elevation units', self.units)
        layout.addLayout(form)
        controls = QHBoxLayout()
        cancel = QPushButton('Cancel')
        cancel.clicked.connect(self.reject)
        self.download_button = QPushButton('Download selected tiles')
        self.download_button.clicked.connect(self.accept)
        controls.addWidget(cancel)
        controls.addWidget(self.download_button)
        layout.addLayout(controls)
        self.items.itemChanged.connect(self.update_review)
        self.datum.textChanged.connect(self.update_review)
        self.units.currentIndexChanged.connect(self.update_review)
        self.update_review()

    def selected_products(self):
        return [self.items.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.items.count())
                if self.items.item(i).checkState() == Qt.CheckState.Checked]

    def update_review(self, *_args):
        products = self.selected_products()
        total = sum(p.get('bytes', 0) for p in products)
        self.summary.setText(f'{len(products)} selected · estimated {total / 1024 / 1024:.0f} MiB · maximum 20 tiles per batch')
        self.download_button.setEnabled(1 <= len(products) <= 20 and bool(self.datum.text().strip()) and self.units.currentIndex() > 0)


def _verify_job(root, pack_id, cancelled, progress):
    return {'verified': RegionalPackStore(root).verify(pack_id, cancelled), 'pack_id': pack_id}


def _search_usgs_job(bounds, cancelled, progress):
    result = search_terrain_products(bounds, cancelled, progress)
    result['plan'] = plan_terrain_products(bounds, result['products'])
    return {'catalog': result}


def _coverage_job(root, catalog_path, bounds, sample_grid, cancelled, progress):
    from .area_coverage import area_preview
    from .map_catalog import PackCatalog
    from .deployment_data import bundled_map
    from .map_pack import inspect_pack
    maps = PackCatalog(catalog_path).entries()
    included = bundled_map()
    if included and not any(row['path'] == str(included.resolve()) for row in maps):
        pack = inspect_pack(included)
        maps.append(dict(pack, available=True, source_date='Included map'))
    store=RegionalPackStore(Path(root)/'regional-packs')
    report=area_preview(bounds,store.list_packs(),maps,Path(root)/'cell-references',cancelled)
    if sample_grid is not None:
        from .terrain_area_sample import sample_area
        report['terrain']['sample']=sample_area(store,bounds,cancelled,grid_size=sample_grid)
    return {'coverage':report}


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
        prepare_scroll = QScrollArea()
        prepare_scroll.setWidgetResizable(True)
        prepare_scroll.setWidget(prepare_page)
        self.workspace_tabs.addTab(prepare_scroll, 'Add / download')
        coverage_page = QWidget()
        coverage_layout = QVBoxLayout(coverage_page)
        self.workspace_tabs.addTab(coverage_page, 'Area preview')
        coverage_hint = QLabel('Check offline data for a WGS84 area before field work. Extents are indicative; validate terrain, cell identities and site conditions separately.')
        coverage_hint.setWordWrap(True);coverage_layout.addWidget(coverage_hint)
        self.coverage_bounds = QLineEdit()
        self.coverage_bounds.setPlaceholderText('west, south, east, north · WGS84 degrees')
        self.coverage_bounds.setAccessibleName('Area preview bounds')
        coverage_layout.addWidget(self.coverage_bounds)
        coverage_actions = QHBoxLayout()
        self.coverage_preset = QPushButton('Huntsville, AL area')
        self.coverage_preset.clicked.connect(self.coverage_huntsville)
        self.coverage_check = QPushButton('Check local data')
        self.coverage_check.clicked.connect(self.check_coverage)
        self.coverage_save = QPushButton('Save preview report…')
        self.coverage_save.setEnabled(False)
        self.coverage_save.clicked.connect(self.save_coverage_report)
        coverage_actions.addWidget(self.coverage_preset);coverage_actions.addWidget(self.coverage_check);coverage_actions.addWidget(self.coverage_save)
        coverage_layout.addLayout(coverage_actions)
        self.coverage_sample = QCheckBox('Also sample terrain')
        self.coverage_sample.setToolTip('Optional sparse no-data check; it does not verify every raster cell or the file checksum.')
        self.coverage_grid = QComboBox()
        self.coverage_grid.setAccessibleName('Terrain sample grid density')
        for size in (11,21,41):
            self.coverage_grid.addItem(f'{size} × {size} · {size*size} points',size)
        self.coverage_grid.setEnabled(False)
        self.coverage_sample.toggled.connect(self.coverage_grid.setEnabled)
        sample_row=QHBoxLayout();sample_row.addWidget(self.coverage_sample);sample_row.addWidget(self.coverage_grid);coverage_layout.addLayout(sample_row)
        self.coverage_table = QTableWidget(0, 2)
        self.coverage_table.setHorizontalHeaderLabels(['Layer', 'Result'])
        self.coverage_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.coverage_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.coverage_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.coverage_table.itemSelectionChanged.connect(self.show_coverage_details)
        coverage_layout.addWidget(self.coverage_table, 1)
        self.coverage_details = QPlainTextEdit()
        self.coverage_details.setReadOnly(True)
        self.coverage_details.setAccessibleName('Selected coverage layer details')
        self.coverage_details.setMaximumHeight(150)
        self.coverage_details.setPlainText('Select an area and check local data, then select a layer for details.')
        coverage_layout.addWidget(self.coverage_details)
        self.coverage_result = None
        self.coverage_bounds.textChanged.connect(self.invalidate_coverage)
        self.coverage_sample.toggled.connect(self.invalidate_coverage)
        self.coverage_grid.currentIndexChanged.connect(self.invalidate_coverage)
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
        self.catalog_view = QComboBox()
        self.catalog_view.addItem('Suggested tiles', 'suggested')
        self.catalog_view.addItem('All catalog results', 'all')
        self.catalog_view.currentIndexChanged.connect(self.show_catalog_products)
        self.catalog_result = None
        self.catalog_summary = QLabel('Search an area to review suggested tiles and estimated download size.')
        self.catalog_summary.setWordWrap(True)
        self.catalog_summary.setTextFormat(Qt.TextFormat.PlainText)
        self.products = QComboBox()
        self.products.setAccessibleName('USGS terrain products for area')
        self.products.setMinimumContentsLength(25)
        self.products.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.use_product_button = QPushButton('Use selected product')
        self.use_product_button.clicked.connect(self.use_product)
        self.batch_button = QPushButton('Review suggested tiles…')
        self.batch_button.clicked.connect(self.review_suggested_tiles)
        prepare_layout.addWidget(self.search_button)
        prepare_layout.addWidget(self.catalog_view)
        prepare_layout.addWidget(self.catalog_summary)
        catalog_row.addWidget(self.products, 1)
        catalog_row.addWidget(self.use_product_button)
        prepare_layout.addLayout(catalog_row)
        prepare_layout.addWidget(self.batch_button)
        hint = QLabel('Structure bounds are declared by the dataset provider and do not prove completeness. Terrain bounds are read from the raster; no-data gaps may remain. Downloads contact only the URL you choose.')
        hint.setWordWrap(True)
        prepare_layout.addWidget(hint)
        actions = QHBoxLayout()
        self.import_button = QPushButton('Import local file…')
        self.import_button.clicked.connect(self.import_local)
        self.download_button = QPushButton('Download and install URL')
        self.download_button.clicked.connect(self.download)
        self.fcc_import_button = QPushButton('Import FCC structure archive…')
        self.fcc_import_button.clicked.connect(self.import_fcc_archive)
        prepare_layout.addWidget(self.fcc_import_button)
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
        self.batch_stop = threading.Event()
        self.batch_cancel = QPushButton('Cancel tile downloads')
        self.batch_cancel.clicked.connect(self.cancel_batch)
        self.batch_cancel.hide()
        layout.addWidget(self.batch_cancel)
        self.controls = [self.table, self.verify_button, self.remove_button, self.records_button,
                         self.kind, self.name, self.source, self.license, self.date, self.datum,
                         self.units, self.bounds, self.url, self.checksum, self.import_button,
                         self.download_button, self.search_button, self.products, self.use_product_button, self.catalog_view,
                         self.batch_button, self.fcc_import_button]
        self.controls.append(self.huntsville_button)
        self.controls.extend([self.coverage_bounds, self.coverage_preset, self.coverage_check, self.coverage_save, self.coverage_sample, self.coverage_grid, self.coverage_table])
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
        self.batch_button.setEnabled(terrain and bool(self.catalog_result and self.catalog_result.get('plan', {}).get('products')))

    def set_busy(self, busy):
        super().set_busy(busy)
        self.coverage_grid.setEnabled(not busy and self.coverage_sample.isChecked())
        self.coverage_save.setEnabled(not busy and self.coverage_result is not None)
        if not busy:
            self.update_kind()

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
    def coverage_huntsville(self):
        self.coverage_bounds.setText('-87.2, 34.3, -86.2, 35.2')

    def invalidate_coverage(self, *_args):
        if self.coverage_result is None:
            return
        self.coverage_result = None
        self.coverage_save.setEnabled(False)
        self.coverage_table.setRowCount(0)
        self.coverage_details.setPlainText('Area or sampling options changed. Check local data again before saving a report.')
        self.status.setText('Area preview needs to be checked again.')

    @Slot()
    def check_coverage(self):
        try:
            from .regional_packs import _bounds
            bounds = _bounds([float(part.strip()) for part in self.coverage_bounds.text().split(',')])
        except ValueError as exc:
            self.status.setText('Enter valid area bounds: '+str(exc));return
        catalog = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'map-catalog.json'
        self.coverage_result = None
        self.coverage_save.setEnabled(False)
        self.coverage_table.setRowCount(0)
        self.coverage_details.setPlainText('Checking the selected area…')
        self.status.setText('Checking local extents and cell records…')
        grid=self.coverage_grid.currentData() if self.coverage_sample.isChecked() else None
        self.start_job(partial(_coverage_job, self.store.root.parent, catalog, bounds, grid))

    @Slot()
    def save_coverage_report(self):
        if self.coverage_result is None:
            return
        target,_=QFileDialog.getSaveFileName(self,'Save area readiness preview','area-readiness.html','HTML report (*.html)')
        if not target:
            return
        try:
            from .area_coverage_report import report_html
            Path(target).write_text(report_html(self.coverage_result),encoding='utf-8')
            self.status.setText('Area readiness preview saved. It reflects the checked area at the time of the preview.')
        except (OSError,ValueError,KeyError) as exc:
            self.status.setText('Could not save preview: '+str(exc))

    @Slot()
    def show_coverage_details(self):
        index = self.coverage_table.currentRow()
        if self.coverage_result is None or not 0 <= index < 4:
            return
        key = ('map', 'terrain', 'cell', 'structures')[index]
        row = self.coverage_result[key]
        lines = [row['note']]
        if key == 'cell':
            if row.get('source'):
                lines.append(f"Source: {row['source']} · date: {row.get('date','Unknown')} · {row.get('attribution','')}")
                lines.append('Records: '+(', '.join(f"{v['radio']} {v['mcc']}/{v['mnc']}: {v['count']:,}" for v in row['groups']) or 'None in area'))
        else:
            for pack in row['packs'][:8]:
                detail=f"{pack.get('name','Unnamed')} · source date: {pack.get('source_date') or 'Unknown'}"
                if key == 'map':
                    detail+=f" · zoom {pack.get('minzoom','?')}–{pack.get('maxzoom','?')} · {pack.get('attribution','Attribution unavailable')}"
                else:
                    detail+=f" · source: {pack.get('source','Unknown')}"
                lines.append(detail)
            if len(row['packs']) > 8:
                lines.append(f"{len(row['packs'])-8} more packs overlap.")
            if key == 'terrain' and row.get('gaps'):
                lines.append('Example uncovered bounds: '+str(row['gaps'][:3]))
            if key == 'terrain' and (sample := row.get('sample')):
                lines.append(sample['note'])
                if sample['status'] == 'sampled':
                    lines.append(f"Grid: {sample['grid_size']} × {sample['grid_size']} · valid: {sample['valid']} · missing: {sample['missing']} (outside: {sample['outside']}; no-data: {sample['nodata']}).")
                    lines.append(f"Declared datum: {', '.join(sample['datums'])} · units: {', '.join(sample['units'])} · " + ('consistent declarations' if sample['compatible'] else 'mixed declarations; do not combine for a path assessment'))
                    if sample['examples']:lines.append('Example missing coordinates (longitude, latitude): '+str(sample['examples'][:3]))
                else:
                    lines.append('No overlapping available terrain packs were sampled.')
        self.coverage_details.setPlainText('\n'.join(lines))

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
        prefix = 'A pack from this source is present (size check only; verify its checksum). ' if self.product_installed(item) else ''
        self.status.setText(prefix+'USGS product selected. Confirm its vertical datum and elevation units from the product metadata before downloading. Product date is not the download date.')

    @Slot()
    def review_suggested_tiles(self):
        products = (self.catalog_result or {}).get('plan', {}).get('products', [])
        if not products:
            return
        installed = {origin for row in self.store.list_packs()
                     if row.get('status') == 'available' and row.get('kind') == 'terrain'
                     for origin in (row.get('download_origin'), row.get('download_requested_origin')) if origin}
        review = TerrainBatchReview(self, products, installed)
        if review.exec() != QDialog.DialogCode.Accepted:
            return
        self.batch_stop.clear()
        self.batch_cancel.show()
        self.batch_cancel.setEnabled(True)
        self.status.setText('Preparing selected terrain downloads…')
        self.start_job(partial(_batch_job, self.store.root, review.selected_products(),
                               review.datum.text().strip(), review.units.currentText(), self.batch_stop))

    @Slot()
    def cancel_batch(self):
        self.batch_stop.set()
        self.batch_cancel.setEnabled(False)
        self.status.setText('Cancelling the current tile; completed tiles remain installed…')

    @Slot()
    def import_fcc_archive(self):
        from .fcc_asr_ui import FccAsrImportDialog
        FccAsrImportDialog(self, self.store.root).exec()
        self.invalidate_coverage()
        self.refresh()

    def product_installed(self, item):
        from .regional_pack_download import sanitized_source_url
        try:
            origin = sanitized_source_url(item['url'])
        except (ValueError, KeyError):
            return False
        return any(row.get('status') == 'available' and row.get('kind') == 'terrain' and
                   origin in (row.get('download_origin'), row.get('download_requested_origin'))
                   for row in self.store.list_packs())

    @Slot()
    def show_catalog_products(self):
        catalog = self.catalog_result
        if not catalog:
            return
        plan = catalog.get('plan')
        items = plan['products'] if plan and self.catalog_view.currentData() == 'suggested' else catalog['products']
        self.products.clear()
        for item in items:
            text = f"{item['title']} · {item['bytes'] / 1024 / 1024:.0f} MiB · {item['source_date']}"
            if self.product_installed(item):
                text += ' · Installed (size check only)'
            self.products.addItem(text, item)
            self.products.setItemData(self.products.count()-1, f"Reported bounds: {item['reported_bounds_wgs84']}", Qt.ItemDataRole.ToolTipRole)
        self.update_kind()

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
            self.invalidate_coverage()
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
        if 'batch' in result:
            rows = result['batch']
            self.invalidate_coverage()
            self.refresh()
            if self.catalog_result:
                self.job_ready({'catalog': self.catalog_result})
            counts = {status: sum(row['status'] == status for row in rows)
                      for status in ('installed', 'skipped', 'failed', 'cancelled', 'not attempted')}
            message = 'Terrain batch: ' + ' · '.join(f'{count} {name}' for name, count in counts.items() if count)
            error = next((row.get('error') for row in rows if row['status'] == 'failed'), None)
            self.status.setText(message + (f'. {error}' if error else '') + '. Completed tiles remain installed.')
        elif coverage := result.get('coverage'):
            self.coverage_result = coverage
            self.coverage_save.setEnabled(self.worker is None)
            self.coverage_table.setRowCount(4)
            for index, (key, title) in enumerate((('map','Map'),('terrain','Terrain'),('cell','Cell references'),('structures','Structures'))):
                item=coverage[key]
                summary=item['status']
                if key == 'cell' and item['count'] is not None:
                    summary += f" · {item['count']:,} records"
                if key == 'terrain' and item['gap_count']:
                    summary += f" · {item['gap_count']} extent gaps"
                if key == 'terrain' and (sample := item.get('sample')) and sample['status'] == 'sampled':
                    summary += f" · {sample['missing']}/{sample['total']} sampled missing"
                self.coverage_table.setItem(index,0,QTableWidgetItem(title))
                self.coverage_table.setItem(index,1,QTableWidgetItem(summary))
            self.coverage_table.selectRow(0)
            self.show_coverage_details()
            self.status.setText(f"Area {coverage['bounds']} checked. Extents and reference records do not guarantee field coverage.")
        elif row := result.get('installed'):
            self.invalidate_coverage()
            self.refresh(row['pack_id'])
            self.status.setText(f"Installed {row['name']} · {row['bytes'] / 1024 / 1024:.1f} MiB · SHA-256 {row['sha256']}.")
        elif catalog := result.get('catalog'):
            self.catalog_result = catalog
            plan = catalog.get('plan')
            if plan:
                installed = [p for p in plan['products'] if self.product_installed(p)]
                remaining = plan['bytes'] - sum(p['bytes'] for p in installed)
                self.catalog_summary.setText(f"{len(plan['products'])} suggested · {len(installed)} installed (size check only) · {remaining/1024/1024:.0f} MiB remaining if installed checksums match · {plan['gap_count']} extent gaps · {plan['duplicate_count']} older duplicate extents. Reported bounds only; no-data and datum remain unverified." + (' Catalog results are truncated.' if catalog.get('truncated') else ''))
            self.show_catalog_products()
            self.status.setText(f"USGS returned {catalog['total']} products. Select a suggested tile or view all results, then confirm datum and units. Historical products may appear.")
        elif 'verified' in result:
            self.status.setText('Pack SHA-256 matches its recorded bytes.' if result['verified'] else
                                'Pack SHA-256 does not match; do not use it for assessment.')

    @Slot(object)
    def job_progress(self, value):
        if value.get('event'):
            label = f"Tile {value['index']}/{value['total']} · {value['title']}"
            if value['event'] == 'progress':
                if value.get('phase') == 'verify':
                    label += ' · Verifying installed checksum'
                else:
                    phase = 'Downloading' if value.get('phase') == 'download' else 'Installing'
                    label += f" · {phase} {value.get('bytes', 0) / 1024 / 1024:.1f} MiB"
            elif value['event'] == 'result':
                label += f" · {value['status']}"
            self.status.setText(label)
        else:
            self.status.setText(f"{value.get('phase', 'Transferred').capitalize()} {value.get('bytes', 0) / 1024 / 1024:.1f} MiB…")

    @Slot()
    def job_finished(self):
        self.batch_cancel.hide()
        super().job_finished()
