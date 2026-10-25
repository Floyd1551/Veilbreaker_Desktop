import math
import unittest

from veilbreaker.rf_tools import calculate


class RFCalculatorTests(unittest.TestCase):
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
