import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from veilbreaker.toolbox_reference import REFERENCES
from veilbreaker.tool_registry import build_registry, search_registry


class OfflineReferenceTests(unittest.TestCase):
    def test_reference_tables_have_correct_values_sources_and_limitations(self):
        records = dict(REFERENCES)
        cases = {
            'RF thermal noise and receiver noise figure': ('−174', '−134', '−104', '290 K', 'keysight.com'),
            'Ethernet frame, MTU and wire time': ('1500', '1518', '1538', 'RFC 6349', 'rfc-editor.org'),
            'PoE power: source and powered device': ('15.4', '12.95', '25.5', '51', '71', 'cisco.com'),
            'Fiber optics loss and power budget': ('mated', 'splice', 'wavelength', 'margin', 'flukenetworks.com'),
        }
        for title, fragments in cases.items():
            with self.subTest(title=title):
                body = records[title]
                for fragment in fragments:
                    self.assertIn(fragment.casefold(), body.casefold())
                self.assertIn('2026-10-30', body)
                self.assertIn('limitations', body.casefold())

    def test_full_reference_text_and_table_terms_are_searchable(self):
        registry = build_registry()
        for query, expected in (
            ('equivalent noise bandwidth', 'RF thermal noise and receiver noise figure'),
            ('interframe gap', 'Ethernet frame, MTU and wire time'),
            ('powered device 25.5', 'PoE power: source and powered device'),
            ('splice optical wavelength', 'Fiber optics loss and power budget'),
        ):
            with self.subTest(query=query):
                self.assertIn(expected, [record.title for record in search_registry(registry, query)])

    def test_new_reference_categories_and_all_references_filter(self):
        registry = build_registry()
        expected = {
            'RF thermal noise and receiver noise figure': 'RF',
            'Ethernet frame, MTU and wire time': 'Networking',
            'PoE power: source and powered device': 'Fiber & Power',
            'Fiber optics loss and power budget': 'Fiber & Power',
        }
        for title, category in expected.items():
            with self.subTest(title=title):
                record = next(r for r in registry if r.title == title)
                self.assertEqual(record.category, category)
                self.assertIn(record, search_registry(registry, category='References'))

    def test_search_result_opens_readable_reference_tab(self):
        from PySide6.QtWidgets import QApplication
        from veilbreaker.toolbox_ui import ToolboxPage
        app = QApplication.instance() or QApplication([])
        page = ToolboxPage()
        try:
            page.resize(760, 650)
            page.global_search.setText('powered device 25.5')
            result = next(card for card in page.result_cards if card.record.title == 'PoE power: source and powered device')
            page.open_record_tab(result.record.record_id)
            page.show()
            app.processEvents()
            body = page.workspace_tabs.currentWidget().body.toPlainText()
            self.assertIn('25.5 W', body)
            self.assertIn('Limitations:', body)
            self.assertIn('2026-10-30', body)
            self.assertLessEqual(page.width(), 760)
        finally:
            page.close()
