import unittest
from veilbreaker.display_labels import source_label, status_label, readable_text
from veilbreaker.acquisition import collection_summary
class LabelTests(unittest.TestCase):
 def test_labels_preserve_raw_identity(self):
  source='windows_network'
  data={'collectors':[dict(source=source,required=True,status='no_data')]}
  self.assertIn('Network',collection_summary(data))
  self.assertEqual(data['collectors'][0]['source'],source)
  self.assertEqual(source_label('windows_wifi'),'Wi-Fi')
  self.assertEqual(status_label('no_data'),'No data')
 def test_text_changes_ids_not_paths_or_metric_keys(self):
  self.assertEqual(readable_text('windows_network: missing'), 'Network: missing')
  self.assertEqual(readable_text('windows_wifi_signal'), 'windows_wifi_signal')
  self.assertEqual(readable_text('C:/logs/windows_wifi.json'),'C:/logs/windows_wifi.json')
