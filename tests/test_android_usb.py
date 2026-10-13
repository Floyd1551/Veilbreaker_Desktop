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

    def test_partial_disconnect_keeps_capture_and_cleans_owned_forward(self):
        from veilbreaker.android_usb import collect_session
        capture = fixture()
        calls = []
        def command(path, *args):
            calls.append(args)
            return '41234'
        replies = [dict(session_id='s', status='collecting'),
                   dict(session_id='s', status='collecting', capture=capture), OSError('disconnected'), OSError('disconnected')]
        with patch('veilbreaker.android_usb.list_devices', return_value=[dict(serial='ABC',state='device')]), patch('veilbreaker.android_usb.adb', side_effect=command), patch('veilbreaker.android_usb.request', side_effect=replies), patch('veilbreaker.android_usb.time.sleep'), patch('veilbreaker.android_usb.time.monotonic', return_value=0):
            result = collect_session('adb', 'ABC', 'a'*32, 5)
        self.assertEqual(result['collection']['outcome'], 'partial')
        self.assertEqual(result['observations'], capture['observations'])
        self.assertEqual(calls[-1], ('-s','ABC','forward','--remove','tcp:41234'))

    def test_no_data_failure_still_cleans_forward(self):
        from veilbreaker.android_usb import collect_session
        with patch('veilbreaker.android_usb.list_devices', return_value=[dict(serial='ABC',state='device')]), patch('veilbreaker.android_usb.adb', return_value='41234') as command, patch('veilbreaker.android_usb.request', side_effect=ValueError('bad token')):
            with self.assertRaisesRegex(ValueError, 'No phone observations'):
                collect_session('adb', 'ABC', 'a'*32, 5)
            self.assertEqual(command.call_args.args, ('adb','-s','ABC','forward','--remove','tcp:41234'))

    def test_cancel_preserves_completed_observations(self):
        from veilbreaker.android_usb import collect_session
        capture = fixture()
        replies = [dict(session_id='s', status='collecting',capture=capture), dict(session_id='s',status='cancelled',capture=capture), dict(session_id='s',status='cancelled',capture=capture)]
        with patch('veilbreaker.android_usb.list_devices', return_value=[dict(serial='ABC',state='device')]), patch('veilbreaker.android_usb.adb', return_value='41234'), patch('veilbreaker.android_usb.request', side_effect=replies):
            result = collect_session('adb', 'ABC', 'a'*32, 5, cancelled=__import__('unittest.mock', fromlist=['Mock']).Mock(side_effect=[False, False, True]))
        self.assertEqual(result['collection']['outcome'], 'cancelled')

    def test_invalid_target_and_duration_do_not_start_transport(self):
        from veilbreaker.android_usb import collect_session
        with patch('veilbreaker.android_usb.adb') as command:
            for serial, duration in [('ABC',301), ('192.168.1.1:5555',5), ('ABC',0)]:
                with self.assertRaises(ValueError): collect_session('adb', serial, 'a'*32, duration)
            command.assert_not_called()

    def test_windows_usb_discovery_without_bus_path(self):
        output = 'device {\n serial: "ABC"\n state: DEVICE\n connection_type: USB\n}\ndevice {\n serial: "WIFI"\n state: DEVICE\n connection_type: SOCKET\n}'
        with patch('veilbreaker.android_usb.adb', return_value=output):
            self.assertEqual(list_devices('adb'), [{'serial':'ABC','state':'device'}])

    def test_precancelled_session_never_uses_adb(self):
        from veilbreaker.android_usb import collect_session
        with patch('veilbreaker.android_usb.adb') as command:
            with self.assertRaisesRegex(ValueError, 'cancelled'):
                collect_session('adb','ABC','a'*32,5,cancelled=lambda: True)
            command.assert_not_called()

    def test_signal_ranges_are_per_cell(self):
        value = fixture()
        other = json.loads(json.dumps(value['observations'][0]))
        other['observation_id'] = 'second'
        other['cells'][0]['signal']['rsrp']['value'] = -105
        value['observations'].append(other)
        signal = summarize_session(value)['registered_cells'][0]['signals']['rsrp']
        self.assertEqual(signal, dict(min=-105,max=-95,first=-95,last=-105,change=-10,unit='dBm'))

    def test_windows_adb_without_proto_or_bus_path_uses_usb_selector(self):
        def command(path, *args):
            if args == ('devices', '--proto-text'): raise ValueError('unsupported option')
            if args == ('-d', 'get-serialno'): return 'PHONE123'
            if args == ('devices', '-l'): return 'List of devices attached\nPHONE123 device product:test model:Test transport_id:1\n192.168.1.2:5555 device model:Other\n'
            raise AssertionError(args)
        with patch('veilbreaker.android_usb.adb', side_effect=command):
            self.assertEqual(list_devices('adb'), [dict(serial='PHONE123',state='device')])

    def test_ambiguous_windows_usb_is_not_guessed(self):
        def command(path, *args):
            if args == ('devices', '-l'): return 'List of devices attached\nPHONE123 device transport_id:1\nPHONE456 device transport_id:2\n'
            raise ValueError('unsupported or multiple USB devices')
        with patch('veilbreaker.android_usb.adb', side_effect=command):
            self.assertEqual(list_devices('adb'), [])
