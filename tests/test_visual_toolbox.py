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
