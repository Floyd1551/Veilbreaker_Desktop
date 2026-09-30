"""Spectrum preview from saved sweep evidence; no hardware acquisition here."""
from collections import defaultdict
from pathlib import Path
import statistics
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget
from .core import HackRFCollector


class SpectrumView(QWidget):
    def __init__(self):
        super().__init__()
        self.points = []
        self.caption = "No spectrum captured. Use Tools & readiness → Capture 2.4 GHz, or enable SDR sweep."
        self.setMinimumHeight(240)
        self.setAccessibleName("Saved spectrum: frequency versus relative power")

    def load_sweep(self, summary):
        self.points = []
        if summary:
            try:
                bins = HackRFCollector.parse_sweep_csv(Path(summary["csv_path"]))
                grouped = defaultdict(list)
                for sample in bins:
                    if summary["min_mhz"] <= sample.hz / 1e6 < summary["max_mhz"]:
                        grouped[sample.hz / 1e6].append(sample.power_db)
                self.points = [(hz, statistics.median(values), max(values)) for hz, values in sorted(grouped.items())]
                self.caption = (f"{summary['label']} • {summary['min_mhz']:g}–{summary['max_mhz']:g} MHz • "
                                f"{summary['bin_width_hz'] / 1000:g} kHz bins • median and maximum across captured sweeps")
            except (OSError, ValueError, KeyError) as exc:
                self.caption = f"Saved spectrum unavailable: {exc}"
        else:
            self.caption = "No spectrum in this run. Use Tools & readiness → Capture 2.4 GHz, or enable SDR sweep."
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111b29"))
        painter.setPen(QColor("#b6c8dc"))
        painter.drawText(QRectF(16, 10, self.width() - 32, 44), Qt.TextFlag.TextWordWrap, self.caption)
        if not self.points:
            return
        plot = QRectF(66, 72, self.width() - 90, self.height() - 128)
        xs = [p[0] for p in self.points]
        values = [v for p in self.points for v in p[1:]]
        low, high = min(values) - 5, max(values) + 5
        xlow, xhigh = min(xs), max(xs)
        def xcoord(x):
            return plot.left() + (x - xlow) / max(1, xhigh - xlow) * plot.width()
        def ycoord(y):
            return plot.bottom() - (y - low) / (high - low) * plot.height()
        for i in range(6):
            value = low + (high - low) * i / 5
            y = ycoord(value)
            painter.setPen(QPen(QColor("#293b50"), 1))
            painter.drawLine(plot.left(), y, plot.right(), y)
            painter.setPen(QColor("#93a9c2"))
            painter.drawText(QRectF(0, y - 9, 57, 20), Qt.AlignmentFlag.AlignRight, f"{value:.0f}")
            frequency = xlow + (xhigh - xlow) * i / 5
            painter.drawText(QRectF(xcoord(frequency) - 30, plot.bottom() + 7, 65, 20), Qt.AlignmentFlag.AlignCenter, f"{frequency:.1f}")
        for index, color, width in ((2, "#e9b86e", 1.2), (1, "#5bd7bd", 2.0)):
            path = QPainterPath()
            for i, point in enumerate(self.points):
                if i == 0:
                    path.moveTo(xcoord(point[0]), ycoord(point[index]))
                else:
                    path.lineTo(xcoord(point[0]), ycoord(point[index]))
            painter.setPen(QPen(QColor(color), width))
            painter.drawPath(path)
        painter.setPen(QColor("#93a9c2"))
        painter.drawText(16, 61, "Relative power (dB; uncalibrated)")
        painter.drawText(QRectF(66, self.height() - 24, self.width() - 90, 20), Qt.AlignmentFlag.AlignCenter, "Frequency (MHz)     •     Teal: median     •     Amber: maximum")
