"""User-visible workflow checks for responsive controls and connection settings."""
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from veilbreaker import core
from veilbreaker.gui import MainWindow, STYLE


class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = MainWindow(core.AppConfig(data_dir=self.temp.name))
        self.errors = []
        self.window.error = self.errors.append

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.temp.cleanup()

    def test_narrow_pages_do_not_clip_controls_and_navigation_stays_available(self):
        self.window.resize(760, 640)
        self.window.show()
        self.window.show_demo()
        for index in range(self.window.nav.count()):
            self.window.compact_navigation.setCurrentIndex(index)
            QTest.qWait(30)
            page = self.window.pages.widget(index)
            self.assertEqual(self.window.nav.currentRow(), index)
            self.assertEqual(page.horizontalScrollBar().maximum(), 0, f"Page {index} clips horizontally")
        self.assertFalse(self.window.sidebar.isVisible())
        self.assertTrue(self.window.compact_navigation.isVisible())
        self.window.resize(1280, 900)
        QTest.qWait(30)
        self.assertTrue(self.window.sidebar.isVisible())
        self.assertFalse(self.window.compact_navigation.isVisible())

    def test_configuration_and_toolbox_are_separate_destinations(self):
        names = [self.window.nav.item(i).text() for i in range(self.window.nav.count())]
        self.assertEqual(names, ['Overview', 'Investigate', 'Evidence', 'Surveys',
                                 'Configuration', 'Tools', 'Settings'])
        self.assertEqual(self.window.pages.count(), len(names))
        self.assertEqual(self.window.nav.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def test_brand_navigation_and_collector_icons_render(self):
        self.assertFalse(self.window.brand_mark.pixmap().isNull())
        self.assertFalse(self.window.overview_mark.pixmap().isNull())
        for index in range(self.window.nav.count()):
            icon = self.window.nav.item(index).icon()
            self.assertFalse(icon.isNull(), self.window.nav.item(index).text())
            self.assertFalse(icon.pixmap(24, 24).isNull())
            self.assertFalse(self.window.compact_navigation.itemIcon(index).isNull())
        for key, check in self.window.flags.items():
            marks = [child for child in check.parentWidget().findChildren(type(self.window.brand_mark))
                     if child.objectName() == 'collectorIcon']
            self.assertEqual(len(marks), 1, key)
            self.assertFalse(marks[0].pixmap().isNull(), key)
        for action in (self.window.run_button, self.window.history_open, self.window.capture_button):
            self.assertFalse(action.icon().isNull())

    def test_collector_choices_explain_what_each_collects(self):
        for key in ('active', 'cellular', 'starlink', 'sdr', 'throughput'):
            check = self.window.flags[key]
            self.assertEqual(check.parentWidget().objectName(), 'collectorCard')
            self.assertTrue(check.parentWidget().findChildren(type(self.window.run_plan)))

    def test_readiness_badges_distinguish_missing_and_untested(self):
        self.assertEqual(self.window.collector_badges['sdr'].text(), 'Not checked')
        self.window.flags['sdr'].setChecked(True)
        self.window.show_readiness_badges({'selected': ['sdr'], 'rows': [
            {'item': 'hackrf_info', 'state': 'Available'},
            {'item': 'hackrf_sweep', 'state': 'Missing'},
            {'item': 'HackRF connection', 'state': 'Untested'},
        ]})
        self.assertEqual(self.window.collector_badges['sdr'].text(), 'Prerequisite missing')
        self.assertEqual(self.window.collector_badges['cellular'].text(), 'Not checked')
        self.window.flags['sdr'].setChecked(False)
        self.assertEqual(self.window.collector_badges['sdr'].text(), 'Not checked')

    def test_available_prerequisites_do_not_claim_hardware_connected(self):
        self.window.show_readiness_badges({'selected': ['cellular'], 'rows': [
            {'item': 'Modem serial support', 'state': 'Available'},
            {'item': 'Modem configuration', 'state': 'Configured'},
            {'item': 'Modem connection', 'state': 'Untested'},
        ]})
        self.assertEqual(self.window.collector_badges['cellular'].text(), 'Connection untested')

    def test_empty_readiness_rows_do_not_claim_prerequisites_checked(self):
        self.window.show_readiness_badges({'selected': ['throughput'], 'rows': []})
        self.assertEqual(self.window.collector_badges['throughput'].text(), 'Not checked')

    def test_evidence_utilities_are_on_evidence_page(self):
        self.assertIsNotNone(self.window.verify_evidence_button)
        self.assertIsNotNone(self.window.recover_button)
        evidence_page = self.window.pages.widget(2).widget()
        self.assertTrue(evidence_page.isAncestorOf(self.window.verify_evidence_button))
        self.assertTrue(evidence_page.isAncestorOf(self.window.recover_button))

    def test_connection_controls_live_in_configuration_and_advanced_editor_in_settings(self):
        configuration_page = self.window.pages.widget(4).widget()
        settings_page = self.window.pages.widget(6).widget()
        self.assertTrue(configuration_page.isAncestorOf(self.window.settings_tabs))
        self.assertTrue(settings_page.isAncestorOf(self.window.config_editor))
        self.assertFalse(settings_page.isAncestorOf(self.window.settings_tabs))

    def test_long_configuration_path_does_not_widen_settings_page(self):
        self.window.settings_location.setText('Configuration: C:\\' + 'longpath' * 35 + '\\config.json')
        self.window.resize(760,640)
        self.window.show()
        self.window.compact_navigation.setCurrentIndex(6)
        QTest.qWait(50)
        self.assertEqual(self.window.pages.widget(6).horizontalScrollBar().maximum(),0)

    def test_metric_filter_includes_zero_and_source_without_changing_evidence(self):
        from veilbreaker.jobs import demo_payload
        payload = demo_payload()
        payload["metrics"] = {"latency_ms": 0, "rsrp": -110, "carrier": "Example"}
        payload["collection"] = {"status": "complete", "collectors": [], "metric_sources": {"rsrp": ["cellular"]}}
        self.window.display_payload(payload)
        self.window.metric_search.setText("CELLULAR")
        visible = [self.window.metrics.item(row, 0).text() for row in range(3) if not self.window.metrics.isRowHidden(row)]
        self.assertEqual(visible, ["rsrp"])
        self.window.metric_search.setText("latency")
        self.assertEqual(self.window.metrics.item(1, 1).text(), "0")
        self.assertFalse(self.window.metrics.isRowHidden(1))
        self.window.metric_search.setText("absent")
        self.assertIn("No matching", self.window.metric_count.text())
        self.window.metric_search.clear()
        self.assertEqual(self.window.metric_count.text(), "3 of 3 measurements")
        self.assertEqual(payload["metrics"]["latency_ms"], 0)

    def test_connection_save_is_atomic_preserves_context_and_never_acquires(self):
        destination = Path(self.temp.name) / "settings.json"
        self.window.site.setText("Roof investigation")
        self.window.hardware_settings.fields["cellular.port"].setText("COM8")
        self.window.network_fields["dns_test_host"].setText("test.example")
        self.assertIn("Unsaved connection", self.window.settings_feedback.text())
        with patch("veilbreaker.core.default_config_path", return_value=destination), patch.object(self.window, "start_job") as start:
            self.window.save_network_settings()
            start.assert_not_called()
            self.assertEqual(self.window.site.text(), "Roof investigation")
            saved = destination.read_bytes()
            self.assertEqual(json.loads(saved)["cellular"]["port"], "COM8")
            self.assertEqual(json.loads(saved)["dns_test_host"], "test.example")
            self.window.hardware_settings.fields["starlink.host"].setText("https://invalid")
            self.window.network_fields["dns_test_host"].setText("another.example")
            self.window.save_network_settings()
            self.assertEqual(destination.read_bytes(), saved)
            self.assertEqual(self.window.config.dns_test_host, "test.example")
        self.assertIn("Starlink host", self.errors[-1])

    def test_advanced_save_does_not_discard_unsaved_connection_edits(self):
        self.window.hardware_settings.fields["sdr.serial"].setText("new-receiver")
        with patch.object(self.window, "persist_settings") as persist:
            self.window.save_settings()
        persist.assert_not_called()
        self.assertIn("connection edits", self.errors[-1])
        self.assertEqual(self.window.hardware_settings.fields["sdr.serial"].text(), "new-receiver")

    def test_guided_selection_explains_active_tests(self):
        self.window.flags["guided"].setChecked(True)
        self.assertIn("ping 1.1.1.1", self.window.run_plan.text())
        self.assertIn("guided follow-up", self.window.run_plan.text())
        self.window.flags["throughput"].setChecked(True)
        self.assertIn("unconfigured server", self.window.run_plan.text())

    def test_task_banner_and_cancel_follow_worker_across_pages(self):
        self.window.show()
        self.window.start_job("selftest")
        self.window.nav.setCurrentRow(0)
        self.assertTrue(self.window.task_banner.isVisible())
        self.assertFalse(self.window.site.isEnabled())
        self.assertTrue(self.window.task_cancel.isEnabled())
        self.window.task_cancel.click()
        self.window.process.waitForFinished(5000) if self.window.process else None
        self.app.processEvents()
        self.assertIsNone(self.window.process)
        self.assertFalse(self.window.task_banner.isVisible())
        self.assertTrue(self.window.site.isEnabled())

    def test_keyboard_find_and_empty_history_actions(self):
        self.assertFalse(self.window.history_open.isEnabled())
        self.assertFalse(self.window.history_compare.isEnabled())
        self.window.show()
        self.window.nav.setCurrentRow(1)
        self.window.focus_search()
        self.assertEqual(self.window.tabs.currentIndex(), 4)
        self.window.nav.setCurrentRow(0)
        self.window.focus_search()
        self.assertEqual(self.window.nav.currentRow(), 2)
        self.assertIn("No saved runs", self.window.history_empty.text())

    def test_survey_queue_actions_reflect_available_work(self):
        page = self.window.survey_page
        self.assertFalse(page.start_button.isEnabled())
        self.assertFalse(page.remove_button.isEnabled())
        self.assertFalse(page.open_session_button.isEnabled())
        self.assertFalse(page.export_button.isEnabled())
        page.add_steps()
        self.assertTrue(page.start_button.isEnabled())
        page.queue.selectRow(0)
        self.assertTrue(page.remove_button.isEnabled())
        page.remove_step()
        self.assertFalse(page.start_button.isEnabled())
        self.assertFalse(page.remove_button.isEnabled())
