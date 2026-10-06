import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from veilbreaker import core
from veilbreaker.gui import MainWindow
from veilbreaker.spectrum import SpectrumView
from veilbreaker.jobs import demo_payload


class SpectrumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_scenario_guidance_and_report_tab(self):
        with tempfile.TemporaryDirectory() as folder:
            window = MainWindow(core.AppConfig(data_dir=folder))
            window.scenario.setCurrentIndex(window.scenario.findData('realtime_voice'))
            self.assertEqual(window.effective_config().scenario, 'realtime_voice')
            self.assertIn('80', window.scenario_description.text())
            window.display_payload(demo_payload())
            self.assertIn('SDR report', [window.tabs.tabText(i) for i in range(window.tabs.count())])
            self.assertIn('No SDR', window.sdr_report_view.toPlainText())
            window.tabs.setCurrentIndex(8)
            self.assertTrue(all(p.isHidden() for p in window.setup_panels))
            window.close()

    def test_custom_plan_persists_and_expands(self):
        from veilbreaker.bandplan import validate_plan
        with tempfile.TemporaryDirectory() as folder:
            window = MainWindow(core.AppConfig(data_dir=folder))
            plan = validate_plan({'name': 'Site reference', 'bands': [{'min_mhz': 2400, 'max_mhz': 2500, 'label': 'Test reference'}]})
            window.apply_band_plan(plan)
            window.expand_spectrum()
            self.assertEqual(window.spectrum_dialog.findChild(SpectrumView).band_plan, plan)
            window.spectrum_dialog.close()
            window.close()
            reopened = MainWindow(core.AppConfig(data_dir=folder))
            self.assertEqual(reopened.spectrum.band_plan, plan)
            reopened.close()

    def test_report_export_and_legend_search(self):
        from PySide6.QtWidgets import QFileDialog
        with tempfile.TemporaryDirectory() as folder:
            window = MainWindow(core.AppConfig(data_dir=folder))
            window.display_payload(demo_payload())
            path = Path(folder) / 'rf.json'
            with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(path), 'JSON')):
                window.export_sdr_report('json')
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['metadata']['run_id'], 'demo')
            window.open_band_plan()
            window.band_plan_dialog.search.setText('Wi-Fi 2.4 GHz Channel 1 (')
            self.assertEqual(window.band_plan_dialog.table.rowCount(), 1)
            window.band_plan_dialog.close()
            window.close()

    def test_zoom_pan_reset_and_readout(self):
        with tempfile.TemporaryDirectory() as folder:
            csv = Path(folder) / "sweep.csv"
            csv.write_text("d,t,2400000000,2410000000,1000000,10," + ",".join(str(-60+i) for i in range(10)) + "\n")
            view = SpectrumView()
            readings = []
            view.inspected.connect(readings.append)
            view.load_sweep({"csv_path": str(csv), "label": "test", "min_mhz": 2400, "max_mhz": 2410, "bin_width_hz": 1000000})
            view.resize(800, 420)
            view.show()
            QTest.qWait(20)
            QTest.keyClick(view, Qt.Key.Key_Plus)
            self.assertLess(view.bounds[1] - view.bounds[0], 10)
            QTest.mouseMove(view, view.plot_rect().center().toPoint())
            self.assertIn("Median", readings[-1])
            QTest.keyClick(view, Qt.Key.Key_Home)
            self.assertEqual(view.bounds, (2400, 2410))
            self.assertGreater(view.plot_rect().height(), 250)
            view.close()

    def test_small_window_compacts_spectrum_and_expands(self):
        with tempfile.TemporaryDirectory() as folder:
            window = MainWindow(core.AppConfig(data_dir=folder))
            window.resize(1024, 640)
            window.show()
            window.nav.setCurrentRow(1)
            window.tabs.setCurrentIndex(6)
            QTest.qWait(20)
            self.assertTrue(all(p.isHidden() for p in window.setup_panels))
            self.assertGreaterEqual(window.spectrum.height(), 320)
            window.expand_spectrum()
            QTest.qWait(20)
            self.assertTrue(window.spectrum_dialog.isVisible())
            window.spectrum_dialog.close()
            window.tabs.setCurrentIndex(0)
            self.assertTrue(all(not p.isHidden() for p in window.setup_panels))
            window.close()

    def test_preset_button_dispatches_selected_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            window = MainWindow(core.AppConfig(data_dir=folder))
            window.rf_sweeps.setValue(7)
            window.rf_bins.setCurrentIndex(0)
            with patch.object(window, "start_job") as start:
                window.capture_preset()
            self.assertEqual(start.call_args.kwargs["capture_settings"]["sweeps"], 7)
            self.assertEqual(start.call_args.kwargs["capture_settings"]["bin_width_hz"], 100000)
            self.assertEqual(start.call_args.kwargs["options"], {"sdr": True})
            window.close()

    def test_comparison_dialog_overlays_matching_saved_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            summaries = []
            for name, power in (("before", -60), ("after", -57)):
                csv = root / f"{name}.csv"
                csv.write_text("d,t,2400000000,2404000000,1000000,4," + ",".join([str(power)]*4) + "\n")
                csv.with_suffix(".capture.json").write_text(json.dumps({"device_serial": "fixture", "returncode": 0,
                    "settings": {"bin_width_hz": 1000000, "sweeps": 1, "lna_gain_db": 16, "vga_gain_db": 20, "amp_enable": False, "antenna_power": False}}))
                summaries.append({"label": "test", "csv_path": str(csv), "min_mhz": 2400, "max_mhz": 2404, "bin_width_hz": 1000000})
            (root / "sdr_summaries.json").write_text(json.dumps([summaries[0]]))
            window = MainWindow(core.AppConfig(data_dir=folder))
            payload = demo_payload()
            payload.update(run_id="after", site_id="fixture", sweeps=[summaries[1]])
            window.display_payload(payload)
            window.history_rows = [{"run_id": "before", "site_id": "fixture", "artifact_dir": folder,
                                    "ts_utc": "2026-10-01", "metrics_json": "{}"}]
            window.compare_spectrum()
            QTest.qWait(20)
            dialog = window.comparison_dialog
            self.assertTrue(any("Median change +3.00" in label.text() for label in dialog.findChildren(QLabel)))
            self.assertEqual(len(dialog.findChild(SpectrumView).reference_points), 4)
            self.assertTrue(next(b for b in dialog.findChildren(QPushButton) if b.text() == "Save comparison…").isEnabled())
            dialog.close()
            window.close()
