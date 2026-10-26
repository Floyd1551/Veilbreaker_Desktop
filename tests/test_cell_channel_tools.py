import unittest

from veilbreaker.cell_channel_tools import inspect_channel, nr_arfcn_to_mhz, nr_mhz_to_arfcn, lte_earfcn_to_mhz, lte_mhz_to_earfcn, LTE_DL_LOW_MHZ
from veilbreaker.cell_visibility import channel_plan


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
        self.assertIn('selected U.S.', lte['limitations'])
        self.assertEqual(inspect_channel('NR', 640000)['bands'], (48, 77, 78))

    def test_selected_us_lte_downlink_anchors(self):
        for band, channel, mhz in ((2, 600, 1930), (2, 1199, 1989.9),
                                   (13, 5180, 746), (14, 5280, 758),
                                   (41, 39650, 2496), (66, 66436, 2110),
                                   (71, 68586, 617), (71, 68935, 651.9)):
            with self.subTest(band=band, channel=channel):
                self.assertAlmostEqual(lte_earfcn_to_mhz(band, channel), mhz)
                self.assertEqual(lte_mhz_to_earfcn(band, mhz), channel)
                info = inspect_channel('LTE', channel)
                self.assertAlmostEqual(info['center_mhz'], mhz)
                self.assertEqual(info['bands'], (band,))
                self.assertEqual(info['frequency_reference_reviewed'], '2026-10-26')
        with self.assertRaises(ValueError):
            lte_earfcn_to_mhz(2, 68586)
        with self.assertRaises(ValueError):
            lte_earfcn_to_mhz(20, 6300)
        for band, mhz in ((71, 617.05), (71, 652), (2, 1989.95), (20, 800), (71, float('nan'))):
            with self.subTest(band=band, mhz=mhz), self.assertRaises(ValueError):
                lte_mhz_to_earfcn(band, mhz)

    def test_each_selected_lte_band_has_one_bundled_range(self):
        for band in LTE_DL_LOW_MHZ:
            rows = [row for row in channel_plan()['ranges'] if row['radio'] == 'LTE' and row['band'] == band]
            with self.subTest(band=band):
                self.assertEqual(len(rows), 1)
                self.assertAlmostEqual(lte_earfcn_to_mhz(band, rows[0]['min']), LTE_DL_LOW_MHZ[band])
                self.assertGreater(lte_earfcn_to_mhz(band, rows[0]['max']), LTE_DL_LOW_MHZ[band])

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
