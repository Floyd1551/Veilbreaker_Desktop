"""Offline map window with native evidence fallback."""
import json
from pathlib import Path
from PySide6.QtCore import QObject,Signal,Slot,Qt,QUrl,QSettings,QTimer,QStandardPaths
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QCheckBox,QComboBox,QSplitter,QTableWidget,QTableWidgetItem,QHeaderView,QFileDialog,QMessageBox,QWidget)
from .map_data import map_bounds,export_geojson
from .map_server import MapServer
from .survey_metrics import (METRICS, UNATTRIBUTED, available_metrics, clean_metrics,
    metric_scale, point_metric, provenance_label, source_options, source_matches)
from .display_labels import source_label

class MapBridge(QObject):
    refresh=Signal()
    highlight=Signal(str)
    fit=Signal()
    def __init__(self,window):super().__init__(window);self.window=window
    @Slot(str)
    def selectFeature(self,feature_id):
        if feature_id in {r['id'] for r in self.window.visible_rows}:self.window.select_feature(feature_id)
    @Slot(float,float)
    def pickCoordinate(self, longitude, latitude):
        if self.window.pick_callback is not None:
            from .survey_spatial import _number
            try:
                longitude = _number(longitude, -180, 180)
                latitude = _number(latitude, -85.05112878, 85.05112878)
            except ValueError:
                return
            self.window.pick_callback(longitude, latitude)
    @Slot()
    def ready(self):
        self.window.ready=True;self.window.renderer_status.setText('Offline map ready · receiver positions, not tower locations')
    @Slot(str)
    def failed(self,message):
        self.window.renderer_status.setText('Map unavailable: '+message[:240]+'. Evidence remains available below.')

