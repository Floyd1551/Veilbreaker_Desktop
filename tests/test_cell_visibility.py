import copy
import unittest
from test_android_capture import fixture


class VisibilityTests(unittest.TestCase):
    def test_network_codes_alone_cannot_identify_a_cell(self):
        from veilbreaker.cell_visibility import build_visibility
        data=fixture(); cells=data['observations'][0]['cells']
        cells[0].update(registered=False, connection_status='none', identity={'mcc':'310','mnc':'260'})
        cells.append(copy.deepcopy(cells[0]))
        self.assertEqual(len(build_visibility(data)['neighbors']),2)

    def test_latest_serving_cell_has_priority_over_history_cap(self):
        from veilbreaker.cell_visibility import build_visibility
        data=fixture(); template=copy.deepcopy(data['observations'][0]); data['observations']=[]
        for i in range(4):
            obs=copy.deepcopy(template); obs['observation_id']=str(i); obs['elapsed_realtime_ms']+=i*5000
            obs['cells']=[]
            for j in range(256):
                cell=copy.deepcopy(template['cells'][0]); cell.update(registered=False,connection_status='none')
                cell['identity']['cell_id']=str(i*256+j); obs['cells'].append(cell)
            data['observations'].append(obs)
        latest=copy.deepcopy(template); latest['observation_id']='latest'; latest['elapsed_realtime_ms']+=25000
        data['observations'].append(latest)
        result=build_visibility(data)
        self.assertEqual(len(result['connected']),1)
        self.assertGreater(result['omitted'],0)

    def test_integration_and_boundary_candidates(self):
        from veilbreaker.cellular_report import build_report, report_html
        from veilbreaker.cell_visibility import band_details, channel_plan
        data = fixture()
        rendered = report_html(build_report(data))
        self.assertIn('Bands observed during capture', rendered)
        self.assertIn('Connected / registered at latest observation', rendered)
        for row in channel_plan()['ranges']:
            field = 'earfcn' if row['radio']=='LTE' else 'nrarfcn'
            for channel in (row['min'], row['max']):
                self.assertIn(row['band'], band_details(row['radio'], {field:channel})['bands'])
            for channel in (row['min']-1, row['max']+1):
                self.assertNotIn(row['band'], band_details(row['radio'], {field:channel})['bands'])

    def test_missing_later_bands_are_not_carried_into_current(self):
        from veilbreaker.cell_visibility import build_visibility
        data = fixture()
        later = copy.deepcopy(data['observations'][0]); later['observation_id']='later'
        later['elapsed_realtime_ms'] += 5000
        later['cells'][0]['identity'] = {'cell_id':'1234','pci':12}
        data['observations'].append(later)
        result = build_visibility(data)
        self.assertEqual(result['connected'][0]['band']['bands'], [])
        self.assertFalse(result['bands'][0]['latest'])

    def test_unknown_registration_and_unknown_identities_stay_separate(self):
        from veilbreaker.cell_visibility import build_visibility
        data=fixture()
        cells=data['observations'][0]['cells']
        cells[0].update(registered=None,connection_status='unknown',identity={})
        cells.append(copy.deepcopy(cells[0]))
        result=build_visibility(data)
        self.assertFalse(result['connected'])
        self.assertEqual(len(result['unknown']),2)

    def test_neighbor_is_visible_without_inheriting_sim_carrier(self):
        from veilbreaker.cell_visibility import build_visibility, visibility_html
        data = fixture()
        data['subscriptions'][0]['network_operator'] = 'Serving carrier'
        neighbor = copy.deepcopy(data['observations'][0]['cells'][0])
        neighbor.update(registered=False, connection_status='none')
        neighbor['identity'] = {'pci': 491, 'earfcn': 5230}
        data['observations'][0]['cells'].append(neighbor)
        result = build_visibility(data)
        self.assertEqual(len(result['connected']), 1)
        self.assertEqual(len(result['neighbors']), 1)
        row = result['neighbors'][0]
        self.assertEqual(row['carrier'], 'Not exposed')
        self.assertEqual(row['band']['bands'], [13])
        self.assertEqual(row['band']['source'], 'channel-derived candidates')
        self.assertIn('491', visibility_html(result))
        self.assertIn('Neighbor', visibility_html(result))

    def test_last_snapshot_clears_connection_and_preserves_history(self):
        from veilbreaker.cell_visibility import build_visibility
        data = fixture()
        later = copy.deepcopy(data['observations'][0]); later['observation_id'] = 'later'
        later['elapsed_realtime_ms'] += 5000; later['cells'] = []
        data['observations'].append(later)
        result = build_visibility(data)
        self.assertFalse(result['connected'])
        self.assertTrue(result['bands'])
        self.assertFalse(result['bands'][0]['latest'])

    def test_reported_bands_win_and_nr_overlap_is_not_resolved(self):
        from veilbreaker.cell_visibility import band_details
        self.assertEqual(band_details('LTE', {'bands':[66], 'earfcn':5230})['bands'], [66])
        result = band_details('NR', {'nrarfcn':640000})
        self.assertTrue({48,77,78}.issubset(result['bands']))
        self.assertEqual(result['source'], 'channel-derived candidates')
        self.assertEqual(band_details('NR', {'nrarfcn':2147483647})['bands'], [])
        self.assertEqual(band_details('LTE', {'earfcn':-1})['bands'], [])

    def test_neighbor_becoming_serving_and_stale_samples(self):
        from veilbreaker.cell_visibility import build_visibility
        data = fixture()
        cell = data['observations'][0]['cells'][0]
        cell.update(registered=False, connection_status='none')
        later = copy.deepcopy(data['observations'][0]); later['observation_id'] = 'later'
        later['elapsed_realtime_ms'] += 5000
        later['cells'][0].update(registered=True, connection_status='secondary', age_ms=20000)
        data['observations'].append(later)
        result = build_visibility(data)
        self.assertEqual(result['connected'][0]['role'], 'Secondary serving')
        self.assertIn('old', result['connected'][0]['freshness'])
        self.assertFalse(result['neighbors'][0]['latest'])
        self.assertEqual(set(result['bands'][0]['roles']), {'Neighbor', 'Secondary serving'})
