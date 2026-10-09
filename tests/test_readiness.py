import tempfile
import unittest
from unittest.mock import patch
from veilbreaker import core
from veilbreaker.readiness import check_selected


class ReadinessTests(unittest.TestCase):
    def test_unselected_hardware_omitted_and_no_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(core.HackRFCollector, 'info') as probe:
                result = check_selected(core.AppConfig(data_dir=folder), {})
                probe.assert_not_called()
            self.assertFalse(any('HackRF' in r['item'] for r in result['rows']))
            self.assertTrue(result['checked_utc'])

    def test_missing_throughput_target_and_executable(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(core, 'command_exists', return_value=False):
                result = check_selected(core.AppConfig(data_dir=folder), {'throughput': True})
            rows = {r['item']:r for r in result['rows']}
            self.assertEqual(rows['iperf3']['state'], 'Missing')
            self.assertEqual(rows['Throughput server']['state'], 'Missing')
