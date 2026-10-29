import json
import math
import unittest

from veilbreaker.rf_tools import calculate, format_snapshot
from veilbreaker.tool_registry import build_registry, search_registry


class AdditionalRFToolsTests(unittest.TestCase):
    def test_vswr_conversion_and_ideal_match(self):
        result=calculate('vswr',{'vswr':2})
        self.assertAlmostEqual(result['outputs']['Reflection coefficient magnitude'],1/3)
        self.assertAlmostEqual(result['outputs']['Return loss (dB)'],9.5424250944)
        self.assertAlmostEqual(result['outputs']['Reflected power (%)'],100/9)
        self.assertAlmostEqual(result['outputs']['Mismatch loss (dB)'],0.5115252245)
        ideal=calculate('vswr',{'vswr':1})
        self.assertEqual(ideal['outputs']['Reflected power (%)'],0)
        self.assertNotIn('Return loss (dB)',ideal['outputs'])
        self.assertIn('infinite',ideal['limitations'].lower())
        json.dumps(ideal,allow_nan=False)
        self.assertIn('Return loss (dB): infinite (ideal)',format_snapshot(ideal))
        near=calculate('vswr',{'vswr':1.000000002})['outputs']
        self.assertGreater(near['Mismatch loss (dB)'],0)

    def test_effective_aperture_isotropic_and_gain_scaling(self):
        result=calculate('aperture',{'frequency':299.792458,'gain':0})
        self.assertAlmostEqual(result['outputs']['Effective aperture (m²)'],1/(4*math.pi))
        gain=calculate('aperture',{'frequency':299.792458,'gain':10})
        self.assertAlmostEqual(gain['outputs']['Effective aperture (m²)'],10/(4*math.pi))
        self.assertIn('not physical',gain['limitations'].lower())

    def test_linear_polarization_mismatch_edges(self):
        match=calculate('polarization',{'angle':0})
        self.assertEqual(match['outputs']['Relative received power (%)'],100)
        angle=calculate('polarization',{'angle':45})
        self.assertAlmostEqual(angle['outputs']['Relative received power (%)'],50)
        self.assertAlmostEqual(angle['outputs']['Polarization mismatch loss (dB)'],3.01029995664)
        orthogonal=calculate('polarization',{'angle':90})
        self.assertEqual(orthogonal['outputs']['Relative received power (%)'],0)
        self.assertNotIn('Polarization mismatch loss (dB)',orthogonal['outputs'])
        self.assertIn('infinite',orthogonal['limitations'].lower())
        self.assertIn('Polarization mismatch loss (dB): infinite (ideal)',format_snapshot(orthogonal))
        json.dumps(orthogonal,allow_nan=False)

    def test_receiver_sensitivity_at_290k_and_cold_source(self):
        inputs=dict(bandwidth=20,temperature=290,noise_figure=5,required_snr=10,implementation_loss=2)
        result=calculate('receiver_sensitivity',inputs)
        self.assertAlmostEqual(result['outputs']['Thermal noise (dBm)'],-100.9648887,places=5)
        self.assertAlmostEqual(result['outputs']['Input-referred receiver noise (dBm)'],-95.9648887,places=5)
        self.assertAlmostEqual(result['outputs']['Estimated receiver sensitivity (dBm)'],-83.9648887,places=5)
        inputs.update(bandwidth=1,temperature=145,noise_figure=3.01029995664,required_snr=0,implementation_loss=0)
        result=calculate('receiver_sensitivity',inputs)
        expected=10*math.log10(1.380649e-23*435*1e9)
        self.assertAlmostEqual(result['outputs']['Estimated receiver sensitivity (dBm)'],expected,places=7)
        self.assertIn('not a measured',result['limitations'].lower())

    def test_search_and_invalid_inputs(self):
        records=build_registry()
        for query,key in [('vswr','vswr'),('effective aperture','aperture'),('polarization mismatch','polarization'),('receiver sensitivity','receiver_sensitivity')]:
            self.assertTrue(any(r.target_id==key for r in search_registry(records,query)))
        for tool,values in [('vswr',{'vswr':.99}),('aperture',{'frequency':0,'gain':0}),
                            ('polarization',{'angle':91}),('polarization',{'angle':True}),
                            ('receiver_sensitivity',dict(bandwidth=0,temperature=290,noise_figure=5,required_snr=10,implementation_loss=2))]:
            with self.assertRaises(ValueError):calculate(tool,values)

    def test_schematic_details_show_assumptions_including_ideal_limits(self):
        from veilbreaker.engineering_diagrams import diagram_data
        for tool,inputs in [('vswr',{'vswr':1}),('aperture',{'frequency':2400,'gain':6}),
                            ('polarization',{'angle':90}),('receiver_sensitivity',dict(bandwidth=20,temperature=290,noise_figure=5,required_snr=10,implementation_loss=2))]:
            diagram=diagram_data(calculate(tool,inputs))
            self.assertIsNotNone(diagram)
            self.assertEqual(len(diagram['stages']),3)
            self.assertTrue(diagram['caption'])


if __name__ == '__main__':unittest.main()
