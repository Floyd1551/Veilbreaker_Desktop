import math
import unittest
from veilbreaker.terrain_profile import assess_profile

class TerrainTests(unittest.TestCase):
    def test_flat_ridge_and_fresnel_analytic(self):
        result=assess_profile([0,500,1000],[0,0,0],10,10,1000)
        bulge=500*500/(2*6371008.8)
        self.assertAlmostEqual(result['clearance_m'][1],10-bulge)
        self.assertAlmostEqual(result['fresnel_radius_m'][1],math.sqrt(.299792458*250))
        self.assertEqual(result['status'],'no sampled terrain obstruction')
        self.assertEqual(assess_profile([0,500,1000],[0,20,0],10,10)['status'],'sampled terrain obstructed')
        self.assertEqual(assess_profile([0,500,1000],[0,None,0],10,10)['status'],'incomplete')
        self.assertEqual(assess_profile([0,500,1000],[0,0,0],10,10)['fresnel_status'],'unknown frequency')
    def test_bad_inputs(self):
        for distances,elevations,hz in [([0,0,10],[0,0,0],100),([0,500,100001],[0,0,0],100),([0,5,10],[0,0,0],0)]:
            with self.assertRaises(ValueError):assess_profile(distances,elevations,10,10,hz)
        with self.assertRaises(ValueError):assess_profile([0,5,10],[0,0,0],float('nan'),10)
