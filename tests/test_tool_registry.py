import unittest
from unittest.mock import patch

from veilbreaker.tool_registry import CATEGORIES, build_registry, search_registry


class ToolRegistryTests(unittest.TestCase):
    def setUp(self):
        self.records = build_registry()

    def test_registry_has_unique_stable_routes_for_existing_content(self):
        ids = [record.record_id for record in self.records]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(self.records), 28)
        self.assertEqual(set(record.kind for record in self.records), {'calculator', 'inspector', 'planner', 'reference'})
        self.assertIn('calculator:fspl', ids)
        self.assertIn('inspector:subnet', ids)
        self.assertIn('calculator:mtu_mss', ids)
        self.assertIn('calculator:tcp_bdp', ids)
        self.assertIn('calculator:fiber_budget', ids)
        self.assertIn('calculator:poe_budget', ids)
        self.assertIn('planner:wifi_channels', ids)
        self.assertIn('calculator:return_loss', ids)
        self.assertIn('calculator:cascade_nf', ids)
        self.assertIn('inspector:cell_channel', ids)
        self.assertIn('inspector:signal_guide', ids)
        self.assertEqual(CATEGORIES, ('RF', 'Cellular', 'Wi-Fi', 'Networking', 'Fiber & Power', 'References'))

    def test_search_uses_all_tokens_keywords_and_category(self):
        found = search_registry(self.records, 'free PATH')
        self.assertEqual([record.record_id for record in found], ['calculator:fspl'])
        self.assertTrue(any(record.title.startswith('Wireless measurements') for record in search_registry(self.records, 'RSRP SINR')))
        networking = search_registry(self.records, '', 'Networking')
        self.assertTrue(networking)
        self.assertTrue(all(record.category == 'Networking' for record in networking))
        self.assertEqual([record.record_id for record in search_registry(self.records, 'MTU MSS')], ['calculator:mtu_mss'])
        self.assertIn('calculator:fiber_budget', [record.record_id for record in search_registry(self.records, 'fiber budget')])
        self.assertEqual([record.record_id for record in search_registry(self.records, 'PoE', 'Fiber & Power')], ['calculator:poe_budget'])
        self.assertEqual([record.record_id for record in search_registry(self.records, 'wifi channel overlap')], ['planner:wifi_channels'])
        self.assertIn('inspector:cell_channel', [record.record_id for record in search_registry(self.records, 'NR ARFCN')])
        self.assertIn('reference:cellular-channel-numbering', [record.record_id for record in search_registry(self.records, 'NR ARFCN')])
        self.assertIn('inspector:signal_guide', [record.record_id for record in search_registry(self.records, 'RSRP SINR')])
        self.assertTrue(any('RSRP' in record.description for record in search_registry(self.records, '', 'Cellular')))
        references = search_registry(self.records, '', 'References')
        self.assertEqual(len(references), 7)
        self.assertTrue(all(record.kind == 'reference' for record in references))

    def test_whitespace_and_unknown_category_are_safe(self):
        self.assertEqual(search_registry(self.records, '   '), self.records)
        self.assertEqual(search_registry(self.records, '', 'Unknown'), ())
        self.assertEqual(search_registry(self.records, 'calculator'), ())

    def test_duplicate_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate tool registry identity'):
            build_registry(extra=(self.records[0],))

    def test_new_reference_does_not_require_parallel_category_table(self):
        with patch('veilbreaker.tool_registry.REFERENCES', (('New field note', '<p>New offline material.</p>'),)):
            records = build_registry()
        reference = next(record for record in records if record.kind == 'reference')
        self.assertEqual(reference.category, 'References')

    def test_cellular_reference_explains_lte_scope(self):
        from veilbreaker.toolbox_reference import REFERENCES
        article = next(body for title, body in REFERENCES if title == 'Cellular channel numbering')
        self.assertIn('selected U.S.', article)
        self.assertIn('band-specific', article)


if __name__ == '__main__':
    unittest.main()
