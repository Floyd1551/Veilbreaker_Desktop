import tempfile
import unittest
import json
from pathlib import Path

from veilbreaker.area_coverage import area_preview
from veilbreaker.cell_reference import import_reference, activate_reference
from test_cell_reference import HEADER, ROW, META


class AreaCoverageTests(unittest.TestCase):
    def test_adjacent_terrain_bounds_and_gaps_are_not_called_verified_coverage(self):
        terrain = [dict(kind='terrain', status='available', name='west', bounds_wgs84=[0,0,1,1]),
                   dict(kind='terrain', status='available', name='east', bounds_wgs84=[1,0,2,1])]
        maps = [dict(name='overview', available=True, bounds=[-1,-1,3,2], minzoom=0, maxzoom=10)]
        with tempfile.TemporaryDirectory() as folder:
            report=area_preview([0,0,2,1],terrain,maps,Path(folder)/'references')
            self.assertEqual(report['terrain']['status'],'bounds cover area')
            self.assertEqual(report['map']['status'],'bounds contain area')
            self.assertIn('no-data',report['terrain']['note'])
            terrain[1]['status']='missing'
            report=area_preview([0,0,2,1],terrain,maps,Path(folder)/'references')
            self.assertEqual(report['terrain']['status'],'bounds have gaps')
            self.assertEqual(report['terrain']['gaps'],[[1.0,0.0,2.0,1.0]])

    def test_actual_reference_records_counted_by_radio_and_network(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'cells.csv'
            source.write_text(HEADER+ROW+ROW.replace('12345','12346').replace('-96.8','-80.0'),encoding='utf-8')
            refroot=root/'refs'; row=import_reference(refroot,source,META,lambda:False,lambda _:None)
            activate_reference(refroot,row['dataset_id'])
            report=area_preview([-97,32,-96,34],[],[],refroot)
            self.assertEqual(report['cell']['count'],1)
            self.assertEqual(report['cell']['groups'][0],{'radio':'LTE','mcc':311,'mnc':480,'count':1})
            self.assertIn('not verified towers',report['cell']['note'])

    def test_invalid_area_and_cancel_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):area_preview([1,0,0,1],[],[],folder)
            with self.assertRaisesRegex(ValueError,'cancel'):
                area_preview([0,0,1,1],[],[],folder,cancelled=lambda:True)

    def test_missing_active_reference_does_not_hide_map_and_terrain_results(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'active.json').write_text(json.dumps({'dataset_id':'a'*32}),encoding='utf-8')
            result=area_preview([0,0,1,1],[],[],root)
            self.assertEqual(result['cell']['status'],'reference unavailable')
            self.assertEqual(result['terrain']['status'],'no available terrain bounds')


if __name__ == '__main__':
    unittest.main()
