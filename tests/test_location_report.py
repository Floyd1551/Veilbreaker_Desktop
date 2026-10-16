import unittest
from veilbreaker.location_report import qualify_location,location_rows,representative_fix
class LocationTests(unittest.TestCase):
 def test_quality_bounds_and_missing_are_not_zero(self):
  fix=dict(status='available',latitude_deg=40,longitude_deg=-90,horizontal_accuracy_m=25,fix_age_ms=10000)
  self.assertTrue(qualify_location(fix)['qualified'])
  for change in ({'fix_age_ms':10001},{'horizontal_accuracy_m':26},{'mock':True},{'fix_age_ms':None}):
   self.assertFalse(qualify_location(dict(fix,**change))['qualified'])
  self.assertIsNone(representative_fix(location_rows({'observations':[{'observation_id':'x'}]})))
 def test_association_uses_phone_age_not_desktop_clock(self):
  row=location_rows({'observations':[dict(observation_id='a',received_utc='2026-10-16T00:00:00Z',location=dict(status='available',fix_age_ms=200),cells=[dict(age_ms=500,radio='LTE',identity={'cell_id':'1'})]) ]})[0]
  self.assertEqual(row['cell_offsets'][0]['location_after_modem_ms'],300)
