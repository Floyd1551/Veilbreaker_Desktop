import unittest
from veilbreaker.core import AppConfig
from veilbreaker.settings_form import apply_network_settings, apply_hardware_settings, target


class NetworkSettingsTests(unittest.TestCase):
    def test_targets_and_optional_server(self):
        for value in ("1.1.1.1", "2001:db8::1", "server.local", "localhost"):
            self.assertEqual(target(value, "Test"), value)
        self.assertEqual(target(" café.example ", "Test"), "xn--caf-dma.example")
        self.assertIsNone(target(" ", "Test", True))
        for value in ("", "https://example.com", "host:5201", "-flag", "a b", "x;command", "a..b"):
            with self.assertRaises(ValueError):
                target(value, "Test")

    def test_network_merge_preserves_hardware_and_original(self):
        cfg = AppConfig()
        cfg.sdr.lna_gain_db = 24
        raw = cfg.to_dict()
        updated = apply_network_settings(raw, "8.8.8.8", "example.net", "", 5202)
        self.assertEqual(updated.sdr.lna_gain_db, 24)
        self.assertEqual(updated.public_ping_target, "8.8.8.8")
        self.assertIsNone(updated.iperf3_server)
        self.assertEqual(raw, cfg.to_dict())
        for port in (0, 65536, True):
            with self.assertRaises(ValueError):
                apply_network_settings(raw, "1.1.1.1", "example.com", "", port)


class HardwareSettingsTests(unittest.TestCase):
    def values(self, **changes):
        values = {"cellular.port": " COM5 ", "cellular.driver": "quectel_rm5xx", "cellular.backend": "serial",
                  "starlink.host": "2001:db8::1", "starlink.port": 9201, "starlink.backend": "grpcurl",
                  "sdr.tools_dir": "C:/Host tools", "sdr.serial": "abcd1234"}
        values.update(changes)
        return values

    def test_merge_preserves_acquisition_privacy_adapters_and_input(self):
        cfg = AppConfig()
        cfg.cellular.include_raw_responses = True
        cfg.cellular.json_command = ["adapter", "--json"]
        cfg.starlink.collect_location = True
        cfg.sdr.antenna_power = True
        cfg.sdr.sweeps = 12
        raw = cfg.to_dict()
        updated = apply_hardware_settings(raw, self.values())
        self.assertEqual(updated.cellular.port, "COM5")
        self.assertEqual(updated.starlink.host, "2001:db8::1")
        self.assertEqual(updated.starlink.port, 9201)
        self.assertEqual(updated.sdr.tools_dir, "C:/Host tools")
        self.assertEqual(updated.cellular.json_command, cfg.cellular.json_command)
        self.assertTrue(updated.cellular.include_raw_responses)
        self.assertTrue(updated.starlink.collect_location)
        self.assertTrue(updated.sdr.antenna_power)
        self.assertEqual(updated.sdr.sweeps, 12)
        self.assertFalse(updated.cellular.enabled)
        self.assertFalse(updated.starlink.enabled)
        self.assertFalse(updated.sdr.enabled)
        self.assertEqual(raw, cfg.to_dict())

    def test_rejects_invalid_targets_ports_and_unconfigured_adapter(self):
        for changes in ({"starlink.host": "https://dish"}, {"starlink.port": 0}, {"starlink.port": True},
                        {"starlink.port": 65536}, {"cellular.backend": "json"},
                        {"cellular.driver": "unsupported"}, {"cellular.port": "COM5\n" + "x"},
                        {"sdr.tools_dir": "a\x00b"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                apply_hardware_settings(AppConfig().to_dict(), self.values(**changes))

    def test_blank_optional_fields_restore_discovery(self):
        cfg = apply_hardware_settings(AppConfig().to_dict(), self.values(**{
            "cellular.port": " ", "sdr.tools_dir": "", "sdr.serial": " "}))
        self.assertEqual(cfg.cellular.port, "auto")
        self.assertIsNone(cfg.sdr.tools_dir)
        self.assertIsNone(cfg.sdr.serial)
