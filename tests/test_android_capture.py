import copy
import json
from pathlib import Path
import tempfile
import unittest
from veilbreaker.android_capture import load_capture, validate_capture, normalize_selection


def fixture():
    return json.loads(Path('examples/android-cellular-v1.json').read_text(encoding='utf-8'))


class CaptureTests(unittest.TestCase):
    def test_source_and_serving_mapping(self):
        capture = load_capture(Path('examples/android-cellular-v1.json'))
        result = normalize_selection(capture['envelope'], 'snapshot-1', 0)
        self.assertEqual(result['metrics']['lte_rsrp'], -95)
        self.assertEqual(result['metrics']['rsrp'], -95)
        self.assertNotIn('nr_rsrp', result['metrics'])
        self.assertNotIn('sinr', result['metrics'])
        self.assertEqual(capture['raw_bytes'], Path('examples/android-cellular-v1.json').read_bytes())

    def test_neighbor_selection_rejected(self):
        value = fixture()
        value['observations'][0]['cells'][0]['registered'] = False
        with self.assertRaises(ValueError):
            normalize_selection(value, 'snapshot-1', 0)

    def test_invalid_contract(self):
        for change in ('schema', 'duplicate', 'nonfinite', 'sentinel', 'subscription'):
            value = fixture()
            if change == 'schema': value['schema_version'] = 2
            if change == 'duplicate': value['observations'] *= 2
            if change == 'nonfinite': value['observations'][0]['cells'][0]['signal']['rsrp']['value'] = float('inf')
            if change == 'sentinel': value['observations'][0]['cells'][0]['signal']['rsrp']['value'] = 2147483647
            if change == 'subscription': value['observations'][0]['subscription_key'] = 'unknown'
            with self.assertRaises(ValueError, msg=change): validate_capture(value)

    def test_malformed_enum_types_are_validation_errors(self):
        for bad in ({}, [], 5):
            value = fixture()
            value['collection']['outcome'] = bad
            with self.assertRaises(ValueError): validate_capture(value)

    def test_gps_zero_is_valid_but_missing_not_zero(self):
        value = fixture()
        self.assertNotIn('location', value['observations'][0])
        location = {'status':'available', 'source':'phone', 'provider':'gps', 'fix_utc':value['created_utc'],
                    'latitude_deg':0, 'longitude_deg':0, 'horizontal_accuracy_m':3}
        value['observations'][0]['location'] = location
        validate_capture(value)
        for key, bad in [('latitude_deg',91), ('horizontal_accuracy_m',-1), ('status','unavailable')]:
            broken = copy.deepcopy(value)
            broken['observations'][0]['location'][key] = bad
            with self.assertRaises(ValueError): validate_capture(broken)

    def test_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'bad.json'
            path.write_text('{"schema_version":1,"schema_version":1}')
            with self.assertRaises(ValueError): load_capture(path)

    def test_bounds_and_nr_selection_do_not_mix_subscriptions(self):
        value = fixture()
        other = copy.deepcopy(value['observations'][0])
        other['observation_id'] = 'nr-observation'
        other['subscription_key'] = 'sim-2'
        other['cells'][0]['radio'] = 'NR'
        other['cells'][0]['signal'] = {'ss_rsrp':{'value':-101,'unit':'dBm'}, 'csi_sinr':{'value':12,'unit':'dB'}}
        value['subscriptions'].append({'key':'sim-2'})
        value['observations'].append(other)
        result = normalize_selection(value,'nr-observation',0)
        self.assertEqual(result['metrics']['nr_rsrp'],-101)
        self.assertNotIn('nr_sinr', result['metrics'])
        self.assertNotIn('lte_rsrp', result['metrics'])
        self.assertEqual(result['provenance']['subscription_key'],'sim-2')
        value['observations'][0]['cells'] *= 257
        with self.assertRaises(ValueError): validate_capture(value)

    def test_cached_and_unknown_age_remain_explicit(self):
        value = fixture()
        value['observations'][0]['cells'][0]['age_ms'] = 9000
        self.assertEqual(normalize_selection(value,'snapshot-1',0)['provenance']['age_ms'],9000)
        value['observations'][0]['cells'][0]['age_ms'] = None
        self.assertIsNone(normalize_selection(value,'snapshot-1',0)['provenance']['age_ms'])

    def test_registered_cell_without_connection_role(self):
        for role in ('none', 'unknown'):
            value = fixture()
            value['observations'][0]['cells'][0]['connection_status'] = role
            result = normalize_selection(value, 'snapshot-1', 0)
            self.assertEqual(result['metrics']['rsrp'], -95)
            self.assertEqual(result['provenance']['connection_status'], role)
            self.assertTrue(any('not confirmed' in note for note in result['notes']))
            for registered in (False, None):
                value['observations'][0]['cells'][0]['registered'] = registered
                with self.assertRaises(ValueError): normalize_selection(value, 'snapshot-1', 0)
