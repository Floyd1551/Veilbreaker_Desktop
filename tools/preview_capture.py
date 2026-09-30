"""Render a saved SDR run in the actual desktop UI without acquiring new data."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from veilbreaker import core
from veilbreaker.gui import MainWindow, STYLE

app = QApplication([])
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
if os.name == "nt":
    for name in ("segoeui.ttf", "segoeuib.ttf"):
        QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name))
window = MainWindow()
errors = []
window.error = errors.append
window.show()
index = next(i for i, row in enumerate(window.history_rows)
             if row.get("artifact_dir") and (Path(row["artifact_dir"]) / "sdr_summaries.json").exists())
window.history.selectRow(index)
window.open_history()
window.tabs.setCurrentIndex(6)
QTest.qWait(200)
assert window.spectrum.points and not errors, errors
output = Path("test-artifacts/hackrf")
output.mkdir(parents=True, exist_ok=True)
assert window.grab().save(str(output / "spectrum.png"))
payload = window.payload
print(json.dumps({"run_id": payload["run_id"], "evidence_zip": payload["evidence_zip"], "points": len(window.spectrum.points), "sweeps": payload["sweeps"], "notes": payload["notes"]}, indent=2))
window.close()
