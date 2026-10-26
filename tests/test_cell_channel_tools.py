import unittest

from veilbreaker.cell_channel_tools import inspect_channel, nr_arfcn_to_mhz, nr_mhz_to_arfcn


class CellChannelToolsTests(unittest.TestCase):
    def test_nr_global_raster_anchor_points_and_round_trip(self):
        for arfcn, mhz in ((0, 0), (599999, 2999.995), (600000, 3000),
                           (620000, 3300), (2016666, 24249.99),
                           (2016667, 24250.08), (2016668, 24250.14)):
            with self.subTest(arfcn=arfcn):
                self.assertAlmostEqual(nr_arfcn_to_mhz(arfcn), mhz, places=5)
                self.assertEqual(nr_mhz_to_arfcn(nr_arfcn_to_mhz(arfcn)), arfcn)

    def test_channel_inspector_preserves_band_ambiguity(self):
        nr = inspect_channel('NR', 620000)
        self.assertEqual(nr['center_mhz'], 3300)
        self.assertEqual(nr['source'], 'channel-derived candidates')
        self.assertIsInstance(nr['bands'], tuple)
        lte = inspect_channel('LTE', 6300)
        self.assertIsNone(lte['center_mhz'])
        self.assertEqual(lte['radio'], 'LTE')
        self.assertIn('frequency', lte['limitations'].lower())
        self.assertEqual(inspect_channel('NR', 640000)['bands'], (48, 77, 78))

    def test_bad_and_off_raster_inputs(self):
        for radio, channel in (('NR', -1), ('NR', 3279166), ('NR', True),
                               ('LTE', 1.5), ('LTE', -1), ('GSM', 100)):
            with self.subTest(radio=radio, channel=channel), self.assertRaises(ValueError):
                inspect_channel(radio, channel)
        for value in (3000.01, float('nan'), -1, 100000):
            with self.subTest(value=value), self.assertRaises(ValueError):
                nr_mhz_to_arfcn(value)


if __name__ == '__main__':
    unittest.main()
