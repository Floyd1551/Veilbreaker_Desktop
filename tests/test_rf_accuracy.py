"""Independent numeric anchors and physical invariants for all toolbox calculators.

Reference methods and tolerances: docs/rf-calculator-accuracy.md.
"""
import json
import math
import unittest

from veilbreaker.rf_tools import TOOLS, calculate, format_snapshot


def defaults(tool):
    return {field.key: field.default for field in tool.fields}


class RFAccuracyTests(unittest.TestCase):
    def test_all_registered_defaults_are_finite_and_serializable(self):
        self.assertEqual(len({tool.key for tool in TOOLS}), len(TOOLS))
        for tool in TOOLS:
            with self.subTest(tool=tool.key):
                values = defaults(tool)
                result = calculate(tool.key, values)
                self.assertTrue(all(math.isfinite(x) for x in result['outputs'].values()))
                self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)
                text = format_snapshot(result)
                for label in result['input_labels'].values():
                    self.assertIn(label, text)
                for label in result['outputs']:
                    self.assertIn(label, text)
                self.assertIn(result['limitations'], text)
                values.clear()
                self.assertTrue(result['inputs'])

    def test_every_field_rejects_missing_nonfinite_and_out_of_bounds(self):
        for tool in TOOLS:
            for field in tool.fields:
                bad = [None, '', 'nan', 'inf', '-inf', True, False, [], {},
                       field.minimum - max(1, abs(field.minimum)),
                       field.maximum + max(1, abs(field.maximum))]
                for value in bad:
                    with self.subTest(tool=tool.key, field=field.key, value=value):
                        values = defaults(tool)
                        values[field.key] = value
                        with self.assertRaises(ValueError):
                            calculate(tool.key, values)
                values = defaults(tool)
                del values[field.key]
                with self.assertRaises(ValueError):
                    calculate(tool.key, values)

    def test_every_field_accepts_documented_limits_with_valid_path(self):
        for tool in TOOLS:
            for field in tool.fields:
                for value in (field.minimum, field.maximum):
                    values = defaults(tool)
                    values[field.key] = value
                    if tool.key in ('fresnel', 'curvature'):
                        if field.key == 'distance':
                            values['position'] = value / 2
                        elif field.key == 'position':
                            if value >= 100:
                                continue  # Explicitly excluded endpoint by relational validation.
                            values['distance'] = max(1, value * 2)
                    if tool.key == 'fspl':
                        # Far-field use requires compatible distance/frequency, not all pairs.
                        values['distance' if field.key == 'frequency' else 'frequency'] = 100000
                    with self.subTest(tool=tool.key, field=field.key, value=value):
                        result = calculate(tool.key, values)
                        self.assertTrue(all(math.isfinite(x) for x in result['outputs'].values()))

    def test_power_reference_points_and_round_trips(self):
        for dbm, mw in [(-120, 1e-12), (-30, .001), (0, 1), (10, 10), (30, 1000), (60, 1e6)]:
            with self.subTest(dbm=dbm):
                result = calculate('power_dbm', {'power': dbm})['outputs']
                self.assertTrue(math.isclose(result['Power (mW)'], mw, rel_tol=1e-12))
                for tool, value in [('power_mw', mw), ('power_w', mw / 1000)]:
                    self.assertAlmostEqual(calculate(tool, {'power': value})['outputs']['Power (dBm)'], dbm, places=10)

    def test_wavelength_frequency_inverse(self):
        for frequency, wavelength in [(1, 299.792458), (100, 2.99792458), (2400, .12491352416666667), (6000, .04996540966666667)]:
            result = calculate('wavelength', {'frequency': frequency})['outputs']
            self.assertAlmostEqual(result['Wavelength (m)'], wavelength, places=11)
            self.assertAlmostEqual(result['Quarter wavelength (m)'] * 4, wavelength, places=11)

    def test_fspl_independent_itu_logarithmic_form(self):
        # ITU's engineering-unit form, with constant from exact vacuum light speed.
        for frequency, distance in [(100, 1), (900, 10), (2400, .1), (5800, 5), (60000, 1)]:
            expected = 32.44778322188338 + 20 * math.log10(frequency) + 20 * math.log10(distance)
            actual = calculate('fspl', {'frequency': frequency, 'distance': distance})['outputs']['Free-space path loss (dB)']
            self.assertAlmostEqual(actual, expected, places=10)
        with self.assertRaises(ValueError):
            calculate('fspl', {'frequency': .001, 'distance': .000001})

    def test_eirp_and_budget_against_linear_power_chain(self):
        values = dict(tx_power=17, tx_gain=9, tx_loss=2, path_loss=93,
                      rx_gain=4, rx_loss=1, other_loss=3, sensitivity=-80)
        # Independent multiplication of linear power/gain/loss ratios.
        tx_mw = 50.11872336272722
        eirp_mw = tx_mw * 7.943282347242816 / 1.5848931924611136
        received_mw = eirp_mw * 2.51188643150958 / (1995262314.9688828 * 1.2589254117941673 * 1.9952623149688795)
        result = calculate('link_budget', values)['outputs']
        self.assertAlmostEqual(result['EIRP (dBm)'], 10 * math.log10(eirp_mw), places=10)
        self.assertAlmostEqual(result['Estimated received power (dBm)'], 10 * math.log10(received_mw), places=10)
        self.assertAlmostEqual(result['Margin above sensitivity (dB)'], 11, places=10)
        values['sensitivity'] = -69
        self.assertAlmostEqual(calculate('link_budget', values)['outputs']['Margin above sensitivity (dB)'], 0)

    def test_fresnel_symmetry_and_scaling(self):
        def radius(frequency, length, position):
            return calculate('fresnel', dict(frequency=frequency, distance=length, position=position))['outputs']['First Fresnel radius (m)']
        self.assertAlmostEqual(radius(2400, 10, 2), radius(2400, 10, 8), places=10)
        self.assertAlmostEqual(radius(2400, 10, 5) / radius(9600, 10, 5), 2, places=10)
        self.assertAlmostEqual(radius(2400, 40, 20) / radius(2400, 10, 5), 2, places=10)
        self.assertGreater(radius(2400, 10, 5), radius(2400, 10, 2))

    def test_fresnel_warns_when_paraxial_approximation_is_inaccurate(self):
        unsuitable = calculate('fresnel', dict(frequency=1, distance=.001, position=.0005))
        # Exact first-ellipsoid midpoint radius is 75.4464577 m, not 8.6572579 m.
        self.assertIn('more than 1%', unsuitable['limitations'])
        self.assertIn('Do not use', unsuitable['limitations'])
        ordinary = calculate('fresnel', dict(frequency=2400, distance=1, position=.5))
        self.assertNotIn('more than 1%', ordinary['limitations'])
        self.assertIn('approximation', ordinary['limitations'])

    def test_curvature_against_spherical_sagitta(self):
        # Independent exact midpoint spherical geometry; small-angle error grows with path length.
        for length_km in (1, 10, 100):
            result = calculate('curvature', dict(distance=length_km, position=length_km / 2))['outputs']
            for label, k in [('Geometric Earth bulge (m)', 1), ('4/3 effective Earth bulge (m)', 4/3)]:
                radius = 6371008.8 * k
                angle = length_km * 1000 / (2 * radius)
                exact = 2 * radius * math.sin(angle / 2) ** 2
                self.assertTrue(math.isclose(result[label], exact, rel_tol=6e-6))

    def test_noise_physical_limits_and_bandwidth_scaling(self):
        one_hz = calculate('noise', dict(bandwidth=.000001, temperature=290, noise_figure=0))['outputs']
        self.assertAlmostEqual(one_hz['Thermal noise (dBm)'], -173.9751871942, places=8)
        self.assertEqual(one_hz['Thermal noise (dBm)'], one_hz['Input-referred receiver noise (dBm)'])
        for temp in (145, 290, 580):
            result = calculate('noise', dict(bandwidth=1, temperature=temp, noise_figure=0))['outputs']
            twice = calculate('noise', dict(bandwidth=2, temperature=temp, noise_figure=0))['outputs']
            self.assertAlmostEqual(twice['Thermal noise (dBm)'] - result['Thermal noise (dBm)'], 3.01029995664, places=9)

    def test_cable_power_conservation_and_cascading(self):
        for loss, percent in [(0, 100), (10, 10), (20, 1), (30, .1)]:
            result = calculate('cable_loss', dict(length=100, attenuation=loss, connector_loss=0))['outputs']
            self.assertAlmostEqual(result['Power delivered (%)'], percent, places=10)
        a = calculate('cable_loss', dict(length=30, attenuation=10, connector_loss=1))['outputs']
        b = calculate('cable_loss', dict(length=60, attenuation=10, connector_loss=2))['outputs']
        self.assertAlmostEqual(b['Power delivered (%)'] / 100, (a['Power delivered (%)'] / 100) ** 2, places=12)

    def test_return_loss_reflection_and_vswr(self):
        result = calculate('return_loss', {'return_loss': 20})['outputs']
        self.assertAlmostEqual(result['Reflection coefficient magnitude'], .1)
        self.assertAlmostEqual(result['Reflected power (%)'], 1)
        self.assertAlmostEqual(result['VSWR'], 1.1 / .9)
        self.assertAlmostEqual(result['Mismatch loss (dB)'], -10 * math.log10(.99))
        stronger_match = calculate('return_loss', {'return_loss': 30})['outputs']
        self.assertLess(stronger_match['Reflected power (%)'], result['Reflected power (%)'])

    def test_two_stage_noise_figure_friis(self):
        result = calculate('cascade_nf', {'nf1': 4, 'gain1': 25, 'nf2': 30})['outputs']
        expected = 10 * math.log10(10 ** .4 + (10 ** 3 - 1) / (10 ** 2.5))
        self.assertAlmostEqual(result['Cascaded noise figure (dB)'], expected)
        self.assertAlmostEqual(result['First-stage gain (linear)'], 10 ** 2.5)
        low_gain = calculate('cascade_nf', {'nf1': 4, 'gain1': 0, 'nf2': 30})['outputs']
        self.assertGreater(low_gain['Cascaded noise figure (dB)'], result['Cascaded noise figure (dB)'])

    def test_new_rf_schematics_label_estimates(self):
        from veilbreaker.engineering_diagrams import diagram_data
        reflection = diagram_data(calculate('return_loss', {'return_loss': 20}))
        self.assertEqual(reflection['kind'], 'return_loss')
        self.assertIn('1', reflection['caption'])
        chain = diagram_data(calculate('cascade_nf', {'nf1': 4, 'gain1': 25, 'nf2': 30}))
        self.assertEqual(chain['kind'], 'cascade_nf')
        self.assertEqual(len(chain['stages']), 3)
        self.assertIn('7.54', chain['caption'])
