import unittest
from veilbreaker.followup import guidance, details


class FollowupTests(unittest.TestCase):
    def test_unknown_and_sdr_do_not_prepare_generic_capture(self):
        self.assertFalse(guidance('unknown')[0])
        self.assertFalse(guidance('TEST-SDR-COMPARE')[0])

    def test_explicit_options_and_limits(self):
        self.assertEqual(guidance('TEST-DNS')[0], {'active'})
        self.assertEqual(guidance('TEST-THROUGHPUT-REPEAT')[0], {'active', 'throughput'})
        self.assertIn('sequential', guidance('TEST-NSA-NR')[2])
        self.assertIn('alternate resolver', guidance('TEST-DNS')[2])
        self.assertIn('Not supplied', details({}))
