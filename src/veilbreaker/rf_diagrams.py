"""Schematic native vector diagrams derived from the same terrain geometry as tools."""
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget
from .terrain_profile import assess_profile


def diagram_data(snapshot):
    if not snapshot or snapshot['tool_id'] not in ('fresnel', 'curvature'):
        return None
    values = snapshot['inputs']
    length, selected = values['distance'] * 1000, values['position'] * 1000
    xs = sorted(set([length * i / 80 for i in range(81)] + [selected]))
    profile = assess_profile(xs, [0] * len(xs), 0, 0, values.get('frequency'))
    if snapshot['tool_id'] == 'fresnel':
        primary = profile['fresnel_radius_m']
        secondary = [.6 * y for y in primary]
    else:
        primary = profile['terrain_effective_m']
        secondary = assess_profile(xs, [0] * len(xs), 0, 0, earth_factor=4/3)['terrain_effective_m']
    return dict(kind=snapshot['tool_id'], x=xs, primary=primary, secondary=secondary,
                selected=selected, caption=' · '.join(f'{k}: {v:.4g}' for k, v in snapshot['outputs'].items()),
                warning=snapshot['limitations'].startswith('WARNING:'))


class RFDiagram(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.setMinimumHeight(220)
        self.setAccessibleName('RF path diagram. Schematic with vertical exaggeration; not surveyed terrain.')

    def set_snapshot(self, snapshot):
        self.data = diagram_data(snapshot)
        self.setVisible(self.data is not None)
        if self.data:
            self.setAccessibleDescription(self.data['caption'])
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return
        d = self.data
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#111c29'))
        painter.setPen(QColor('#cddbe9'))
        painter.drawText(12, 20, 'Schematic · vertical scale exaggerated · no measured terrain')
        left, right = 30, max(31, self.width() - 30)
        top, bottom = 55, self.height() - 60
        mid = (top + bottom) / 2 if d['kind'] == 'fresnel' else bottom
        scale = max(d['primary']) or 1
        amplitude = (bottom - top) / 2 if d['kind'] == 'fresnel' else bottom - top
        def point(x, y):
            return QPointF(left + (right - left) * x / d['x'][-1], mid - amplitude * y / scale)
        painter.setPen(QPen(QColor('#a5b6c8'), 1, Qt.PenStyle.DashLine))
        painter.drawLine(point(0, 0), point(d['x'][-1], 0))
        for series, color in [(d['primary'], '#55d7c0'), (d['secondary'], '#e9b75c')]:
            painter.setPen(QPen(QColor(color), 2))
            for sign in ([1, -1] if d['kind'] == 'fresnel' else [1]):
                path = QPainterPath(point(d['x'][0], series[0] * sign))
                for x, y in zip(d['x'][1:], series[1:]):
                    path.lineTo(point(x, y * sign))
                painter.drawPath(path)
        selected = d['x'].index(d['selected'])
        painter.setPen(QPen(QColor('#f4f8ff'), 1))
        painter.drawLine(point(d['selected'], 0), point(d['selected'], d['primary'][selected]))
        annotation_x = max(12, min(int(point(d['selected'], 0).x()) + 8, self.width() - 180))
        painter.drawText(annotation_x, int(mid - amplitude * d['primary'][selected] / scale / 2), f"{d['primary'][selected]:.4g} m")
        painter.drawText(left, int(mid) - 6, 'A')
        painter.drawText(right - 10, int(mid) - 6, 'B')
        painter.drawText(int(point(d['selected'], 0).x()) - 5, int(mid) + 16, '↑')
        painter.drawText(12, self.height() - 36, 'Teal: first zone · amber: 60% radius' if d['kind'] == 'fresnel' else 'Teal: geometric bulge · amber: k = 4/3 bulge')
        painter.drawText(12, self.height() - 16, f"Path: {d['x'][-1] / 1000:g} km · selected point: {d['selected'] / 1000:g} km")
        if d['warning']:
            painter.setPen(QColor('#ffb35c'))
            painter.drawText(12, 40, 'Approximation warning: do not use for clearance decisions')
