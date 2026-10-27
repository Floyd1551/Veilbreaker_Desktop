import unittest

from veilbreaker.field_tools import calculate
from veilbreaker.tool_handoff import fspl_to_link_budget


class ToolHandoffTests(unittest.TestCase):
    def test_fspl_maps_value_and_full_calculation_context(self):
        source = calculate('fspl', {'frequency': 5800, 'distance': 0.25})
        handoff = fspl_to_link_budget(source)
        self.assertEqual(handoff['tool_id'], 'link_budget')
        self.assertEqual(handoff['inputs']['path_loss'], source['outputs']['Free-space path loss (dB)'])
        self.assertEqual(handoff['source']['kind'], 'calculated estimate')
        self.assertEqual(handoff['source']['inputs'], source['inputs'])
        self.assertIn('Ideal far-field', handoff['source']['limitations'])

    def test_rejects_other_tool_and_modified_result(self):
        source = calculate('fspl', {'frequency': 2400, 'distance': 1})
        for bad in (calculate('cable_loss', {'length': 10, 'attenuation': 12, 'connector_loss': 1}),
                    {**source, 'outputs': {'Free-space path loss (dB)': source['outputs']['Free-space path loss (dB)'] + 3}}):
            with self.subTest(bad=bad['tool_id']), self.assertRaises(ValueError):
                fspl_to_link_budget(bad)


if __name__ == '__main__':
    unittest.main()
