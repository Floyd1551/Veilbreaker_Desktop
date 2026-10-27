import json
import tempfile
import unittest
from pathlib import Path

from veilbreaker import tool_presets


class ToolPresetTests(unittest.TestCase):
    def test_save_reopen_filter_and_delete(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'tool-presets.json'
            first = tool_presets.save_preset(path, 'Warehouse AP', 'fspl',
                                             {'frequency': '5800', 'distance': '0.25'}, 'roof path')
            second = tool_presets.save_preset(path, 'Warehouse AP', 'fspl',
                                              {'frequency': '2400', 'distance': '1'})
            self.assertNotEqual(first['id'], second['id'])
            self.assertEqual(first['kind'], 'operator preset')
            self.assertEqual(first['inputs'], {'frequency': 5800.0, 'distance': 0.25})
            self.assertEqual(first['units']['frequency'], 'Frequency (MHz)')
            self.assertEqual(first['notes'], 'roof path')
            self.assertEqual(len(tool_presets.list_presets(path, 'fspl')), 2)
            self.assertEqual(tool_presets.list_presets(path, 'eirp'), ())
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['version'], 1)
            self.assertTrue(tool_presets.delete_preset(path, first['id']))
            self.assertFalse(tool_presets.delete_preset(path, first['id']))
            self.assertEqual(tool_presets.list_presets(path, 'fspl')[0]['id'], second['id'])

    def test_invalid_inputs_and_corrupt_store_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'tool-presets.json'
            self.assertEqual(tool_presets.list_presets(path), ())
            for name, tool, inputs in [('', 'fspl', {'frequency': 2400, 'distance': 1}),
                                       ('bad', 'missing', {}),
                                       ('bad', 'fspl', {'frequency': 2400, 'distance': 0}),
                                       ('bad', 'fspl', {'frequency': 2400, 'distance': 1, 'extra': 2})]:
                with self.subTest(name=name, tool=tool, inputs=inputs):
                    with self.assertRaises(ValueError):
                        tool_presets.save_preset(path, name, tool, inputs)
            self.assertFalse(path.exists())
            path.write_text('{not json', encoding='utf-8')
            with self.assertRaises(ValueError):
                tool_presets.list_presets(path)
            with self.assertRaises(ValueError):
                tool_presets.save_preset(path, 'Valid', 'fspl', {'frequency': 2400, 'distance': 1})
            self.assertEqual(path.read_text(encoding='utf-8'), '{not json')

    def test_incomplete_record_is_rejected_before_ui_can_load_it(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'tool-presets.json'
            path.write_text(json.dumps({'version': 1, 'presets': [
                {'id': 'old', 'tool_id': 'fspl', 'inputs': {'frequency': 2400, 'distance': 1}}
            ]}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'invalid entries'):
                tool_presets.list_presets(path)


if __name__ == '__main__':
    unittest.main()
