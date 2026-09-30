import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from veilbreaker import core, paths
from veilbreaker.cli import main
from veilbreaker.comparison import compare_runs
from veilbreaker.jobs import DEMO_METRICS, execute


class CoreTests(unittest.TestCase):
    def test_recovered_synthetic_suite(self):
        rc, output = core.selftest()
        self.assertEqual(rc, 0, output)

    def test_host_inventory_does_not_claim_healthy_network(self):
        for metrics in ({}, {"host_os": "Windows", "mtu": 1500, "memory_pct": 30}):
            report = core.ProfessionalVeilbreakerEngine().analyze(metrics)
            self.assertEqual(report.status, "INSUFFICIENT_EVIDENCE")

    def test_analysis_preserves_unicode_and_history(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder, site_id="Büro 東京")
            source = Path(folder) / "測定.json"
            source.write_text(json.dumps(DEMO_METRICS), encoding="utf-8")
            with patch.object(core.VeilbreakerApplication, "collect_passive", side_effect=AssertionError("offline analysis must not collect")):
                payload = execute({"action": "analyze", "config": cfg.to_dict(), "input": str(source)})
            with zipfile.ZipFile(payload["evidence_zip"]) as pack:
                self.assertIn(cfg.site_id, pack.read("report.html").decode("utf-8"))
                self.assertIn("health_score", json.loads(pack.read("report.json")))
            store = core.VeilbreakerStore(cfg.db_path)
            try:
                self.assertEqual(store.list_runs()[0]["site_id"], cfg.site_id)
                case = store.add_case(payload["run_id"], "Confirmed coverage issue", "Relocate antenna")
                self.assertEqual(store.list_cases()[0]["case_id"], case)
            finally:
                store.close()

    def test_invalid_stdin_is_rejected(self):
        with patch("sys.stdin", io.StringIO("[]")):
            with self.assertRaisesRegex(ValueError, "JSON object"):
                core.VeilbreakerApplication.load_metrics_file("-")

    def test_invalid_configuration_cannot_enable_hardware_by_truthiness(self):
        for invalid in ({"cellular": {"enabled": "false"}}, {"sdr": {"timeout_s": float("inf")}},
                        {"data_dir": ""}, {"baseline_run_count": -1}, {"iperf3_port": 70000}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                core.AppConfig.from_dict(invalid)

    def test_missing_explicit_config_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.stderr", io.StringIO()) as output:
                self.assertEqual(main(["--config", str(Path(folder) / "missing.json"), "history"]), 2)
            self.assertIn("Configuration not found", output.getvalue())

    def test_legacy_data_is_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            legacy = Path(folder) / ".veilbreaker"
            legacy.mkdir()
            (legacy / "veilbreaker.db").touch()
            with patch.object(Path, "home", return_value=Path(folder)), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(paths.data_root(), legacy)

    def test_platform_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(Path, "home", return_value=Path(folder)), patch.dict(os.environ, {"LOCALAPPDATA": folder}, clear=True), patch("sys.platform", "win32"):
                self.assertEqual(paths.data_root(), Path(folder) / "Veilbreaker")
            with patch.object(Path, "home", return_value=Path(folder)), patch.dict(os.environ, {"XDG_DATA_HOME": folder}, clear=True), patch("sys.platform", "linux"):
                self.assertEqual(paths.data_root(), Path(folder) / "veilbreaker")

    def test_comparison_distinguishes_missing_and_zero(self):
        before = {"run_id": "before", "metrics_json": json.dumps({"latency_ms": 100, "sinr": 0, "dns_success": True})}
        after = {"run_id": "after", "metrics_json": json.dumps({"latency_ms": 30, "rsrp": -95, "dns_success": False})}
        result = compare_runs(before, after)
        self.assertIn("Δ -70", result)
        self.assertIn("not collected (previously 0)", result)
        self.assertIn("dns_success: True → False", result)

    def test_ping_uses_native_platform_flags(self):
        for system, expected in [("Windows", "-f"), ("Linux", "-M")]:
            with self.subTest(system=system), patch.object(core.platform, "system", return_value=system), patch.object(core, "command_exists", return_value=True), patch.object(core, "run_command", return_value=core.CommandResult([], 1, "", "", 0)) as run:
                core.ping_host("192.0.2.1", do_not_fragment=True)
                self.assertIn(expected, run.call_args.args[0])

    def test_iperf_measures_directions_separately(self):
        def response(argv, timeout):
            received = 80_000_000 if "-R" in argv else 20_000_000
            body = json.dumps({"end": {"sum_received": {"bits_per_second": received}, "sum_sent": {"bits_per_second": 999_000_000}}})
            return core.CommandResult(argv, 0, body, "", 0)
        cfg = core.AppConfig(iperf3_server="192.0.2.1")
        with patch.object(core, "command_exists", return_value=True), patch.object(core, "run_command", side_effect=response) as run:
            metrics, notes = core.ActiveTestExecutor(cfg).iperf3()
        self.assertEqual(run.call_count, 2)
        self.assertEqual(metrics["upload_mbps"], 20)
        self.assertEqual(metrics["download_mbps"], 80)
        self.assertEqual(notes, [])

    def test_iperf_does_not_invent_missing_download(self):
        responses = [core.CommandResult([], 0, '{"end":{"sum_received":{"bits_per_second":20000000}}}', "", 0),
                     core.CommandResult([], 1, "", "reverse unsupported", 0)]
        with patch.object(core, "command_exists", return_value=True), patch.object(core, "run_command", side_effect=responses):
            metrics, notes = core.ActiveTestExecutor(core.AppConfig(iperf3_server="192.0.2.1")).iperf3()
        self.assertNotIn("download_mbps", metrics)
        self.assertIn("reverse unsupported", notes[0])


if __name__ == "__main__":
    unittest.main()