class MapWindow(QDialog):
    def __init__(self,parent,model,open_run,enable_web=True,restore_pack=True,config=None,pick_callback=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle('Veilbreaker · Survey map');self.resize(1200,850)
        self.config=config;self.cell_overlay=None
        self.pick_callback=pick_callback
        self.model=model;self.open_run_callback=open_run;self.selected=None;self.ready=False;self.web=None
        self.bridge=MapBridge(self);self.settings=QSettings('Veilbreaker','Maps')
        from .map_catalog import PackCatalog
        self.catalog=PackCatalog(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))/'map-catalog.json')
        self.server=MapServer(Path(__file__).parent/'assets/maps');self.server.start()
        outer=QVBoxLayout(self)
        title=QLabel('Survey map');title.setObjectName('title');outer.addWidget(title)
        if pick_callback:
            hint=QLabel('Placement mode: click the map to choose coordinates, then review and save in the placement editor.')
            hint.setWordWrap(True);outer.addWidget(hint)
        self.summary=QLabel();self.summary.setWordWrap(True);outer.addWidget(self.summary)
        actions=QHBoxLayout()
        def action(text,callback):
            b=QPushButton(text);b.clicked.connect(callback);actions.addWidget(b);return b
        action('Fit measurements',lambda:self.bridge.fit.emit())
        action('Import offline map…',self.import_pack)
        action('Clear basemap',self.clear_pack)
        action('Export GeoJSON…',self.export)
        if config:action('Cell references / assess path…',self.cell_references)
        self.questionable=QCheckBox('Show questionable fixes');actions.addWidget(self.questionable)
        outer.addLayout(actions)
        packs=QHBoxLayout()
        self.pack_selector=QComboBox();self.pack_selector.setAccessibleName('Saved offline maps');packs.addWidget(self.pack_selector,1)
        use_pack=QPushButton('Use selected map');use_pack.clicked.connect(self.use_saved_pack);packs.addWidget(use_pack)
        remove_pack=QPushButton('Remove registration');remove_pack.clicked.connect(self.remove_saved_pack);packs.addWidget(remove_pack)
        outer.addLayout(packs);self.refresh_catalog()
        self.run_filter=QComboBox();self.run_filter.addItem('Survey overview · first qualified fix per run',None)
        seen=set()
        for row in model['rows']:
            if row['run_id'] not in seen:
                seen.add(row['run_id']);self.run_filter.addItem(row['label']+' · all observations',row['run_id'])
        outer.addWidget(self.run_filter)
        metric_row=QHBoxLayout()
        metric_row.addWidget(QLabel('Measured metric'))
        self.metric_selector=QComboBox();self.metric_selector.setAccessibleName('Survey measured metric')
        self.metric_selector.addItem('Location provenance',None)
        for key in available_metrics(model):
            title,unit=METRICS[key]
            self.metric_selector.addItem(f'{title} ({unit})',key)
        metric_row.addWidget(self.metric_selector,1)
        outer.addLayout(metric_row)
        source_row=QHBoxLayout()
        source_row.addWidget(QLabel('Metric source'))
        self.source_filter=QComboBox();self.source_filter.setAccessibleName('Filter survey metrics by recorded source')
        self.source_filter.addItem('All recorded sources',None)
        source_row.addWidget(self.source_filter,1)
        outer.addLayout(source_row)
        self.metric_legend=QLabel()
        self.metric_legend.setWordWrap(True)
        self.metric_legend.setTextFormat(Qt.TextFormat.PlainText)
        outer.addWidget(self.metric_legend)
        self.metric_ramp=QWidget()
        self.metric_ramp.setFixedHeight(8)
        self.metric_ramp.setAccessibleName('Relative measured-value color scale: blue low, amber high')
        self.metric_ramp.setStyleSheet('background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4877ca,stop:1 #f5bf5d); border-radius: 4px;')
        outer.addWidget(self.metric_ramp)
        self.pack_status=QLabel('Basemap unavailable · Import a Protomaps .pmtiles regional map. Points work without a basemap.')
        self.pack_status.setTextFormat(Qt.TextFormat.PlainText);self.pack_status.setWordWrap(True);outer.addWidget(self.pack_status)
        self.renderer_status=QLabel('Loading offline map…');self.renderer_status.setWordWrap(True);self.renderer_status.setTextFormat(Qt.TextFormat.PlainText);outer.addWidget(self.renderer_status)
        self.splitter=QSplitter(Qt.Orientation.Vertical);outer.addWidget(self.splitter,1)
        self.map_container=QWidget();self.map_layout=QVBoxLayout(self.map_container);self.map_layout.setContentsMargins(0,0,0,0);self.splitter.addWidget(self.map_container)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(['Run / point','Observation','GPS quality','Accuracy (m)','Age (ms)','Selected run metric'])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.splitter.addWidget(self.table);self.splitter.setSizes([460,180])
        self.details=QLabel('Select a measurement to inspect its location evidence.');self.details.setWordWrap(True);self.details.setTextFormat(Qt.TextFormat.PlainText);outer.addWidget(self.details)
        self.open_button=QPushButton('Open diagnostic');self.open_button.setEnabled(False);self.open_button.clicked.connect(self.open_diagnostic);outer.addWidget(self.open_button)
        self.run_filter.currentIndexChanged.connect(self.change_run);self.questionable.toggled.connect(self.update_view)
        self.metric_selector.currentIndexChanged.connect(self.change_metric)
        self.source_filter.currentIndexChanged.connect(self.update_view)
        self.table.itemSelectionChanged.connect(self.table_selected)
        self.update_view()
        if restore_pack:
            path=self.settings.value('pack_path','')
            if path:
                try:self.load_pack(path,persist=False)
                except (OSError,ValueError) as exc:self.pack_status.setText('Basemap unavailable · '+str(exc))
        if enable_web:
            try:self.create_web()
            except (ImportError,RuntimeError,OSError) as exc:self.bridge.failed(str(exc))
        else:self.bridge.failed('renderer unavailable')
        if not self.web:self.map_container.hide()
        QTimer.singleShot(20000,self.check_ready)
    def check_ready(self):
        if self.web and not self.ready:self.bridge.failed('renderer did not initialize')
    def visible_features(self):
        run=self.run_filter.currentData();questionable=self.questionable.isChecked()
        key=self.metric_selector.currentData();source=self.source_filter.currentData()
        return [f for f in self.model['features']['features'] if (run is None or f['properties']['run_id']==run) and
                (source is None or (key in clean_metrics(self.model.get('run_metrics',{}).get(f['properties']['run_id'],{})) and
                                    source_matches(self.model,f['properties']['run_id'],key,source))) and
                (f['properties'].get('manual') or (f['properties']['quality']['qualified'] and (run is not None or f['id'] in self.model['representatives'])) or (questionable and not f['properties']['quality']['qualified']))]
    def change_metric(self):
        key=self.metric_selector.currentData()
        selected=self.source_filter.currentData()
        self.source_filter.blockSignals(True)
        self.source_filter.clear()
        self.source_filter.addItem('All recorded sources',None)
        for source in source_options(self.model,key) if key else []:
            self.source_filter.addItem('Source unrecorded' if source==UNATTRIBUTED else source_label(source),source)
        index=self.source_filter.findData(selected)
        self.source_filter.setCurrentIndex(max(0,index))
        self.source_filter.blockSignals(False)
        self.update_view()
    def update_view(self):
        features=self.visible_features();ids={f['id'] for f in features};run=self.run_filter.currentData()
        metric_key=self.metric_selector.currentData()
        source=self.source_filter.currentData()
        metric_model=dict(self.model,run_metrics={run_id:values for run_id,values in self.model.get('run_metrics',{}).items()
            if source_matches(self.model,run_id,metric_key,source)})
        scale=metric_scale(metric_model,metric_key) if metric_key else None
        self.metric_ramp.setVisible(bool(scale))
        if scale:
            single=scale['minimum']==scale['maximum']
            self.metric_ramp.setStyleSheet('background: #52b7ca; border-radius: 4px;' if single else
                'background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4877ca,stop:1 #f5bf5d); border-radius: 4px;')
            range_text=(f"single value {scale['minimum']:g} {scale['unit']}" if single else
                        f"{scale['minimum']:g} to {scale['maximum']:g} {scale['unit']}")
            count_text=f"{scale['count']} saved {'run' if scale['count']==1 else 'runs'}"
            self.metric_legend.setText(f"{scale['label']} · {range_text} across {count_text}. Colors show relative measured values, not a quality verdict. Run metrics are not per-fix readings. Purple outline = operator placement; teal = qualified GPS; amber = questionable GPS; gray fill = value unavailable.")
        else:
            self.metric_legend.setText('Location provenance · teal = qualified GPS; purple = operator placement; amber = questionable GPS. Choose a saved run metric to color positioned scans.')
        coordinate_ids={f['id'] for f in self.model['features']['features']}
        self.visible_rows=[r for r in self.model['rows'] if (run is None or r['run_id']==run) and (r['id'] in ids or r['id'] not in coordinate_ids)]
        self.table.blockSignals(True);self.table.clearContents();self.table.setRowCount(len(self.visible_rows))
        for i,row in enumerate(self.visible_rows):
            metric=point_metric(self.model,row['run_id'],metric_key,scale) if metric_key else None
            metric_text=f"{metric['label']} {metric['value']:g} {metric['unit']}" if metric else '—'
            for j,value in enumerate([row['label'],row['observation_id'],row['quality']['label'],row.get('horizontal_accuracy_m'),row.get('fix_age_ms'),metric_text]):
                self.table.setItem(i,j,QTableWidgetItem('Not exposed' if value is None else str(value)))
        self.table.blockSignals(False);self.selected=None;self.open_button.setEnabled(False)
        counts=self.model['counts'];self.summary.setText(f"{counts['mapped']} qualified plottable observations · {counts['questionable']} questionable fixes · {counts['unpositioned_runs']} runs without a qualified position" + (' · '+ ' '.join(self.model['warnings'][:3]) if self.model['warnings'] else ''))
        if counts.get('manual'):
            self.summary.setText(self.summary.text()+f" · {counts['manual']} manual placements (purple; not GPS)")
        if source is not None:
            self.summary.setText(self.summary.text()+f' · {len(features)} positioned observations shown for selected metric source')
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        if not self.model['rows']:self.details.setText('No GPS evidence. Enable phone location during capture, then open the saved diagnostic or survey here.')
        else:self.details.setText('Select a measurement. Questionable fixes are hidden until enabled.')
        pack=self.server.pack
        rendered=[]
        for feature in features:
            if not feature['properties']['renderable']:
                continue
            properties=dict(feature['properties'])
            if metric_key and (properties.get('manual') or feature['id'] in self.model['representatives']):
                metric=point_metric(self.model,properties['run_id'],metric_key,scale)
                if metric:
                    properties['metric_color']=metric['color']
                    properties['metric_value']=metric['value']
            rendered.append(dict(feature,properties=properties))
        self.server.set_model(dict(features=dict(type='FeatureCollection',features=rendered),metric_mode=bool(metric_key),bounds=self.cell_overlay['bounds'] if self.cell_overlay else map_bounds(features),cell_overlay=self.cell_overlay,pack={k:pack[k] for k in ('name','attribution','minzoom','maxzoom','resource')} if pack else None))
        self.bridge.refresh.emit()
    def change_run(self):
        self.cell_overlay=None;self.update_view()
    def cell_references(self):
        from .cell_reference_ui import CellReferenceDialog
        self.reference_dialog=CellReferenceDialog(self,self.config,[r['run_id'] for r in self.model['rows']],self.model.get('survey_path'),self.show_cell_candidate)
        self.reference_dialog.show()
    def show_cell_candidate(self,row,candidate):
        location=row['location']
        a=[location['longitude_deg'],location['latitude_deg']];b=[candidate['lon'],candidate['lat']]
        if abs(a[1])>85.05112878 or abs(b[1])>85.05112878:
            self.details.setText('Selected path is outside the map projection. Numerical context remains available.');return
        features=[dict(geometry=dict(coordinates=c),properties=dict(renderable=True)) for c in (a,b)]
        self.cell_overlay=dict(receiver=a,candidate=b,bounds=map_bounds(features))
        self.update_view()
        self.details.setText('Selected receiver-to-reference bearing; this line does not establish LOS or a physical tower identity.')
    def select_feature(self,feature_id):
        for i,row in enumerate(self.visible_rows):
            if row['id']==feature_id:
                self.table.blockSignals(True);self.table.selectRow(i);self.table.blockSignals(False)
                self.selected=row;self.open_button.setEnabled(True)
                def val(key):return str(row[key]) if row.get(key) is not None else 'Not exposed'
                metric_key=self.metric_selector.currentData()
                scale=metric_scale(self.model,metric_key) if metric_key else None
                metric=point_metric(self.model,row['run_id'],metric_key,scale) if metric_key else None
                metric_note=(f"\n{metric['label']} {metric['value']:g} {metric['unit']} · "
                             + ('derived live-session value' if metric_key.startswith('live_phone_') else 'saved run metric')
                             + ', not an individual fix reading.'
                             if metric else ('\nSelected run metric unavailable.' if metric_key else ''))
                context=self.model.get('run_context',{}).get(row['run_id'],{}).get(metric_key,{}) if metric_key else {}
                source_note='\n'+provenance_label(context) if metric_key else ''
                self.details.setText(f"{row['label']} · {row['observation_id']}\nLatitude {val('latitude_deg')} · Longitude {val('longitude_deg')} · Accuracy {val('horizontal_accuracy_m')} m · Age {val('fix_age_ms')} ms\n{row['quality']['label']} · {val('source')} / {val('provider')} · Fix {val('fix_utc')}" + metric_note + source_note + ('\nPosition cannot be plotted in Web Mercator.' if not row['renderable'] else ''))
                self.bridge.highlight.emit(feature_id);return
    def table_selected(self):
        i=self.table.currentRow()
        if 0<=i<len(self.visible_rows):self.select_feature(self.visible_rows[i]['id'])
    def open_diagnostic(self):
        if self.selected:self.open_run_callback(self.selected['run_id'])
    def load_pack(self,path,persist=True):
        pack=self.server.set_pack(Path(path))
        self.pack_status.setText(f"{pack['name']} · {pack['size']/1024/1024:.1f} MiB · {pack['attribution']}")
        if persist:
            self.catalog.register(path);self.refresh_catalog()
            self.settings.setValue('pack_path',str(Path(path).resolve()))
        self.update_view()
    def refresh_catalog(self):
        self.pack_selector.clear()
        try:
            for row in self.catalog.entries():
                text=f"{Path(row['path']).name} · z{row.get('minzoom')}–{row.get('maxzoom')} · {row.get('size',0)/1024/1024:.0f} MiB · source {row.get('source_date') or 'date unknown'}"
                if not row['available']:text+=' · file missing — import its new location'
                self.pack_selector.addItem(text,row['path'])
                self.pack_selector.setItemData(self.pack_selector.count()-1,str(row.get('bounds'))+' · '+row['path'],Qt.ItemDataRole.ToolTipRole)
        except (OSError,ValueError,TypeError) as exc:
            self.pack_selector.addItem('Catalog unavailable: '+str(exc),None)
    def use_saved_pack(self):
        path=self.pack_selector.currentData()
        if path:
            try:self.load_pack(path)
            except (OSError,ValueError) as exc:QMessageBox.warning(self,'Cannot load map',str(exc))
    def remove_saved_pack(self):
        path=self.pack_selector.currentData()
        if path:
            try:
                self.catalog.remove(path)
                if self.settings.value('pack_path','')==path:self.clear_pack()
                self.refresh_catalog()
            except (OSError,ValueError) as exc:QMessageBox.warning(self,'Cannot update map list',str(exc))
    def clear_pack(self):
        self.server.set_pack(None);self.settings.remove('pack_path');self.pack_status.setText('Basemap unavailable · Coordinate-only view. Import a Protomaps regional map.');self.update_view()
    def import_pack(self):
        path,_=QFileDialog.getOpenFileName(self,'Import offline Protomaps map','','PMTiles map (*.pmtiles)')
        if path:
            try:self.load_pack(path)
            except (OSError,ValueError) as exc:QMessageBox.warning(self,'Cannot load map',str(exc))
    def export(self):
        path,_=QFileDialog.getSaveFileName(self,'Export visible location evidence','survey-locations.geojson','GeoJSON (*.geojson)')
        if path:
            try:Path(path).write_text(export_geojson(self.model,[f['id'] for f in self.visible_features()]),encoding='utf-8')
            except OSError as exc:QMessageBox.warning(self,'Cannot export',str(exc))
    def create_web(self):
        from .map_web import create_view
        self.web,self.profile,self.interceptor=create_view(self,self.server.url,self.bridge)
        self.map_layout.addWidget(self.web);self.web.load(QUrl(self.server.url+'index.html'))
    def closeEvent(self,event):
        from .background_dialog import defer_background_close
        if defer_background_close(self,event):return
        if self.web:self.web.stop();self.web.setUrl(QUrl('about:blank'))
        self.server.close();super().closeEvent(event)
