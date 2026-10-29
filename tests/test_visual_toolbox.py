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
        self.assertEqual(page.result_count.text(), '32 results')
        page.global_search.setText('RSRP SINR')
        self.assertEqual({card.record.kind for card in page.result_cards}, {'reference', 'inspector'})
        page.global_search.setText('')
        page.category_filter.setCurrentText('Networking')
        self.assertTrue(page.result_cards)
        self.assertTrue(all(card.record.category == 'Networking' for card in page.result_cards))
        page.global_search.setText('nothing-can-match-this')
        self.assertEqual(page.result_cards, [])
        self.assertTrue(page.empty_state.isVisibleTo(page))
        page.close()

    def test_rf_calculators_search_open_and_fit_field_width(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page=ToolboxPage()
        try:
            page.resize(760,650)
            page.global_search.setText('polarization mismatch')
            self.assertIn('calculator:polarization',[card.record.record_id for card in page.result_cards])
            page.open_record_tab('calculator:polarization')
            panel=page.workspace_tabs.currentWidget()
            panel.inputs['angle'].setText('45')
            panel.run_calculation()
            self.assertIn('50',panel.result.toPlainText())
            self.assertIsNotNone(panel.flow_diagram.data)
            page.show();self.app.processEvents()
            self.assertLessEqual(page.width(),760)
            self.assertLessEqual(page.height(),900)
            page.open_record_tab('calculator:vswr')
            self.assertEqual(page.workspace_tabs.currentWidget().selector.currentData(),'vswr')
        finally:page.close()

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
        self.assertEqual(page.tabs.currentIndex(), 5)
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
        page.cell_channel.radio.setCurrentText('LTE')
        page.cell_channel.channel.setText('68586')
        page.cell_channel.inspect()
        self.assertIn('617 MHz', page.cell_channel.result.toPlainText())
        page.cell_channel.reverse_mode.setCurrentText('LTE downlink')
        page.cell_channel.reverse_band.setCurrentIndex(page.cell_channel.reverse_band.findData(71))
        page.cell_channel.frequency.setText('617.1')
        page.cell_channel.reverse_lookup()
        self.assertEqual(page.cell_channel.channel.text(), '68587')
        page.activate_record('inspector:signal_guide')
        self.assertEqual(page.tabs.currentWidget(), page.signal_guide)
        page.signal_guide.inputs['rsrp'].setText('-85')
        page.signal_guide.inputs['sinr'].setText('0')
        page.signal_guide.interpret()
        self.assertIn('Strong power', page.signal_guide.result.toPlainText())
        self.assertIn('RSRP ≥ -90', page.signal_guide.result.toPlainText())
        self.assertIn('SINR < 5', page.signal_guide.result.toPlainText())
        self.assertTrue(page.signal_guide.copy_button.isEnabled())
        page.signal_guide.radio.setCurrentText('NR')
        self.assertEqual(page.signal_guide.inputs['rsrp'].text(), '')
        self.assertEqual(page.signal_guide.result.toPlainText(), '')
        self.assertEqual(page.signal_guide.form.labelForField(page.signal_guide.inputs['rsrp']).text(), 'SS-RSRP')
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

    def test_signal_guide_fits_field_width(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page = ToolboxPage()
        page.resize(760, 650)
        page.tabs.setCurrentWidget(page.signal_guide)
        page.show()
        self.app.processEvents()
        self.assertLessEqual(page.signal_guide.sizeHint().width(), page.width())
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
        self.assertEqual(card.open_button.text(), 'Open tab')
        card.setFocus()
        QTest.keyClick(card, Qt.Key.Key_Return)
        self.assertEqual(page.workspace_tabs.count(), 2)
        self.assertEqual(page.workspace_tabs.currentWidget().selector.currentData(), 'fspl')
        page.close()

    def test_calculator_tabs_preserve_independent_results_and_can_reopen(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page = ToolboxPage()
        self.assertEqual(page.workspace_tabs.count(), 1)
        page.open_record_tab('calculator:fspl')
        first = page.workspace_tabs.currentWidget()
        self.assertFalse(first.selector.isVisibleTo(page))
        first.inputs['frequency'].setText('5800')
        first.run_calculation()
        self.assertIsNotNone(first.snapshot)
        page.open_record_tab('calculator:eirp')
        second = page.workspace_tabs.currentWidget()
        self.assertIsNot(first, second)
        self.assertEqual(second.selector.currentData(), 'eirp')
        self.assertEqual(page.workspace_tabs.count(), 3)
        page.open_record_tab('calculator:fspl')
        self.assertIs(page.workspace_tabs.currentWidget(), first)
        self.assertEqual(first.inputs['frequency'].text(), '5800')
        self.assertIsNotNone(first.snapshot)
        page.close_workspace_tab(page.workspace_tabs.indexOf(first))
        self.assertEqual(page.workspace_tabs.count(), 2)
        page.open_record_tab('calculator:fspl')
        self.assertIsNot(page.workspace_tabs.currentWidget(), first)
        self.assertEqual(page.workspace_tabs.currentWidget().inputs['frequency'].text(), '2400')
        page.close()

    def test_reference_tabs_and_browse_tab_have_separate_lifetimes(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page = ToolboxPage()
        references = [record for record in page.records if record.kind == 'reference']
        page.open_record_tab(references[0].record_id)
        first = page.workspace_tabs.currentWidget()
        self.assertEqual(page.workspace_tabs.tabText(page.workspace_tabs.currentIndex()), references[0].title)
        self.assertIn('LTE EARFCN', first.body.toPlainText())
        page.open_record_tab(references[1].record_id)
        second = page.workspace_tabs.currentWidget()
        self.assertIsNot(first, second)
        page.global_search.setText(references[0].title)
        page.result_cards[0].open_button.click()
        self.assertIs(page.workspace_tabs.currentWidget(), first)
        page.open_record_tab(references[0].record_id)
        self.assertEqual(page.workspace_tabs.count(), 3)
        self.assertIs(page.workspace_tabs.currentWidget(), first)
        page.close_workspace_tab(0)
        self.assertEqual(page.workspace_tabs.count(), 3)
        self.assertIsNone(page.workspace_tabs.tabBar().tabButton(0, page.workspace_tabs.tabBar().ButtonPosition.RightSide))
        page.close_workspace_tab(page.workspace_tabs.indexOf(first))
        self.assertEqual(page.workspace_tabs.count(), 2)
        self.assertIs(page.workspace_tabs.widget(1), second)
        page.close()

    def test_multiple_open_tool_tabs_fit_field_width(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        from veilbreaker.gui import STYLE
        previous = self.app.styleSheet()
        self.app.setStyleSheet(STYLE)
        try:
            page = ToolboxPage()
            page.resize(760, 650)
            page.open_record_tab('calculator:fspl')
            page.open_record_tab('calculator:eirp')
            page.open_record_tab(next(record.record_id for record in page.records if record.kind == 'reference'))
            page.show()
            self.app.processEvents()
            self.assertLessEqual(page.workspace_tabs.currentWidget().sizeHint().width(), page.width())
            self.assertGreaterEqual(page.workspace_tabs.tabBar().width(), 1)
            self.assertLessEqual(page.height(), 900)
            page.close()
        finally:
            self.app.setStyleSheet(previous)

    def test_open_tab_prioritizes_work_area_and_search_returns_to_browse(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        page = ToolboxPage()
        page.show()
        self.app.processEvents()
        self.assertTrue(page.discovery.isVisibleTo(page))
        page.open_record_tab('calculator:fspl')
        self.app.processEvents()
        self.assertFalse(page.discovery.isVisibleTo(page))
        self.assertTrue(page.global_search.isVisibleTo(page))
        page.global_search.setText('fiber')
        self.app.processEvents()
        self.assertEqual(page.workspace_tabs.currentIndex(), 0)
        self.assertTrue(page.discovery.isVisibleTo(page))
        page.close()

    def test_calculator_tabs_share_preset_storage_without_sharing_unsaved_inputs(self):
        from types import SimpleNamespace
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from PySide6.QtWidgets import QWidget
        from veilbreaker.toolbox_ui import ToolboxPage
        with TemporaryDirectory() as folder:
            parent = QWidget()
            parent.config = SimpleNamespace(root=Path(folder))
            page = ToolboxPage(parent)
            page.open_record_tab('calculator:fspl')
            first = page.workspace_tabs.currentWidget()
            self.assertEqual(first.preset_path, Path(folder) / 'tool-presets.json')
            first.inputs['frequency'].setText('5800')
            self.assertTrue(first.save_current_preset('5.8 GHz path'))
            page.close_workspace_tab(page.workspace_tabs.indexOf(first))
            page.open_record_tab('calculator:fspl')
            reopened = page.workspace_tabs.currentWidget()
            self.assertEqual(reopened.preset_selector.count(), 1)
            self.assertEqual(reopened.inputs['frequency'].text(), '2400')
            self.assertTrue(reopened.load_selected_preset())
            self.assertEqual(reopened.inputs['frequency'].text(), '5800')
            page.close()
            parent.close()

    def test_fspl_handoff_opens_independent_link_budget_with_exported_origin(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        from veilbreaker.field_tools import format_snapshot
        page = ToolboxPage()
        page.open_record_tab('calculator:link_budget')
        original = page.workspace_tabs.currentWidget()
        original.inputs['tx_power'].setText('33')
        page.open_record_tab('calculator:fspl')
        fspl = page.workspace_tabs.currentWidget()
        fspl.inputs['frequency'].setText('5800')
        fspl.inputs['distance'].setText('0.25')
        fspl.run_calculation()
        self.assertTrue(fspl.handoff_button.isEnabled())
        fspl.handoff_button.click()
        linked = page.workspace_tabs.currentWidget()
        self.assertIsNot(linked, original)
        self.assertEqual(linked.selector.currentData(), 'link_budget')
        self.assertEqual(original.inputs['tx_power'].text(), '33')
        self.assertIsNone(linked.snapshot)
        self.assertIn('Free-space path loss', linked.source_label.text())
        linked.run_calculation()
        self.assertEqual(linked.snapshot['source']['tool_id'], 'fspl')
        self.assertIn('Ideal far-field', format_snapshot(linked.snapshot))
        linked.inputs['tx_power'].setText('26')
        linked.run_calculation()
        self.assertIn('source', linked.snapshot)
        linked.inputs['path_loss'].setText('110')
        linked.run_calculation()
        self.assertNotIn('source', linked.snapshot)
        self.assertEqual(page.workspace_tabs.count(), 4)
        page.close()

    def test_handoff_tabs_fit_narrow_tools_workspace_and_close_independently(self):
        from veilbreaker.toolbox_ui import ToolboxPage
        from veilbreaker.gui import STYLE
        previous = self.app.styleSheet()
        self.app.setStyleSheet(STYLE)
        try:
            page = ToolboxPage()
            page.resize(760, 650)
            page.open_record_tab('calculator:fspl')
            fspl = page.workspace_tabs.currentWidget()
            fspl.run_calculation()
            fspl.handoff_button.click()
            first = page.workspace_tabs.currentWidget()
            fspl.handoff_button.click()
            second = page.workspace_tabs.currentWidget()
            page.show()
            self.app.processEvents()
            self.assertIsNot(first, second)
            self.assertLessEqual(page.width(), 760)
            self.assertLessEqual(page.height(), 900)
            page.close_workspace_tab(page.workspace_tabs.indexOf(first))
            self.assertEqual(page.workspace_tabs.currentWidget(), second)
            page.close()
        finally:
            self.app.setStyleSheet(previous)
