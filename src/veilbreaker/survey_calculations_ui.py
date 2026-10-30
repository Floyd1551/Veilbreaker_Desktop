"""Attach saved calculation snapshots as operator planning context."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox,QDialog,QFileDialog,QFormLayout,QHeaderView,QHBoxLayout,
    QLabel,QLineEdit,QMessageBox,QPlainTextEdit,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout)
from .field_tools import format_snapshot
from .survey import read_session
from .survey_calculations import attach_calculation,read_snapshot,remove_calculation


class CalculationsDialog(QDialog):
    def __init__(self,parent,config,path,selected_run=None):
        super().__init__(parent)
        self.config,self.path=config,path
        self.setWindowTitle('Survey calculations');self.resize(900,650)
        layout=QVBoxLayout(self)
        intro=QLabel('Attach a JSON calculation snapshot saved from Tools. These are operator-entered estimates, not measured evidence.')
        intro.setWordWrap(True);layout.addWidget(intro)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['Attached UTC','Point','Calculation'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);layout.addWidget(self.table,1)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setMaximumHeight(170)
        self.details.setAccessibleName('Selected calculation details');layout.addWidget(self.details)
        form=QFormLayout();self.point=QComboBox();self.point.addItem('Survey-wide',None)
        session=read_session(config,path)
        for step in session['steps']:self.point.addItem(step.get('label','Unnamed point'),step['run_id'])
        if selected_run is not None:self.point.setCurrentIndex(max(0,self.point.findData(selected_run)))
        self.notes=QLineEdit();self.notes.setMaxLength(1000);self.notes.setPlaceholderText('Optional context or purpose')
        form.addRow('Survey point',self.point);form.addRow('Notes',self.notes);layout.addLayout(form)
        actions=QHBoxLayout();self.attach_button=QPushButton('Attach saved JSON…');self.attach_button.clicked.connect(self.choose_file);actions.addWidget(self.attach_button)
        self.remove_button=QPushButton('Remove selected…');self.remove_button.clicked.connect(self.remove);actions.addWidget(self.remove_button)
        close=QPushButton('Close');close.clicked.connect(self.accept);actions.addWidget(close);layout.addLayout(actions)
        self.status=QLabel();self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
        self.table.itemSelectionChanged.connect(self.selection_changed);self.refresh()

    def refresh(self):
        session=read_session(self.config,self.path)
        self.editable=session.get('lifecycle')!='completed' and session.get('status')!='running'
        self.attach_button.setEnabled(self.editable);self.point.setEnabled(self.editable);self.notes.setEnabled(self.editable)
        labels={step['run_id']:step.get('label','Unnamed point') for step in session['steps']}
        records=session.get('calculations',[])
        self.rows=[row for row in records if isinstance(row,dict) and not row.get('deleted_utc') and isinstance(row.get('snapshot'),dict)] if isinstance(records,list) else []
        self.table.setRowCount(len(self.rows))
        for i,row in enumerate(self.rows):
            run=row.get('run_id');values=[row.get('attached_utc','Unknown'),labels.get(run,'Survey-wide' if not run else 'Point unavailable'),row['snapshot'].get('title','Calculation')]
            for j,value in enumerate(values):self.table.setItem(i,j,QTableWidgetItem(str(value)))
        self.status.setText('Saved calculations are estimates. The original test evidence is unchanged.' if self.editable else 'Reopen the survey or wait for collection to finish before changing calculations.')
        self.selection_changed()

    def selection_changed(self):
        index=self.table.currentRow();valid=0 <= index < len(self.rows)
        self.remove_button.setEnabled(self.editable and valid)
        if valid:
            try:self.details.setPlainText('Survey context: '+(self.rows[index].get('notes') or 'None recorded')+'\n\n'+format_snapshot(self.rows[index]['snapshot']))
            except (TypeError,ValueError,KeyError):self.details.setPlainText('This stored calculation cannot be displayed.')
        else:self.details.setPlainText('Select a calculation to review its inputs, result and limitations.')

    def choose_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Attach saved calculation','','Calculation snapshot (*.json)')
        if path:self.attach_file(path)

    def attach_file(self,path):
        try:
            snapshot=read_snapshot(path)
            attach_calculation(self.config,self.path,snapshot,run_id=self.point.currentData(),notes=self.notes.text())
            self.notes.clear();self.refresh();self.status.setText('Calculated estimate attached to the survey.')
        except (OSError,ValueError,KeyError) as exc:self.status.setText(str(exc))

    def remove(self):
        index=self.table.currentRow()
        if not 0<=index<len(self.rows):return
        if QMessageBox.question(self,'Remove calculation','Remove this calculation from the active report? Its removal remains in the survey journal.') != QMessageBox.StandardButton.Yes:return
        try:
            remove_calculation(self.config,self.path,self.rows[index]['id']);self.refresh()
            self.status.setText('Calculation removed; the survey journal retains its removal time.')
        except (OSError,ValueError,KeyError) as exc:self.status.setText(str(exc))
