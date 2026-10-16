import unittest
from veilbreaker.sdr_assessment import compare_capture_context
class SdrAssessmentTests(unittest.TestCase):
 def test_only_identical_complete_context_qualifies(self):
  context = dict(receiver='abc', ranges=[[100,200]], bin_width=100000, lna=16, vga=20, antenna_power=False, amp=False)
  self.assertTrue(compare_capture_context(context, context)['compatible'])
  self.assertFalse(compare_capture_context(context, {})['compatible'])
  self.assertFalse(compare_capture_context(context, dict(context,lna=24))['compatible'])
