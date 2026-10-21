"""Offline reference management and observation-specific inspection."""
import json
from functools import partial
from PySide6.QtCore import Slot,Qt
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QComboBox,QLineEdit,
                              QFileDialog,QTableWidget,QTableWidgetItem,QHeaderView)
from .background_dialog import JobDialog
from .cell_reference import import_reference,list_references,activate_reference,active_reference
from .cell_matching import load_run_matches
from .cell_context import context_html,save_context,load_context


def import_job(root,source,metadata,cancelled,progress):
    return {'imported':import_reference(root,source,metadata,cancelled,progress)}


def match_job(config,run_id,cancelled,progress):
    if cancelled():raise ValueError('Cancelled')
    return {'matched':load_run_matches(config,run_id,cancelled)}


class CellReferenceDialog(JobDialog):
    def __init__(self,parent,config,run_ids=(),survey_path=None,on_candidate=None):
        super().__init__(parent);self.config=config;self.root=config.root/'cell-references'
        self.survey_path=survey_path;self.on_candidate=on_candidate;self.matches={};self.choices=[];self.assessments=[]
        self.setWindowTitle('Cell references and path assessment');self.resize(1100,760)
        layout=QVBoxLayout(self)
        intro=QLabel('Match full serving-cell identities against local references. Estimated cell positions are not verified towers. No online lookup is performed.')
        intro.setWordWrap(True);layout.addWidget(intro)
        self.datasets=QComboBox();layout.addWidget(self.datasets)
        actions=QHBoxLayout();layout.addLayout(actions)
        self.use=QPushButton('Use selected reference');self.use.clicked.connect(self.activate);actions.addWidget(self.use)
        self.clear=QPushButton('Deactivate reference');self.clear.clicked.connect(self.deactivate);actions.addWidget(self.clear)
        self.source=QLineEdit('OpenCellID');self.source.setPlaceholderText('Reference source')
        self.license=QLineEdit('CC BY-SA 4.0');self.license.setPlaceholderText('License / usage terms')
        self.date=QLineEdit('Unknown');self.date.setPlaceholderText('Dataset date')
        for title,widget in [('Source',self.source),('License',self.license),('Dataset date',self.date)]:
            line=QHBoxLayout();line.addWidget(QLabel(title));line.addWidget(widget);layout.addLayout(line)
        self.import_button=QPushButton('Import full OpenCellID CSV/GZIP or operator JSON…');self.import_button.clicked.connect(self.import_file);layout.addWidget(self.import_button)
        self.runs=QComboBox()
        for run_id in dict.fromkeys(run_ids):self.runs.addItem(str(run_id),str(run_id))
        layout.addWidget(self.runs)
        self.match_button=QPushButton('Match serving cells in selected test');self.match_button.clicked.connect(self.match);layout.addWidget(self.match_button)
        self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(['Observation','Radio / network','Status','Reference position','Distance m','Bearing °','Evidence'])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);layout.addWidget(self.table,1)
        self.table.itemSelectionChanged.connect(self.select_candidate)
        bottom=QHBoxLayout();layout.addLayout(bottom)
        self.map_button=QPushButton('Show selected bearing');self.map_button.clicked.connect(self.show_candidate);bottom.addWidget(self.map_button)
        self.path_button=QPushButton('Assess selected path…');self.path_button.clicked.connect(self.assess_path);bottom.addWidget(self.path_button)
        self.report_button=QPushButton('View context report');self.report_button.clicked.connect(self.view_report);bottom.addWidget(self.report_button)
        self.save_button=QPushButton('Save context to survey' if survey_path else 'Save context JSON…');self.save_button.clicked.connect(self.save);bottom.addWidget(self.save_button)
        self.status=QLabel('Import or select a reference snapshot, then choose a diagnostic.');self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
        self.controls=[self.datasets,self.use,self.clear,self.source,self.license,self.date,self.import_button,self.runs,self.match_button,self.map_button,self.path_button,self.report_button,self.save_button]
        self.refresh();self.select_candidate()
        self.runs.currentIndexChanged.connect(self.populate)
        if survey_path:
            try:
                saved=load_context(config,survey_path)
                if saved:
                    self.matches={r['run_id']:r for r in saved['context'].get('runs',[])}
                    self.assessments=saved['context'].get('assessments',[])
                    self.status.setText('Loaded saved context. Match again to update references.'+(' Saved context is out of date.' if saved['stale'] else ''))
                    self.populate()
            except (OSError,ValueError,KeyError) as exc:self.status.setText(str(exc))

    def refresh(self):
        self.datasets.clear()
        try:
            active=active_reference(self.root)
            for row in list_references(self.root):
                self.datasets.addItem(f"{row['source']} · {row['date']} · {row['accepted']:,} records"+(' · Active' if active and active['dataset_id']==row['dataset_id'] else ''),row['dataset_id'])
        except (OSError,ValueError,KeyError) as exc:self.status.setText(str(exc))
    @Slot()
    def activate(self):
        if self.datasets.currentData():
            try:activate_reference(self.root,self.datasets.currentData());self.refresh()
            except (OSError,ValueError) as exc:self.status.setText(str(exc))
    @Slot()
    def deactivate(self):
        try:activate_reference(self.root,None);self.refresh()
        except (OSError,ValueError) as exc:self.status.setText(str(exc))
    @Slot()
    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Import full reference snapshot','','Reference files (*.csv *.gz *.json)')
        if path:self.start_job(partial(import_job,self.root,path,dict(source=self.source.text(),license=self.license.text(),date=self.date.text())))
    @Slot()
    def match(self):
        run=self.runs.currentData()
        if run:self.start_job(partial(match_job,self.config,run))
    @Slot(object)
    def job_ready(self,value):
        if self.closing:return
        if 'imported' in value:
            row=value['imported'];self.refresh();self.status.setText(f"Imported {row['accepted']:,}; rejected {row['rejected']:,}; unsupported {row['unsupported']:,}. Select it and choose Use selected reference.")
        else:
            result=value['matched'];self.matches[result['run_id']]=result;self.populate()
            self.status.setText(f"Showing selected test (up to 200 observation/candidate rows). {result.get('omitted',0)} observations omitted. Select a candidate to inspect its bearing or assess a conditional terrain path.")
    def populate(self):
        self.choices=[]
        selected=self.matches.get(self.runs.currentData())
        for run in ([selected] if selected else []):
            for row in run['rows']:
                for candidate in row['candidates'] or [None]:
                    self.choices.append((run,row,candidate))
                    if len(self.choices)>=200:break
                if len(self.choices)>=200:break
            if len(self.choices)>=200:break
        self.table.setRowCount(len(self.choices))
        for i,(run,row,c) in enumerate(self.choices):
            values=[row['observation_id'],f"{row['radio']} / {row.get('carrier') or 'Not exposed'}",row['status'],f"{c['lat']}, {c['lon']}" if c else 'Unresolved',round(c['distance_m'],1) if c and c.get('distance_m') is not None else 'Unknown',round(c['bearing_deg'],1) if c and c.get('bearing_deg') is not None else 'Unknown',c.get('verification','Estimated') if c else 'No candidate']
            for j,value in enumerate(values):self.table.setItem(i,j,QTableWidgetItem(str(value)))
        self.select_candidate()
    def selected(self):
        i=self.table.currentRow()
        return self.choices[i] if 0<=i<len(self.choices) else None
    @Slot()
    def select_candidate(self):
        choice=self.selected();valid=bool(choice and choice[2] and choice[1]['location_quality']['qualified'])
        self.map_button.setEnabled(valid and self.on_candidate is not None and self.worker is None)
        self.path_button.setEnabled(valid and self.worker is None)
    def set_busy(self,busy):
        super().set_busy(busy)
        if not busy:self.select_candidate()
    @Slot()
    def show_candidate(self):
        choice=self.selected()
        if choice and choice[2] and self.on_candidate:self.on_candidate(choice[1],choice[2])
    @Slot()
    def assess_path(self):
        choice=self.selected()
        if not choice or not choice[2]:return
        from .path_assessment_ui import PathAssessmentDialog
        dialog=PathAssessmentDialog(self,self.config,dict(run_id=choice[0]['run_id'],capture_sha256=choice[0].get('capture_sha256'),observation=choice[1],candidate=choice[2]))
        if dialog.exec() and dialog.assessment:self.assessments.append(dialog.assessment)
    def context(self):return dict(schema_version=1,runs=list(self.matches.values()),assessments=self.assessments)
    @Slot()
    def view_report(self):
        from .report_viewer import ReportViewer
        html=('<html><body>'+context_html(self.context())+'</body></html>').encode()
        if len(html)>8*1024*1024:
            self.status.setText('Context exceeds the report viewing limit. Save fewer observations.');return
        self.viewer=ReportViewer(self,'Cell-reference context',reports=[('cell-context.html',html)]);self.viewer.show()
    @Slot()
    def save(self):
        try:
            if not self.matches:raise ValueError('Match a test before saving context.')
            if self.survey_path:save_context(self.config,self.survey_path,self.context())
            else:
                from .recovery import atomic_json
                path,_=QFileDialog.getSaveFileName(self,'Save reference context','cell-context.json','JSON (*.json)')
                if not path:return
                atomic_json(path,self.context())
            self.status.setText('Saved derived context. Original captured evidence is unchanged.')
        except (OSError,ValueError) as exc:self.status.setText(str(exc))
