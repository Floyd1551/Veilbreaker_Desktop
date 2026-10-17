import copy,json,unittest
from veilbreaker.map_data import build_map_data,map_bounds,export_geojson

def fix(**changes):
    return dict(dict(status='available',latitude_deg=0,longitude_deg=0,horizontal_accuracy_m=25,fix_age_ms=10000,observation_id='same'),**changes)

class MapDataTests(unittest.TestCase):
    def model(self,*locations):
        return build_map_data([dict(run_id='r',label='<script>',locations=list(locations))])
    def test_quality_coordinates_and_immutable_input(self):
        rows=[fix(),fix(longitude_deg=12,latitude_deg=30,fix_age_ms=10001),fix(mock=True),fix(horizontal_accuracy_m=26),fix(fix_age_ms=None)]
        before=copy.deepcopy(rows);m=self.model(*rows)
        self.assertEqual(m['features']['features'][0]['geometry']['coordinates'],[0,0])
        self.assertEqual(m['features']['features'][1]['geometry']['coordinates'],[12,30])
        self.assertEqual(m['representatives'],['p0'])
        self.assertEqual(m['counts']['questionable'],4)
        self.assertEqual(rows,before)
    def test_invalid_and_legacy_do_not_hide_good_run(self):
        m=build_map_data([dict(run_id='old',locations=[]),dict(run_id='bad',locations=[fix(latitude_deg=float('nan')),None]),dict(run_id='good',locations=[fix()])])
        self.assertEqual(len(m['features']['features']),1)
        self.assertEqual(m['counts']['unpositioned_runs'],2)
        self.assertTrue(m['warnings'])
        json.dumps(m,allow_nan=False)
    def test_duplicate_ids_overlap_polar_and_bounds(self):
        m=build_map_data([dict(run_id='a',locations=[fix(longitude_deg=179),fix(longitude_deg=-179)]),dict(run_id='b',locations=[fix(longitude_deg=179),fix(latitude_deg=89)])])
        fs=m['features']['features']
        self.assertEqual(len({f['id'] for f in fs}),4)
        b=map_bounds(fs);self.assertAlmostEqual(b[2]-b[0],2)
        self.assertFalse(m['rows'][-1]['renderable'])
        self.assertEqual(fs[-1]['geometry']['coordinates'][1],89)
        exported=json.loads(export_geojson(m,['p3']))
        self.assertEqual(len(exported['features']),1)
    def test_stored_quality_not_trusted(self):
        m=self.model(fix(mock=True,quality={'qualified':True}))
        self.assertEqual(m['representatives'],[])
