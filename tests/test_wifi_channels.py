import unittest

from veilbreaker.wifi_channels import channels, inspect_pair


class WifiChannelsTests(unittest.TestCase):
    def test_channel_centers_and_nominal_overlap(self):
        result = inspect_pair('2.4 GHz', 1, 6)
        self.assertEqual(result['first']['center_mhz'], 2412)
        self.assertEqual(result['second']['center_mhz'], 2437)
        self.assertEqual(result['nominal_overlap_mhz'], 0)
        self.assertEqual(inspect_pair('2.4 GHz', 1, 3)['nominal_overlap_mhz'], 10)
        self.assertEqual(inspect_pair('5 GHz', 36, 40)['first']['center_mhz'], 5180)
        self.assertEqual(inspect_pair('6 GHz', 1, 5)['second']['center_mhz'], 5975)

    def test_known_channels_and_invalid_inputs(self):
        self.assertEqual(channels('2.4 GHz'), tuple(range(1, 12)))
        self.assertEqual(channels('6 GHz')[-1], 233)
        for band, channel in (('2.4 GHz', 12), ('5 GHz', 35), ('6 GHz', 2), ('7 GHz', 1)):
            with self.subTest(band=band, channel=channel), self.assertRaises(ValueError):
                inspect_pair(band, channel, channel)
        with self.assertRaises(ValueError):
            inspect_pair('2.4 GHz', True, 6)


if __name__ == '__main__':
    unittest.main()
