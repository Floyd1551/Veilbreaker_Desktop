import os
import json
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QCheckBox, QPushButton, QTableWidget
from veilbreaker import core
from veilbreaker.gui import MainWindow
from veilbreaker.case_ui import show_cases


class CaseWorkflowTests(unittest.TestCase):
    def test_confirmation_and_withdrawal_preserve_original_run(self):
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            store = core.VeilbreakerStore(cfg.db_path)
            store.db.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("source", "2026-10-02", "Site", "field_validation", '{"latency_ms": 15}', '{}', '', 'Original note'))
            store.db.commit()
            original = dict(store.get_run("source"))
            with self.assertRaises(ValueError):
                store.add_case("source", " ")
            store.close()
            window = MainWindow(cfg)
            window.history.selectRow(0)
            errors = []
            window.error = errors.append
            def inspect(dialog):
                save = next(b for b in dialog.findChildren(QPushButton) if b.text() == "Save confirmed case")
                self.assertFalse(save.isEnabled())
                next(e for e in dialog.findChildren(QLineEdit) if e.accessibleName() == "Confirmed cause").setText("Damaged antenna cable")
                next(e for e in dialog.findChildren(QPlainTextEdit) if not e.isReadOnly()).setPlainText("Replaced cable and repeated measurements")
                dialog.findChild(QCheckBox).setChecked(True)
                self.assertTrue(save.isEnabled())
                save.click()
                table = dialog.findChild(QTableWidget)
                self.assertEqual(table.rowCount(), 1)
                self.assertEqual(table.item(0,3).text(), "Confirmed")
                self.assertFalse(save.isEnabled())
                table.selectRow(0)
                next(b for b in dialog.findChildren(QPushButton) if b.text().startswith("Withdraw")).click()
                self.assertEqual(table.item(0,3).text(), "Withdrawn")
                table.selectRow(0)
                destination = Path(folder) / "case-export.json"
                with patch("veilbreaker.case_ui.QFileDialog.getSaveFileName", return_value=(str(destination), "")):
                    next(b for b in dialog.findChildren(QPushButton) if b.text().startswith("Export selected case")).click()
                record = json.loads(destination.read_text(encoding="utf-8"))
                self.assertEqual([e["action"] for e in record["events"]], ["confirmed", "withdrawn"])
                self.assertEqual(record["source"]["run_id"], "source")
                search = next(e for e in dialog.findChildren(QLineEdit) if e.accessibleName() == "Search cases")
                search.setText("not present")
                self.assertEqual(table.rowCount(), 0)
                search.clear()
                self.assertEqual(table.rowCount(), 1)
                return 0
            try:
                with patch("veilbreaker.case_ui.QDialog.exec", inspect):
                    next(b for b in window.findChildren(QPushButton) if b.text() == "Confirmed cases…").click()
                self.assertEqual(errors, [])
                store = core.VeilbreakerStore(cfg.db_path)
                try:
                    self.assertEqual(dict(store.get_run("source")), original)
                    self.assertEqual(store.list_cases()[0]["confirmed"], 0)
                    self.assertEqual(store.match_cases({"latency_ms":15}), [])
                finally:
                    store.close()
            finally:
                window.close()
