"""Interactive spectrum inspection from saved evidence, independent of hardware."""
from collections import defaultdict
from pathlib import Path
import statistics
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget, QSizePolicy
from .core import HackRFCollector
from .bandplan import default_plan, bands_at, band_description


class SpectrumView(QWidget):
    inspected = Signal(str)

    def __init__(self):
        super().__init__()
        self.points = []
        self.summary = None
        self.reference_points = []
        self.caption = "No spectrum captured. Capture a sweep or reopen a saved SDR run."
        self.bounds = (0, 1)
        self.full_bounds = (0, 1)
        self.cursor = None
        self.drag = None
        self.band_plan = default_plan()
        self.show_bands = True
        self.setMinimumSize(360, 320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Spectrum plot. Plus and minus zoom; arrows pan; Home resets.")

    def load_sweep(self, summary):
        self.points = []
        self.summary = summary
        self.reference_points = []
        self.cursor = None
        if summary:
            try:
                from .rf_workflow import read_trace
                self.points = read_trace(summary)
                self.caption = (f"{summary['label']} • {summary['min_mhz']:g}–{summary['max_mhz']:g} MHz • "
                                f"{summary['bin_width_hz'] / 1000:g} kHz bins • {len(self.points)} frequency bins")
                self.full_bounds = (float(summary['min_mhz']), float(summary['max_mhz']))
                if not self.points:
                    self.caption = "No readable samples in the saved frequency range."
            except (OSError, ValueError, KeyError) as exc:
                self.caption = f"Saved spectrum unavailable: {exc}"
        else:
            self.caption = "No spectrum in this run. Capture a sweep or reopen a saved SDR run."
        self.reset_view()

    def set_reference(self, summary):
        from .rf_workflow import read_trace
        self.reference_points = read_trace(summary) if summary else []
        self.inspected.emit("Hover to inspect before/after median power and change in relative dB")
        self.update()

    def set_band_plan(self, plan, visible=True):
        self.band_plan = plan
        self.show_bands = visible
        self.update()

    def plot_rect(self):
        return QRectF(64, 76, max(1, self.width() - 90), max(1, self.height() - 132))

    def reset_view(self):
        self.bounds = self.full_bounds
        self.cursor = None
        if self.points:
            peak = max(self.points, key=lambda p: p[2])
            self.inspected.emit(f"Peak: {peak[0]:.3f} MHz • {peak[2]:.1f} relative dB • Hover to inspect; wheel to zoom; drag to pan")
        else:
            self.inspected.emit("No samples available")
        self.update()

    def set_bounds(self, low, high):
        a, b = self.full_bounds
        span = min(b - a, high - low)
        low = max(a, min(low, b - span))
        self.bounds = (low, low + span)
        self.update()

    def zoom(self, factor, anchor=None):
        low, high = self.bounds
        center = (low + high) / 2 if anchor is None else anchor
        span = max((self.full_bounds[1] - self.full_bounds[0]) / max(1, len(self.points) / 4), (high - low) * factor)
        ratio = (center - low) / max(high - low, 1e-9)
        self.set_bounds(center - span * ratio, center + span * (1 - ratio))

    def wheelEvent(self, event):
        plot = self.plot_rect()
        if self.points and plot.contains(event.position()):
            low, high = self.bounds
            anchor = low + (event.position().x() - plot.left()) / plot.width() * (high - low)
            self.zoom(0.75 if event.angleDelta().y() > 0 else 1.333333, anchor)
            event.accept()
        else:
            event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.plot_rect().contains(event.position()):
            self.drag = (event.position().x(), self.bounds)
            self.setFocus()

    def mouseReleaseEvent(self, event):
        self.drag = None

    def mouseMoveEvent(self, event):
        plot = self.plot_rect()
        if self.drag:
            x, (low, high) = self.drag
            shift = (x - event.position().x()) / plot.width() * (high - low)
            self.set_bounds(low + shift, high + shift)
        if self.points and plot.contains(event.position()):
            low, high = self.bounds
            frequency = low + (event.position().x() - plot.left()) / plot.width() * (high - low)
            self.cursor = min(self.points, key=lambda p: abs(p[0] - frequency))
            context = (' • Expected uses: ' + ('; '.join(band_description(b) for b in bands_at(self.band_plan, self.cursor[0])) or 'No reference entry')) if self.show_bands else ''
            self.inspected.emit(f"{self.cursor[0]:.3f} MHz • Median {self.cursor[1]:.1f} dB • Maximum {self.cursor[2]:.1f} dB (relative, uncalibrated)" + context)
            if self.reference_points:
                before = min(self.reference_points, key=lambda p: abs(p[0] - self.cursor[0]))
                self.inspected.emit(f"{self.cursor[0]:.3f} MHz • Before {before[1]:.1f} dB • After {self.cursor[1]:.1f} dB • Change {self.cursor[1]-before[1]:+.1f} dB (relative)" + context)
            self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom(0.75)
        elif key == Qt.Key.Key_Minus:
            self.zoom(1.333333)
        elif key == Qt.Key.Key_Home:
            self.reset_view()
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            low, high = self.bounds
            shift = (high - low) * (0.2 if key == Qt.Key.Key_Right else -0.2)
            self.set_bounds(low + shift, high + shift)
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111b29"))
        painter.setPen(QColor("#b6c8dc"))
        painter.drawText(QRectF(16, 10, self.width() - 32, 44), Qt.TextFlag.TextWordWrap, self.caption)
        if not self.points:
            return
        plot = self.plot_rect()
        xlow, xhigh = self.bounds
        visible = [p for p in self.points if xlow <= p[0] <= xhigh]
        values = [v for p in (visible or self.points) for v in (p[1:2] if self.reference_points else p[1:])]
        values += [p[1] for p in self.reference_points if xlow <= p[0] <= xhigh]
        low, high = min(values) - 5, max(values) + 5
        def xcoord(x):
            return plot.left() + (x - xlow) / max(1e-9, xhigh - xlow) * plot.width()
        def ycoord(y):
            return plot.bottom() - (y - low) / (high - low) * plot.height()
        ticks = max(2, min(8, int(plot.width() / 110)))
        for i in range(6):
            value = low + (high - low) * i / 5
            y = ycoord(value)
            painter.setPen(QPen(QColor("#293b50"), 1))
            painter.drawLine(plot.left(), y, plot.right(), y)
            painter.setPen(QColor("#93a9c2"))
            painter.drawText(QRectF(0, y - 9, 55, 20), Qt.AlignmentFlag.AlignRight, f"{value:.0f}")
        for i in range(ticks + 1):
            frequency = xlow + (xhigh - xlow) * i / ticks
            painter.setPen(QPen(QColor("#293b50"), 1))
            painter.drawLine(xcoord(frequency), plot.top(), xcoord(frequency), plot.bottom())
            painter.setPen(QColor("#93a9c2"))
            painter.drawText(QRectF(xcoord(frequency) - 40, plot.bottom() + 7, 80, 20), Qt.AlignmentFlag.AlignCenter, f"{frequency:.2f}")
        painter.save()
        painter.setClipRect(plot)
        if self.show_bands:
            label_ends = [-1.0, -1.0, -1.0]
            for index, band in enumerate(self.band_plan['bands']):
                left, right = max(xlow, band['min_mhz']), min(xhigh, band['max_mhz'])
                if band.get('kind') == 'marker' and xlow <= band['min_mhz'] <= xhigh:
                    painter.setPen(QPen(QColor('#a9bee0'), 1, Qt.PenStyle.DotLine))
                    painter.drawLine(xcoord(left), plot.top(), xcoord(left), plot.bottom())
                    right = min(xhigh, left + (xhigh-xlow)*0.18)
                if right <= left:
                    continue
                rect = QRectF(xcoord(left), plot.top(), xcoord(right)-xcoord(left), plot.height())
                if band.get('kind') != 'marker':
                    painter.fillRect(rect, QColor(88, 130, 200, 12))
                painter.setPen(QColor('#a9bee0'))
                painter.drawLine(rect.left(), plot.top(), rect.left(), plot.bottom())
                lane = next((i for i, end in enumerate(label_ends) if rect.left() >= end+4), None)
                if rect.width() > 45 and lane is not None:
                    text = painter.fontMetrics().elidedText(band['label'], Qt.TextElideMode.ElideRight, int(rect.width())-8)
                    painter.drawText(QRectF(rect.left()+4, plot.top()+3+lane*18, rect.width()-8, 18), Qt.AlignmentFlag.AlignLeft, text)
                    label_ends[lane] = rect.right()
        series = ((1, "#5bd7bd", 1.8),) if self.reference_points else ((2, "#e9b86e", 1.4), (1, "#5bd7bd", 1.8))
        for index, color, width in series:
            path = QPainterPath()
            for i, point in enumerate(self.points):
                if i == 0:
                    path.moveTo(xcoord(point[0]), ycoord(point[index]))
                else:
                    path.lineTo(xcoord(point[0]), ycoord(point[index]))
            pen = QPen(QColor(color), width)
            if index == 2:
                pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawPath(path)
        if self.reference_points:
            path = QPainterPath()
            for i, point in enumerate(self.reference_points):
                if i == 0:
                    path.moveTo(xcoord(point[0]), ycoord(point[1]))
                else:
                    path.lineTo(xcoord(point[0]), ycoord(point[1]))
            painter.setPen(QPen(QColor("#bd9cff"), 1.8, Qt.PenStyle.DashLine))
            painter.drawPath(path)
        if self.cursor:
            painter.setPen(QPen(QColor("#ffffff"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(xcoord(self.cursor[0]), plot.top(), xcoord(self.cursor[0]), plot.bottom())
        painter.restore()
        painter.setPen(QColor("#93a9c2"))
        painter.drawText(16, 63, "Relative power (dB; uncalibrated)")
        painter.drawText(QRectF(16, self.height() - 24, self.width() - 32, 20), Qt.AlignmentFlag.AlignCenter, "Frequency (MHz)  •  Teal: after median  •  Purple: before median" if self.reference_points else "Frequency (MHz)  •  Teal: median  •  Amber dashed: maximum")
