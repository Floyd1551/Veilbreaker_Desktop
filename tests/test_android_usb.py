import json
import unittest
from unittest.mock import patch
from veilbreaker.android_usb import list_devices, validate_response, summarize_session
from test_android_capture import fixture

class UsbTests(unittest.TestCase):
    def test_only_authorized_usb_devices(self):
        output = 'List of devices attached\nABC device usb:1-2 product:x\nNO unauthorized usb:1-3\n192.168.1.2:5555 device product:x\n'
        with patch('veilbreaker.android_usb.adb', return_value=output):
            self.assertEqual(list_devices('adb'), [{'serial':'ABC','state':'device'}, {'serial':'NO','state':'unauthorized'}])

    def test_response_identifiers_and_capture_validation(self):
        body = dict(protocol=1, request_id='r', session_id='s', status='collecting', capture=fixture())
        self.assertEqual(validate_response(body, 'r', 's')['status'], 'collecting')
        for field in ('request_id', 'session_id'):
            broken = dict(body); broken[field] = 'old'
            with self.assertRaises(ValueError): validate_response(broken, 'r', 's')
        body['capture']['schema_version'] = 20
        with self.assertRaises(ValueError): validate_response(body, 'r', 's')

    def test_summaries_do_not_blend_cells(self):
        value = fixture()
        other = json.loads(json.dumps(value['observations'][0]))
        other['observation_id'] = 'second'
        other['elapsed_realtime_ms'] += 5000
        other['cells'][0]['age_ms'] += 5000
        value['observations'].append(other)
        result = summarize_session(value)
        self.assertEqual(result['observations'], 2)
        self.assertEqual(result['repeated_samples'], 1)
