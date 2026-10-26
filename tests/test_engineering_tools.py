import math
import unittest

from veilbreaker.engineering_tools import calculate
from veilbreaker.engineering_diagrams import diagram_data


class EngineeringToolsTests(unittest.TestCase):
    def test_mtu_mss_ipv4_ipv6_and_tunnel_overhead(self):
        basic = calculate('mtu_mss', dict(mtu=1500, ip_header=20, tcp_header=20, encapsulation=0))
        self.assertEqual(basic['outputs']['Effective IP MTU (bytes)'], 1500)
        self.assertEqual(basic['outputs']['TCP MSS (bytes)'], 1460)
        v6 = calculate('mtu_mss', dict(mtu=1500, ip_header=40, tcp_header=20, encapsulation=40))
        self.assertEqual(v6['outputs']['TCP MSS (bytes)'], 1400)
        self.assertEqual(v6['kind'], 'calculated estimate')

    def test_tcp_bandwidth_delay_product(self):
        result = calculate('tcp_bdp', dict(bandwidth=100, rtt=40))
        self.assertEqual(result['outputs']['Bandwidth-delay product (bytes)'], 500000)
        self.assertAlmostEqual(result['outputs']['Bandwidth-delay product (MiB)'], 500000 / 1048576)

    def test_fiber_budget_and_shortfall(self):
        values = dict(tx_min=-3, rx_sensitivity=-20, length=10, attenuation=.35,
                      connectors=2, connector_loss=.5, splices=4, splice_loss=.1, reserve=3)
        result = calculate('fiber_budget', values)
        self.assertAlmostEqual(result['outputs']['Estimated receive power (dBm)'], -7.9)
        self.assertAlmostEqual(result['outputs']['Margin after reserve (dB)'], 9.1)
        values['length'] = 100
        self.assertLess(calculate('fiber_budget', values)['outputs']['Margin after reserve (dB)'], 0)

    def test_poe_budget_and_shortfall(self):
        values = dict(supply=180, allocated=100, target=30, reserve=20)
        result = calculate('poe_budget', values)
        self.assertEqual(result['outputs']['Headroom after target (W)'], 30)
        self.assertEqual(result['outputs']['Additional same-demand devices after target'], 1)
        values['allocated'] = 160
        self.assertEqual(calculate('poe_budget', values)['outputs']['Additional same-demand devices after target'], 0)
        self.assertLess(calculate('poe_budget', values)['outputs']['Headroom after target (W)'], 0)
        fractional = calculate('poe_budget', dict(supply='.3', allocated='0', target='.1', reserve='0'))
        self.assertEqual(fractional['outputs']['Additional same-demand devices after target'], 2)

    def test_schematic_diagrams_use_the_calculation_snapshot(self):
        fiber = calculate('fiber_budget', dict(tx_min=-3, rx_sensitivity=-20, length=10, attenuation=.35,
                                               connectors=2, connector_loss=.5, splices=4, splice_loss=.1, reserve=3))
        data = diagram_data(fiber)
        self.assertEqual(data['kind'], 'fiber_budget')
        self.assertIn('-7.9', ' '.join(data['stages']))
        self.assertIn('9.1', data['caption'])
        self.assertFalse(data['shortfall'])
        poe = calculate('poe_budget', dict(supply=180, allocated=100, target=30, reserve=20))
        data = diagram_data(poe)
        self.assertEqual(data['kind'], 'poe_budget')
        self.assertIn('30', data['caption'])
        self.assertFalse(data['shortfall'])
        poe['outputs']['Headroom after target (W)'] = -5
        self.assertTrue(diagram_data(poe)['shortfall'])
        self.assertIsNone(diagram_data(calculate('tcp_bdp', dict(bandwidth=100, rtt=40))))

    def test_schematic_stages_fit_narrow_canvas(self):
        from veilbreaker.engineering_diagrams import stage_rects
        for width in (200, 270, 900):
            rectangles = stage_rects(width)
            self.assertEqual(len(rectangles), 3)
            self.assertTrue(all(rect.left() >= 0 and rect.right() <= width for rect in rectangles))

    def test_reject_bad_inputs_and_inconsistent_headers(self):
        with self.assertRaises(ValueError):
            calculate('mtu_mss', dict(mtu=68, ip_header=40, tcp_header=60, encapsulation=0))
        with self.assertRaises(ValueError):
            calculate('mtu_mss', dict(mtu=1500, ip_header=21, tcp_header=20, encapsulation=0))
        with self.assertRaises(ValueError):
            calculate('tcp_bdp', dict(bandwidth=0, rtt=40))
        with self.assertRaises(ValueError):
            calculate('fiber_budget', dict(tx_min=-3, rx_sensitivity=-20, length=math.nan,
                                           attenuation=.35, connectors=2, connector_loss=.5,
                                           splices=4, splice_loss=.1, reserve=3))
        with self.assertRaises(ValueError):
            calculate('poe_budget', dict(supply=True, allocated=0, target=30, reserve=0))
        with self.assertRaises(ValueError):
            calculate('fiber_budget', dict(tx_min=-3, rx_sensitivity=-20, length=1,
                                           attenuation=.35, connectors=1.5, connector_loss=.5,
                                           splices=0, splice_loss=.1, reserve=3))
        with self.assertRaises(ValueError):
            calculate('mtu_mss', dict(mtu=1500.5, ip_header=20, tcp_header=20, encapsulation=0))
