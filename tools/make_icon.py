"""Render the recovered vector emblem into desktop icon formats."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import Qt

app = QApplication([])
root = Path(__file__).resolve().parents[1] / "src/veilbreaker/assets"
svg = QSvgRenderer(str(root / "app.svg"))
if not svg.isValid():
    raise RuntimeError("Invalid source SVG")
image = QImage(256, 256, QImage.Format.Format_ARGB32)
image.fill(Qt.GlobalColor.transparent)
painter = QPainter(image)
svg.render(painter)
painter.end()
for name in ("app.png", "app.ico"):
    if not image.save(str(root / name)):
        raise RuntimeError(f"Cannot write {name}")
