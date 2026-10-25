import math
import unittest

from veilbreaker.rf_tools import calculate


class RFCalculatorTests(unittest.TestCase):
    def test_fresnel_and_curvature(self):
        result = calculate('fresnel', {'frequency': 1000, 'distance': 1, 'position': .5})
        self.assertAlmostEqual(result['outputs']['First Fresnel radius (m)'], 8.657257, places=5)
        self.assertAlmostEqual(result['outputs']['60% clearance radius (m)'], 5.194354, places=5)
        earth = calculate('curvature', {'distance': 10, 'position': 5})['outputs']
        self.assertAlmostEqual(earth['Geometric Earth bulge (m)'], 1.962013, places=5)
        self.assertAlmostEqual(earth['4/3 effective Earth bulge (m)'], earth['Geometric Earth bulge (m)'] * .75)
        for position in (0, 1, 2):
            with self.assertRaises(ValueError):
                calculate('fresnel', {'frequency': 1000, 'distance': 1, 'position': position})

    def test_noise_and_cable_loss(self):
        noise = calculate('noise', {'bandwidth': 20, 'temperature': 290, 'noise_figure': 5})['outputs']
        self.assertAlmostEqual(noise['Thermal noise (dBm)'], -100.9648887, places=5)
        self.assertAlmostEqual(noise['Input-referred receiver noise (dBm)'], -95.9648887, places=5)
        cold = calculate('noise', {'bandwidth': 1, 'temperature': 145, 'noise_figure': 3.01029995664})['outputs']
        # A factor-of-two noise figure contributes Te=290 K, independent of source temperature.
        self.assertAlmostEqual(cold['Input-referred receiver noise (dBm)'], 10 * math.log10(1.380649e-23 * 435 * 1e9), places=7)
        cable = calculate('cable_loss', {'length': 25, 'attenuation': 12, 'connector_loss': 1})['outputs']
        self.assertEqual(cable['Total feed loss (dB)'], 4)
        self.assertAlmostEqual(cable['Power delivered (%)'], 39.810717, places=5)
        with self.assertRaises(ValueError):
            calculate('noise', {'bandwidth': 0, 'temperature': 290, 'noise_figure': 0})

    def test_power_units(self):
        self.assertAlmostEqual(calculate('power_dbm', {'power': 30})['outputs']['Power (W)'], 1)
        self.assertAlmostEqual(calculate('power_mw', {'power': 1000})['outputs']['Power (dBm)'], 30)
        self.assertAlmostEqual(calculate('power_w', {'power': .001})['outputs']['Power (dBm)'], 0)
        self.assertAlmostEqual(calculate('power_dbm', {'power': -90})['outputs']['Power (mW)'], 1e-9)

    def test_wavelength_and_fspl(self):
        self.assertAlmostEqual(calculate('wavelength', {'frequency': 1000})['outputs']['Wavelength (m)'], .299792458)
        result = calculate('fspl', {'frequency': 2400, 'distance': 1})
        self.assertAlmostEqual(result['outputs']['Free-space path loss (dB)'], 100.052, places=3)
        doubled = calculate('fspl', {'frequency': 2400, 'distance': 2})
        self.assertAlmostEqual(doubled['outputs']['Free-space path loss (dB)'] - result['outputs']['Free-space path loss (dB)'], 6.0206, places=4)

    def test_eirp_and_link_margin(self):
        values = {'tx_power': 20, 'tx_gain': 12, 'tx_loss': 2}
        self.assertEqual(calculate('eirp', values)['outputs']['EIRP (dBm)'], 30)
        values.update(path_loss=110, rx_gain=8, rx_loss=1, other_loss=3, sensitivity=-85)
        result = calculate('link_budget', values)
        self.assertEqual(result['outputs']['Estimated received power (dBm)'], -76)
        self.assertEqual(result['outputs']['Margin above sensitivity (dB)'], 9)
        values['path_loss'] = 130
        self.assertEqual(calculate('link_budget', values)['outputs']['Margin above sensitivity (dB)'], -11)
        self.assertEqual(result['inputs']['path_loss'], 110)
        self.assertIn('version', result)
        self.assertTrue(result['limitations'])

    def test_reject_invalid_values(self):
        for value in [0, -1, math.nan, math.inf, -math.inf, True, 'bad', 1e300]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                calculate('power_w', {'power': value})
        with self.assertRaises(ValueError):
            calculate('fspl', {'frequency': 2400, 'distance': 0})
        with self.assertRaises(ValueError):
            calculate('eirp', {'tx_power': 20, 'tx_gain': 2, 'tx_loss': -1})
        with self.assertRaises(ValueError):
            calculate('wavelength', {})
        with self.assertRaises(ValueError):
            calculate('missing', {})
