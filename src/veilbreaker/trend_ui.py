"""Native survey trend view with a table as the accessible source of values."""
import json
from pathlib import Path
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QComboBox, QScrollArea, QHeaderView, QFileDialog
from .survey import list_sessions, read_session
from .survey_compare import load_settings_snapshot
from .survey_trends import build_trend, finite_number, trend_csv
from .recovery import atomic_json


class TrendPlot(QWidget):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.metric_name = ""
        self.setMinimumHeight(250)
        self.setAccessibleName("Comparable observations by visit; exact values and exclusions are in the table")

    def set_result(self, result):
        self.rows = result.get("rows", [])
        self.metric_name = result.get("metric", "")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111d2b"))
        painter.setPen(QColor("#aac0d7"))
        painter.drawText(12, 22, self.metric_name + " • comparable observations")
        values = [r["value"] for r in self.rows if r["comparable"]]
        if not values:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No comparable observations to plot")
            return
        low, high = min(values), max(values)
        margin = (high-low)*0.12 if high != low else max(1, abs(low)*0.05)
        low, high = low-margin, high+margin
        area = QRectF(74, 38, max(1, self.width()-96), max(1, self.height()-84))
        for i in range(5):
            y = area.bottom()-area.height()*i/4
            painter.setPen(QColor("#293e52"))
            painter.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            painter.setPen(QColor("#aac0d7"))
            painter.drawText(QRectF(0,y-10,68,20), Qt.AlignmentFlag.AlignRight, f"{low+(high-low)*i/4:.3g}")
        previous = None
        for i, row in enumerate(self.rows):
            x = area.left()+area.width()*i/max(1,len(self.rows)-1)
            if not row["comparable"]:
                previous = None
                painter.setPen(QColor("#dbb46d"))
                painter.drawText(QPointF(x-3, area.bottom()+17), "×")
                continue
            point = QPointF(x, area.bottom()-(row["value"]-low)/(high-low)*area.height())
            painter.setPen(QPen(QColor("#58d9be"),2))
            if previous is not None:
                painter.drawLine(previous, point)
            painter.setBrush(QColor("#58d9be"))
            painter.drawEllipse(point, 4, 4)
            previous = point
        painter.setPen(QColor("#aac0d7"))
        painter.drawText(74, self.height()-8, "Visits oldest → newest (equal spacing); × excluded; UTC dates below")


class TrendDialog(QDialog):
    def __init__(self, window, baseline_path):
        super().__init__(window)
        from .gui import label, button, table, fill
        self.fill = fill
        self.setWindowTitle("Survey trends")
        bounds = window.screen().availableGeometry()
        self.resize(min(1180,bounds.width()-40), min(850,bounds.height()-80))
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        layout = QVBoxLayout(content)
        self.baseline = read_session(window.config, baseline_path)
        self.settings = load_settings_snapshot(baseline_path)
        self.visits = [(s,load_settings_snapshot(p)) for p,s in list_sessions(window.config) if s["site_id"] == self.baseline["site_id"]]
        layout.addWidget(label("Survey trends", "title"))
        layout.addWidget(label(f"Site: {self.baseline['site_id']} • Baseline: {self.baseline['name']} • {self.baseline['created_utc']}", "muted"))
        self.point = QComboBox()
        self.point.setAccessibleName("Trend point")
        self.point.addItems(list(dict.fromkeys(s["label"] for s in self.baseline["steps"])))
        self.metric_selector = QComboBox()
        self.metric_selector.setAccessibleName("Trend metric")
        for widget in (self.point,self.metric_selector):
            widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            widget.setMinimumContentsLength(18)
            layout.addWidget(widget)
        self.summary = label("", "muted")
        layout.addWidget(self.summary)
        self.plot = TrendPlot()
        layout.addWidget(self.plot)
        self.table = table(["UTC", "Visit", "Value", "Change", "Collection", "Notes"])
        self.table.setMinimumHeight(220)
        layout.addWidget(self.table)
        layout.addWidget(label("Only complete, compatible observations contribute to the plot and statistics. Changes are current minus baseline, not improvement scores. Matching settings cannot verify identical hardware, antennas or conditions. Use spectrum comparison for RF evidence.", "muted"))
        self.export_json = button("Export trend JSON…", lambda: self.export("json"))
        self.export_csv = button("Export trend CSV…", lambda: self.export("csv"))
        layout.addWidget(self.export_json)
        layout.addWidget(self.export_csv)
        self.result = {}
        self.point.currentIndexChanged.connect(self.select_point)
        self.metric_selector.currentIndexChanged.connect(self.refresh)
        self.select_point()

    def select_point(self):
        self.metric_selector.blockSignals(True)
        previous = self.metric_selector.currentText()
        self.metric_selector.clear()
        steps = [s for s in self.baseline["steps"] if s["label"] == self.point.currentText()]
        if len(steps) == 1:
            self.metric_selector.addItems(sorted(k for k,v in steps[0].get("metrics", {}).items() if finite_number(v)))
        index = self.metric_selector.findText(previous)
        if index >= 0:
            self.metric_selector.setCurrentIndex(index)
        self.metric_selector.blockSignals(False)
        self.refresh()

    def refresh(self):
        self.result = {}
        self.table.setRowCount(0)
        self.plot.set_result({})
        for control in (self.export_json,self.export_csv):
            control.setEnabled(False)
        if not self.metric_selector.currentText():
            self.summary.setText("Choose a unique point with numeric measurements in the baseline visit.")
            return
        try:
            self.result = build_trend(self.baseline,self.settings,self.visits,self.point.currentText(),self.metric_selector.currentText())
            result = self.result
            display = lambda v: "—" if v is None else f"{v:.6g}"
            self.fill(self.table,[[r["created_utc"],r["name"],display(r["value"]),display(r["delta"]),r["collection"],r["notes"]] for r in result["rows"]])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            for i,width in enumerate((190,200,95,95,100,320)):
                self.table.setColumnWidth(i,width)
            stats = result["summary"]
            self.summary.setText(f"{stats['comparable']} comparable / {stats['visits']} visits • {stats['excluded']} excluded • Min {display(stats['minimum'])} • Median {display(stats['median'])} • Max {display(stats['maximum'])}")
            self.plot.set_result(result)
            for control in (self.export_json,self.export_csv):
                control.setEnabled(True)
        except (ValueError, KeyError) as exc:
            self.summary.setText(str(exc))

    def export(self, kind):
        if not self.result:
            return
        target,_ = QFileDialog.getSaveFileName(self,"Export survey trend",f"survey-trend.{kind}",f"{kind.upper()} (*.{kind})")
        if target:
            try:
                if kind == "json":
                    atomic_json(Path(target),self.result)
                else:
                    Path(target).write_text(trend_csv(self.result),encoding="utf-8-sig")
                self.summary.setText(f"Trend exported to {target}")
            except OSError as exc:
                self.summary.setText(f"Export failed: {exc}")
