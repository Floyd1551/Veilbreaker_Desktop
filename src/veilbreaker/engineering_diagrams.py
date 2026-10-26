"""Schematic diagrams for operator-entered fiber and PoE planning results."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


def diagram_data(snapshot):
    if not snapshot or snapshot['tool_id'] not in ('fiber_budget', 'poe_budget'):
        return None
    values, outputs = snapshot['inputs'], snapshot['outputs']
    if snapshot['tool_id'] == 'fiber_budget':
        stages = (f"TX minimum\n{values['tx_min']:g} dBm",
                  f"Fiber + joints\n{outputs['Estimated path loss (dB)']:g} dB loss",
                  f"RX estimate\n{outputs['Estimated receive power (dBm)']:g} dBm")
        caption = f"Margin after {values['reserve']:g} dB reserve: {outputs['Margin after reserve (dB)']:g} dB"
        shortfall = outputs['Margin after reserve (dB)'] < 0
    else:
        stages = (f"PSE supply\n{values['supply']:g} W",
                  f"Committed + reserve\n{values['allocated'] + values['reserve']:g} W",
                  f"New device demand\n{values['target']:g} W")
        caption = f"Headroom after target: {outputs['Headroom after target (W)']:g} W"
        shortfall = outputs['Headroom after target (W)'] < 0
    return dict(kind=snapshot['tool_id'], stages=stages, caption=caption, shortfall=shortfall)


def stage_rects(width):
    """Lay out the three flow stages without requiring horizontal scrolling."""
    if width < 340:
        return tuple(QRectF(12, 42 + index * 37, max(0, width - 24), 34) for index in range(3))
    gap = 16
    box_width = (width - 32 - 2 * gap) / 3
    return tuple(QRectF(12 + index * (box_width + gap), 40, box_width, 72) for index in range(3))


class EngineeringDiagram(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.setMinimumHeight(190)
        self.setAccessibleName('Planning flow diagram. Schematic from entered assumptions, not a measurement.')

    def set_snapshot(self, snapshot):
        self.data = diagram_data(snapshot)
        self.setVisible(self.data is not None)
        if self.data:
            self.setAccessibleDescription('; '.join(self.data['stages']) + '; ' + self.data['caption'])
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#111c29'))
        painter.setPen(QColor('#cddbe9'))
        painter.drawText(QRectF(12, 3, max(0, self.width() - 24), 34),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                         'Schematic · entered specifications · not measured equipment')
        rectangles = stage_rects(self.width())
        for index, (stage, rect) in enumerate(zip(self.data['stages'], rectangles)):
            painter.setPen(QPen(QColor('#4d8993'), 1))
            painter.setBrush(QColor('#1a3241'))
            painter.drawRoundedRect(rect, 6, 6)
            painter.setPen(QColor('#e8f0f8'))
            inset = rect.adjusted(5, 1, -5, -1) if self.width() < 340 else rect.adjusted(6, 5, -6, -5)
            painter.drawText(inset, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, stage)
            if index < 2:
                painter.setPen(QPen(QColor('#55d7c0'), 2))
                next_rect = rectangles[index + 1]
                if self.width() < 340:
                    painter.drawLine(int(rect.center().x()), int(rect.bottom()),
                                     int(next_rect.center().x()), int(next_rect.top()))
                else:
                    painter.drawLine(int(rect.right() + 3), int(rect.center().y()),
                                     int(next_rect.left() - 3), int(next_rect.center().y()))
        painter.setPen(QColor('#e9b75c' if self.data['shortfall'] else '#55d7c0'))
        painter.drawText(QRectF(12, 156 if self.width() < 340 else 120, max(0, self.width() - 24), 30),
                         Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                         self.data['caption'])
