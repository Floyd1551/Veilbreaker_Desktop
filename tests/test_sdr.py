from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from veilbreaker import core


class SDRTests(unittest.TestCase):
    def test_repeated_sweeps_keep_bin_width(self):
        bins = [core.SweepBin(2400.5e6, -40), core.SweepBin(2400.5e6, -42),
                core.SweepBin(2401.5e6, -50), core.SweepBin(2401.5e6, -48)]
        result = core.HackRFCollector.summarize("test", core.SDRRange("test", 2400, 2402), bins, Path("unused.csv"))
        self.assertEqual(result.bin_width_hz, 1_000_000)
        self.assertEqual(result.bins, 4)

    def test_explicit_tool_directory_wins(self):
        with tempfile.TemporaryDirectory() as folder:
            suffix = ".exe" if core.os.name == "nt" else ""
            executable = Path(folder) / ("hackrf_sweep" + suffix)
            executable.touch()
            collector = core.HackRFCollector(core.SDRConfig(tools_dir=folder), Path(folder))
            self.assertEqual(collector.tool_path("hackrf_sweep"), str(executable))
            self.assertIsNone(collector.tool_path("hackrf_info"))

    def test_unknown_board_is_a_note_not_fake_qualification(self):
        output = "hackrf_info version: 2024.02.1\nFound HackRF\nBoard ID Number: 5 (unknown)\nFirmware Version: unknown (API:1.09)\n"
        with tempfile.TemporaryDirectory() as folder:
            collector = core.HackRFCollector(core.SDRConfig(), Path(folder))
            with patch.object(collector, "tool_path", return_value="hackrf_info"), patch.object(core, "run_command", return_value=core.CommandResult([], 0, output, "", 0)):
                metrics, notes = collector.info()
            self.assertTrue(metrics["sdr_present"])
            self.assertEqual(metrics["sdr_host_version"], "2024.02.1")
            self.assertTrue(notes)

    def test_sweep_rejects_fractional_cli_frequency(self):
        with tempfile.TemporaryDirectory() as folder:
            collector = core.HackRFCollector(core.SDRConfig(), Path(folder))
            with self.assertRaises(ValueError):
                collector._validate(core.SDRRange("invalid", 2400.5, 2500))

    def test_sweep_parser_ignores_nonfinite_power(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sweep.csv"
            path.write_text("date,time,2400000000,2405000000,1000000,20,-40,nan,inf,-50\n", encoding="utf-8")
            bins = core.HackRFCollector.parse_sweep_csv(path)
            self.assertEqual([b.power_db for b in bins], [-40, -50])
