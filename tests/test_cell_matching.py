import unittest
from unittest.mock import patch
from test_android_capture import fixture
from veilbreaker import cell_matching as match

class MatchingTests(unittest.TestCase):
    def test_nr_full_identity_matches_opencellid_snapshot(self):
        envelope=fixture()
        cell=envelope['observations'][0]['cells'][0]
        cell['radio']='NR'
        cell['identity'].update(tac=123456,cell_id='55341514827')
        cell['signal']={'ss_rsrp': {'value': -101, 'unit': 'dBm'}}
        with patch.object(match,'active_reference',return_value={'format':'opencellid','dataset_id':'fixed'}), \
             patch.object(match,'lookup_reference',return_value=[dict(lon=-86.5,lat=34.7)]) as lookup:
            row=match.match_capture(envelope,'unused')['rows'][0]
            self.assertEqual(row['status'],'reference match')
            self.assertEqual(lookup.call_args.args[1],('NR',310,260,123456,55341514827))

    def test_identity_and_observation_alignment(self):
        envelope=fixture()
        observation=envelope['observations'][0]
        cell=observation['cells'][0]
        cell['identity']['tac']=42
        candidate=dict(lon=-96,lat=32,verification='estimated cell location')
        with patch.object(match,'active_reference',return_value={'format':'opencellid','dataset_id':'fixed'}),patch.object(match,'lookup_reference',return_value=[candidate]) as lookup:
            result=match.match_capture(envelope,'unused')
            self.assertEqual(result['rows'][0]['status'],'reference match')
            self.assertIsNone(result['rows'][0]['candidates'][0]['distance_m'])
            self.assertEqual(lookup.call_args.args[1][0],'LTE')
            cell['identity']['tac']=None
            self.assertEqual(match.match_capture(envelope,'unused')['rows'][0]['status'],'incomplete identity')

    def test_conflict_and_qualified_distance(self):
        envelope=fixture(); obs=envelope['observations'][0]
        obs['cells'][0]['identity']['tac']=42
        obs['location']=dict(source='phone',provider='gps',fix_utc=obs['received_utc'],status='available',latitude_deg=32.,longitude_deg=-96.,horizontal_accuracy_m=5.,fix_age_ms=100,mock=False)
        with patch.object(match,'active_reference',return_value={'format':'operator','dataset_id':'fixed'}),patch.object(match,'lookup_reference',return_value=[dict(lon=-96,lat=33),dict(lon=-95,lat=32)]):
            row=match.match_capture(envelope,'unused')['rows'][0]
            self.assertEqual(row['status'],'conflicting references')
            self.assertAlmostEqual(row['candidates'][0]['distance_m'],111195,delta=2)
            self.assertAlmostEqual(row['candidates'][0]['bearing_deg'],0)
        self.assertEqual(match.distance_bearing(0,0,0,0),(0.0,None))
