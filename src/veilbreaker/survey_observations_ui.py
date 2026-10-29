"""Manage operator observations without changing collected run evidence."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout)

from .survey import read_session
from .survey_observations import CATEGORIES, MATERIALS, add_observation, remove_observation, update_observation
from .widgets import FlowLayout


class ObservationsDialog(QDialog):
    def __init__(self,parent,config,path,selected_run=None):
        super().__init__(parent)
        self.config,self.path=config,path
        self.editing_id=None
        self.editing_revision=None
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
        actions=FlowLayout()
        self.add_button=QPushButton('Add observation');self.add_button.clicked.connect(self.add);actions.addWidget(self.add_button)
        self.edit_button=QPushButton('Edit selected');self.edit_button.clicked.connect(self.start_edit);actions.addWidget(self.edit_button)
        self.history_button=QPushButton('View edit history');self.history_button.clicked.connect(self.view_history);actions.addWidget(self.history_button)
        self.cancel_button=QPushButton('Cancel edit');self.cancel_button.clicked.connect(self.cancel_edit);self.cancel_button.hide();actions.addWidget(self.cancel_button)
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
        self.rows_by_id={row.get('id'):row for row in rows}
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
        enabled=self.editable and self.editing_id is None and self.table.currentRow()>=0
        self.remove_button.setEnabled(enabled)
        self.edit_button.setEnabled(enabled)
        self.history_button.setEnabled(self.editing_id is None and self.table.currentRow()>=0)

    def view_history(self):
        index=self.table.currentRow()
        if index<0 or not self.table.item(index,0):return
        observation_id=self.table.item(index,0).data(Qt.ItemDataRole.UserRole)
        try:
            session=read_session(self.config,self.path)
            row=next((r for r in session.get('observations',[]) if isinstance(r,dict) and r.get('id')==observation_id and not r.get('deleted_utc')),None)
            if row is None:raise ValueError('Observation is no longer available.')
            history=row.get('history',[])
            if not isinstance(history,list):raise ValueError('Observation edit history is invalid.')
            labels={s['run_id']:s.get('label','Unnamed point') for s in session['steps']}
            def fields(values):
                if not isinstance(values,dict):return 'Unavailable'
                run=values.get('run_id')
                point=labels.get(run,'Survey-wide' if not run else 'Point unavailable')
                return (f"Point: {point}\nType: {values.get('category','Unknown')}\nMaterial: {values.get('material','Unknown')}\n"
                        f"Operator: {values.get('author') or 'Not supplied'}\nDescription: {values.get('description','')}")
            lines=[f"Observation {observation_id}\nOriginally recorded: {row.get('recorded_utc','Unknown')} (UTC)"]
            if not history:lines.append('No edits recorded.')
            for number,entry in enumerate(history,1):
                if not isinstance(entry,dict):
                    lines.append(f'Edit {number}: invalid history entry');continue
                lines.append(f"Edit {number} · {entry.get('timestamp','Unknown')} (UTC)\nBefore:\n{fields(entry.get('previous'))}\nAfter:\n{fields(entry.get('updated'))}")
            viewer=QDialog(self);viewer.setWindowTitle('Observation edit history');viewer.resize(700,520)
            layout=QVBoxLayout(viewer)
            self.history_view=QPlainTextEdit();self.history_view.setReadOnly(True);self.history_view.setPlainText('\n\n'.join(lines))
            layout.addWidget(self.history_view)
            close=QPushButton('Close');close.clicked.connect(viewer.accept);layout.addWidget(close)
            viewer.exec()
        except (OSError,ValueError,KeyError) as exc:self.status.setText(str(exc))

    def start_edit(self):
        index=self.table.currentRow()
        if not self.editable or index<0:return
        item=self.table.item(index,0)
        row=self.rows_by_id.get(item.data(Qt.ItemDataRole.UserRole)) if item else None
        if not row:return
        point_index=self.point.findData(row.get('run_id'))
        category_index=self.category.findText(row.get('category',''))
        material_index=self.material.findText(row.get('material',''))
        revision=row.get('revision',0)
        if min(point_index,category_index,material_index)<0 or type(revision) is not int or revision<0:
            self.status.setText('This observation has unsupported values. Review its survey journal before editing.')
            return
        self.editing_id=row['id'];self.editing_revision=revision
        self.point.setCurrentIndex(point_index);self.category.setCurrentIndex(category_index);self.material.setCurrentIndex(material_index)
        self.author.setText(row.get('author',''));self.description.setPlainText(row.get('description',''))
        self.add_button.setText('Save changes');self.cancel_button.show();self.table.setEnabled(False)
        self.selection_changed()
        self.status.setText('Editing the selected observation. Save changes or cancel edit.')

    def cancel_edit(self):
        self.editing_id=None;self.editing_revision=None
        self.description.clear();self.add_button.setText('Add observation');self.cancel_button.hide();self.table.setEnabled(True)
        self.refresh()
        self.status.setText('Edit cancelled. The saved observation is unchanged.')

    def add(self):
        try:
            values=dict(run_id=self.point.currentData(),category=self.category.currentText(),material=self.material.currentText(),
                        description=self.description.toPlainText(),author=self.author.text())
            editing=self.editing_id is not None
            if editing:
                update_observation(self.config,self.path,self.editing_id,values,expected_revision=self.editing_revision)
                self.cancel_edit()
            else:
                add_observation(self.config,self.path,values)
            self.description.clear();self.refresh();self.status.setText('Observation changes saved.' if editing else 'Operator observation saved.')
        except (OSError,ValueError,KeyError) as exc:self.status.setText(str(exc))

    def remove(self):
        index=self.table.currentRow()
        if index<0:return
        if QMessageBox.question(self,'Remove observation','Remove this observation from the active survey report? Its removal remains recorded in the survey.') != QMessageBox.StandardButton.Yes:return
        try:
            observation_id=self.table.item(index,0).data(Qt.ItemDataRole.UserRole)
            row=self.rows_by_id.get(observation_id,{})
            remove_observation(self.config,self.path,observation_id,expected_revision=row.get('revision',0))
            self.refresh();self.status.setText('Observation removed; its removal is retained in survey history.')
        except (OSError,ValueError,KeyError) as exc:
            self.refresh();self.status.setText(str(exc))
