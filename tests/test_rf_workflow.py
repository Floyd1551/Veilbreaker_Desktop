import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from veilbreaker import core
from veilbreaker.rf_workflow import apply_preset, compare_sweeps, PRESETS, read_trace


class RFWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def capture(self, name, powers, **overrides):
        path = self.folder / f"{name}.csv"
        path.write_text("d,t,2400000000,2404000000,1000000,4," + ",".join(map(str, powers)) + "\n", encoding="utf-8")
        settings = {"bin_width_hz": 1000000, "sweeps": 1, "lna_gain_db": 16, "vga_gain_db": 20,
                    "amp_enable": False, "antenna_power": False}
        settings.update(overrides)
        path.with_suffix(".capture.json").write_text(json.dumps({"returncode": 0, "device_serial": "fixture", "settings": settings}), encoding="utf-8")
        return {"csv_path": str(path), "min_mhz": 2400, "max_mhz": 2404, "bin_width_hz": 1000000}

    def test_presets_have_bounded_counts_and_power_off(self):
        cfg = core.AppConfig()
        cfg.sdr.antenna_power = cfg.sdr.amp_enable = True
        for name in PRESETS:
            apply_preset(cfg, name, sweeps=20, bin_width_hz=100000)
            self.assertFalse(cfg.sdr.antenna_power)
            self.assertFalse(cfg.sdr.amp_enable)
            self.assertEqual(cfg.sdr.sweeps, 20)
            self.assertLessEqual(cfg.sdr.ranges[0].max_mhz, 6000)
        with self.assertRaises(ValueError):
            apply_preset(cfg, next(iter(PRESETS)), sweeps=21)
        with self.assertRaises(ValueError):
            apply_preset(cfg, "unknown")

    def test_delta_sign_and_export_provenance(self):
        before = self.capture("before", [-60, -50, -40, -70])
        after = self.capture("after", [-57, -47, -37, -67])
        result = compare_sweeps(before, after)
        self.assertEqual(result["median_delta_db"], 3)
        self.assertEqual(len(result["before"]["sha256"]), 64)
        self.assertTrue(all(r["delta_db"] == 3 for r in result["rows"]))
        self.assertEqual(result["bin_count"], 4)

    def test_changed_gain_or_resolution_is_rejected(self):
        before = self.capture("before", [-60]*4)
        after = self.capture("after", [-50]*4, lna_gain_db=24)
        with self.assertRaisesRegex(ValueError, "lna_gain_db"):
            compare_sweeps(before, after)
        after["bin_width_hz"] = 500000
        with self.assertRaisesRegex(ValueError, "resolution"):
            compare_sweeps(before, after)

    def test_missing_metadata_and_other_device_are_rejected(self):
        before = self.capture("before", [-60]*4)
        after = self.capture("after", [-50]*4)
        metadata = Path(after["csv_path"]).with_suffix(".capture.json")
        obj = json.loads(metadata.read_text())
        obj["device_serial"] = "other"
        metadata.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, "serial"):
            compare_sweeps(before, after)
        metadata.unlink()
        with self.assertRaisesRegex(ValueError, "unavailable"):
            compare_sweeps(before, after)

    def test_truncated_matching_grids_still_fail(self):
        before = self.capture("before", [-60]*2)
        after = self.capture("after", [-50]*2)
        with self.assertRaisesRegex(ValueError, "full requested range"):
            compare_sweeps(before, after)

    def test_interrupted_capture_is_rejected(self):
        before = self.capture("before", [-60]*4)
        after = self.capture("after", [-50]*4)
        metadata = Path(after["csv_path"]).with_suffix(".capture.json")
        obj = json.loads(metadata.read_text())
        obj["returncode"] = -1
        metadata.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, "interrupted"):
            compare_sweeps(before, after)

    def test_repeated_samples_use_median(self):
        before = self.capture("before", [-60]*4)
        path = Path(before["csv_path"])
        with path.open("a") as stream:
            stream.write("d,t,2400000000,2404000000,1000000,4,-50,-50,-50,-50\n")
        self.assertEqual(read_trace(before)[0][1:], (-55, -50))
