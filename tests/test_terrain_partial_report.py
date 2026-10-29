import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest

from PySide6.QtWidgets import QApplication
from veilbreaker.terrain_profile import assess_profile
from veilbreaker.path_assessment_report import profile_png, assessment_html, partial_segments


class PartialTerrainReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])

    def test_missing_samples_split_observed_segments_without_interpolation(self):
        runs,gaps=partial_segments([0,10,20,30,40],[100,101,None,103,104])
        self.assertEqual(runs,[[(0,100),(10,101)],[(30,103),(40,104)]])
        self.assertEqual(gaps,[(15,25)])
        profile=assess_profile([0,10,20,30,40],[100,101,None,103,104],2,10,1900)
        self.assertEqual(profile['status'],'incomplete')
        self.assertEqual(profile['line_m'],[])
        png=profile_png(profile)
        self.assertTrue(png.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_missing_endpoints_and_all_missing_remain_incomplete(self):
        runs,gaps=partial_segments([0,10,20,30,40],[None,101,102,103,None])
        self.assertEqual(gaps,[(0,5),(35,40)])
        self.assertEqual(runs,[[(10,101),(20,102),(30,103)]])
        profile=assess_profile([0,10,20],[None,None,None],2,10)
        self.assertIsNone(profile_png(profile))

    def test_incomplete_report_discloses_missing_samples_and_no_clearance(self):
        profile=assess_profile([0,10,20],[100,None,101],2,10)
        value={'profile':profile,'terrain':{'dem':{'source':'Fixture','vertical_datum':'NAVD88',
            'units':'m','crs':'EPSG:4326','sha256':'abc','sample_spacing_m':10},
            'endpoints':[[0,0],[1,1]],'elevations_m':[100,None,101]},
            'endpoint_context':{'candidate':{'verification':'estimated'}}}
        html=assessment_html(value)
        self.assertIn('1 of 3 terrain samples unavailable',html)
        self.assertIn('no clearance conclusion',html.lower())

    def test_all_missing_report_does_not_claim_observed_profile(self):
        profile=assess_profile([0,10,20],[None,None,None],2,10)
        value={'profile':profile,'terrain':{'dem':{'source':'Fixture','vertical_datum':'NAVD88',
            'units':'m','crs':'EPSG:4326','sha256':'abc','sample_spacing_m':10},
            'endpoints':[[0,0],[1,1]],'elevations_m':[None,None,None]},
            'endpoint_context':{'candidate':{'verification':'estimated'}},'profile_png':None}
        html=assessment_html(value)
        self.assertIn('3 of 3 terrain samples unavailable',html)
        self.assertIn('No partial profile is available',html)
        self.assertNotIn('partial profile shows observed',html)


if __name__ == '__main__': unittest.main()
