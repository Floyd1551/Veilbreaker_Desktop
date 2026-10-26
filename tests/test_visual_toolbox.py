import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from veilbreaker.rf_tools import calculate
from veilbreaker.rf_diagrams import diagram_data
from veilbreaker.network_tools import inspect_subnet


class VisualToolboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_diagram_geometry_and_selected_values(self):
        for tool in ('fresnel', 'curvature'):
            inputs = dict(distance=10, position=2)
            if tool == 'fresnel':
                inputs['frequency'] = 2400
            result = calculate(tool, inputs)
            data = diagram_data(result)
            self.assertEqual(data['x'][0], 0)
            self.assertEqual(data['x'][-1], 10000)
            self.assertEqual(data['primary'][0], 0)
            self.assertEqual(data['primary'][-1], 0)
            i = data['x'].index(2000)
            name = 'First Fresnel radius (m)' if tool == 'fresnel' else 'Geometric Earth bulge (m)'
            self.assertAlmostEqual(data['primary'][i], result['outputs'][name])
            ratio = .6 if tool == 'fresnel' else .75
            self.assertAlmostEqual(data['secondary'][i], data['primary'][i] * ratio)

    def test_subnets_and_edge_semantics(self):
        result = inspect_subnet('192.168.10.55/24')
        self.assertEqual(result['Network'], '192.168.10.0/24')
        self.assertEqual(result['Address count'], '256')
        self.assertEqual(result['Host range'], '192.168.10.1 – 192.168.10.254')
        self.assertEqual(inspect_subnet('192.0.2.0/31')['Usable address count'], '2')
        self.assertEqual(inspect_subnet('192.0.2.1/32')['Usable address count'], '1')
        self.assertEqual(inspect_subnet('2001:db8::1234/64')['Address count'], '18446744073709551616')
        self.assertEqual(inspect_subnet('::/0')['Address count'], str(2**128))
        self.assertNotIn('Broadcast', inspect_subnet('::1/128'))
        for invalid in ('bad', '10.0.0.1', '1.2.3.4/33', 'fe80::1%eth0/64'):
            with self.assertRaises(ValueError):
                inspect_subnet(invalid)

    def test_embedded_diagram_invalidation_and_reference_search(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page = ToolboxPage()
        panel = page.calculators
        panel.selector.setCurrentIndex(panel.selector.findData('fresnel'))
        panel.run_calculation()
        self.assertIsNotNone(panel.diagram.data)
        panel.inputs['frequency'].setText('')
        self.assertIsNone(panel.diagram.data)
        page.reference_search.setText('SINR')
        self.assertGreater(page.reference_list.count(), 0)
        page.reference_search.setText('no-matching-reference')
        self.assertEqual(page.reference_list.count(), 0)
        self.assertEqual(page.reference_body.toPlainText(), '')
        page.close()

    def test_escape_does_not_hide_embedded_calculators(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page = ToolboxPage()
        page.show()
        self.app.processEvents()
        QTest.keyClick(page.calculators.inputs['power'], Qt.Key.Key_Escape)
        self.assertTrue(page.calculators.isVisible())
        page.close()

    def test_global_search_category_and_empty_state(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page = ToolboxPage()
        self.assertEqual(page.result_count.text(), '27 results')
        page.global_search.setText('RSRP SINR')
        self.assertEqual(len(page.result_cards), 1)
        self.assertEqual(page.result_cards[0].record.kind, 'reference')
        page.global_search.setText('')
        page.category_filter.setCurrentText('Networking')
        self.assertTrue(page.result_cards)
        self.assertTrue(all(card.record.category == 'Networking' for card in page.result_cards))
        page.global_search.setText('nothing-can-match-this')
        self.assertEqual(page.result_cards, [])
        self.assertTrue(page.empty_state.isVisibleTo(page))
        page.close()

    def test_search_result_routes_to_existing_hosts(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page = ToolboxPage()
        page.activate_record('calculator:fspl')
        self.assertEqual(page.tabs.currentIndex(), 0)
        self.assertEqual(page.calculators.selector.currentData(), 'fspl')
        page.activate_record('calculator:fiber_budget')
        self.assertEqual(page.calculators.selector.currentData(), 'fiber_budget')
        page.calculators.run_calculation()
        self.assertIsNotNone(page.calculators.snapshot)
        self.assertEqual(page.calculators.snapshot['kind'], 'calculated estimate')
        page.activate_record('inspector:subnet')
        self.assertEqual(page.tabs.currentIndex(), 1)
        target = next(record for record in page.records if record.kind == 'reference')
        page.activate_record(target.record_id)
        self.assertEqual(page.tabs.currentIndex(), 4)
        self.assertEqual(page.reference_list.currentText(), target.title)
        page.activate_record('planner:wifi_channels')
        self.assertEqual(page.tabs.currentWidget(), page.wifi_planner)
        page.wifi_planner.band.setCurrentText('6 GHz')
        self.assertEqual(page.wifi_planner.first.itemData(0), 1)
        self.assertEqual(page.wifi_planner.second.itemData(1), 5)
        self.assertIn('5955 MHz', page.wifi_planner.result.text())
        page.activate_record('inspector:cell_channel')
        self.assertEqual(page.tabs.currentWidget(), page.cell_channel)
        page.cell_channel.radio.setCurrentText('NR')
        page.cell_channel.channel.setText('620000')
        page.cell_channel.inspect()
        self.assertIn('3300 MHz', page.cell_channel.result.toPlainText())
        page.cell_channel.frequency.setText('3300')
        page.cell_channel.reverse_lookup()
        self.assertEqual(page.cell_channel.channel.text(), '620000')
        page.cell_channel.channel.setText('1.5')
        page.cell_channel.inspect()
        self.assertIn('whole channel number', page.cell_channel.result.toPlainText())
        page.close()

    def test_wifi_planner_has_no_horizontal_scroll_at_field_width(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page = ToolboxPage()
        page.resize(760, 650)
        page.tabs.setCurrentWidget(page.wifi_planner)
        page.show()
        self.app.processEvents()
        self.assertLessEqual(page.wifi_planner.sizeHint().width(), page.width())
        page.close()

    def test_cell_channel_inspector_fits_field_width(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page = ToolboxPage()
        page.resize(760, 650)
        page.tabs.setCurrentWidget(page.cell_channel)
        page.show()
        self.app.processEvents()
        self.assertLessEqual(page.cell_channel.sizeHint().width(), page.width())
        page.close()

    def test_result_cards_wrap_and_keyboard_activation(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page = ToolboxPage()
        page.resize(900, 640)
        page.show()
        self.app.processEvents()
        self.assertEqual(page.discovery.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        first_row_y = page.result_cards[0].geometry().y()
        self.assertEqual(page.result_cards[2].geometry().y(), first_row_y)
        self.assertGreater(page.result_cards[3].geometry().y(), first_row_y)
        self.assertTrue(all(card.geometry().right() <= page.discovery.viewport().width()
                            for card in page.result_cards[:4]))
        page.global_search.setText('free path')
        card = page.result_cards[0]
        card.setFocus()
        QTest.keyClick(card, Qt.Key.Key_Return)
        self.assertEqual(page.calculators.selector.currentData(), 'fspl')
        page.close()
