"""Manage operator observations without changing collected run evidence."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout)

from .survey import read_session
from .survey_observations import CATEGORIES, MATERIALS, add_observation, remove_observation


class ObservationsDialog(QDialog):
    def __init__(self,parent,config,path,selected_run=None):
        super().__init__(parent)
        self.config,self.path=config,path
        self.setWindowTitle('Survey operator observations')
        self.resize(900,650)
        layout=QVBoxLayout(self)
        intro=QLabel('Record what you observe at the site. Observations are operator input; they do not measure material loss or prove a propagation effect.')
        intro.setWordWrap(True);layout.addWidget(intro)
        self.table=QTableWidget(0,4)
        self.table.setHorizontalHeaderLabels(['Recorded UTC','Point','Type / material','Description'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table,1)
        form=QFormLayout()
        self.point=QComboBox();self.point.addItem('Survey-wide',None)
        session=read_session(config,path)
        for step in session['steps']:
            self.point.addItem(step.get('label','Unnamed point'),step['run_id'])
        if selected_run is not None:
            self.point.setCurrentIndex(max(0,self.point.findData(selected_run)))
        self.category=QComboBox();self.category.addItems(CATEGORIES)
        self.material=QComboBox();self.material.addItems(MATERIALS)
        self.author=QLineEdit();self.author.setMaxLength(80);self.author.setPlaceholderText('Optional')
        self.description=QPlainTextEdit();self.description.setMaximumHeight(80)
        self.description.setPlaceholderText('Describe what you saw and where it was relative to the point.')
        for title,control in [('Survey point',self.point),('Observation type',self.category),('Material',self.material),('Operator',self.author),('Description',self.description)]:
            form.addRow(title,control)
        layout.addLayout(form)
        actions=QHBoxLayout()
        self.add_button=QPushButton('Add observation');self.add_button.clicked.connect(self.add);actions.addWidget(self.add_button)
        self.remove_button=QPushButton('Remove selected…');self.remove_button.clicked.connect(self.remove);actions.addWidget(self.remove_button)
        close=QPushButton('Close');close.clicked.connect(self.accept);actions.addWidget(close)
        layout.addLayout(actions)
        self.status=QLabel();self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.refresh()

    def refresh(self):
        session=read_session(self.config,self.path)
        self.editable=session.get('lifecycle')!='completed' and session.get('status')!='running'
        self.add_button.setEnabled(self.editable)
        for control in (self.point,self.category,self.material,self.author,self.description):control.setEnabled(self.editable)
        labels={step['run_id']:step.get('label','Unnamed point') for step in session['steps']}
        rows=[row for row in session.get('observations',[]) if isinstance(row,dict) and not row.get('deleted_utc')]
        self.table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            values=[row.get('recorded_utc','Unknown'),labels.get(row.get('run_id'),'Survey-wide' if not row.get('run_id') else 'Point unavailable'),
                    str(row.get('category','Unknown'))+' / '+str(row.get('material','Unknown')),row.get('description','')]
            for j,value in enumerate(values):
                item=QTableWidgetItem(str(value))
                if j==0:item.setData(Qt.ItemDataRole.UserRole,row.get('id'))
                self.table.setItem(i,j,item)
        self.status.setText('Observations are included in survey reports and exports.' if self.editable else
                            'Reopen the survey or wait for collection to finish before changing observations.')
        self.selection_changed()

    def selection_changed(self):
        self.remove_button.setEnabled(self.editable and self.table.currentRow()>=0)

    def add(self):
        try:
            add_observation(self.config,self.path,dict(run_id=self.point.currentData(),category=self.category.currentText(),
                material=self.material.currentText(),description=self.description.toPlainText(),author=self.author.text()))
            self.description.clear();self.refresh();self.status.setText('Operator observation saved.')
        except (OSError,ValueError,KeyError) as exc:self.status.setText(str(exc))

    def remove(self):
        index=self.table.currentRow()
        if index<0:return
        if QMessageBox.question(self,'Remove observation','Remove this observation from the active survey report? Its removal remains recorded in the survey.') != QMessageBox.StandardButton.Yes:return
        try:
            remove_observation(self.config,self.path,self.table.item(index,0).data(Qt.ItemDataRole.UserRole))
            self.refresh();self.status.setText('Observation removed; its removal is retained in survey history.')
        except (OSError,ValueError,KeyError) as exc:self.status.setText(str(exc))
