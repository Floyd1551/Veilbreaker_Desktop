import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from veilbreaker import core
from veilbreaker.acquisition import Acquisition
from veilbreaker.cli import main
from veilbreaker.evidence import verify_bundle


class AcquisitionTests(unittest.TestCase):
    def test_optional_absence_and_negative_measurements_are_valid(self):
        events = []
        tracker = Acquisition(events.append)
        tracker.collect("gps", lambda: ({}, []), required=False)
        tracker.collect("network", lambda: ({"internet_reachable": False, "download_mbps": 0}, []))
        self.assertEqual(tracker.to_dict()["status"], "complete")
        self.assertEqual([e["status"] for e in events], ["running", "no_data", "running", "collected"])
        self.assertGreaterEqual(tracker.records[0]["duration_s"], 0)

    def test_failure_is_recorded_and_other_evidence_survives(self):
        tracker = Acquisition()
        tracker.collect("host", lambda: ({"host_os": "test"}, []))
        def fail():
            raise OSError("device disconnected")
        self.assertEqual(tracker.collect("hardware", fail)[0], {})
        self.assertEqual(tracker.to_dict()["status"], "partial")
        self.assertEqual(tracker.records[-1]["status"], "error")
        self.assertIn("device disconnected", tracker.records[-1]["notes"][0])
        self.assertEqual(tracker.sources["host_os"], ["host"])

    def test_overrides_preserve_source_order(self):
        tracker = Acquisition()
        tracker.collect("network", lambda: ({"latency_ms": 10}, []))
        tracker.collect("imported_metrics", lambda: ({"latency_ms": 20}, []))
        self.assertEqual(tracker.sources["latency_ms"], ["network", "imported_metrics"])

    def test_requested_sdr_without_sweeps_is_partial_and_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            app = core.VeilbreakerApplication(core.AppConfig(data_dir=folder))
            self.addCleanup(app.close)
            with patch.object(app, "collect_passive", return_value=({"host_os": "test"}, [])), patch.object(core.HackRFCollector, "collect", return_value=({"sdr_present": True}, ["Sweep failed"], [])):
                result = app.run(sdr=True)
            self.assertEqual(result.collection["status"], "partial")
            self.assertIn("Partial collection", result.report.summary[-1])
            with zipfile.ZipFile(result.evidence_zip) as archive:
                self.assertEqual(json.loads(archive.read("collection.json")), result.collection)
            self.assertEqual(verify_bundle(result.evidence_zip)["status"], "verified")
            app.close()

    def test_throughput_missing_reverse_is_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            app = core.VeilbreakerApplication(core.AppConfig(data_dir=folder))
            try:
                with patch.object(app, "collect_passive", return_value=({}, [])), patch.object(core.ActiveTestExecutor, "iperf3", return_value=({"upload_mbps": 8}, [])):
                    result = app.run(throughput=True)
                self.assertEqual(result.collection["status"], "partial")
                self.assertEqual(result.metrics["upload_mbps"], 8)
            finally:
                app.close()

    def test_analysis_import_provenance_without_hardware(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "metrics.json"
            source.write_text('{"latency_ms": 20}', encoding="utf-8")
            app = core.VeilbreakerApplication(core.AppConfig(data_dir=folder))
            try:
                with patch.object(app, "collect_passive", side_effect=AssertionError("must stay offline")):
                    result = app.analyze_file(str(source))
                self.assertEqual(result.collection["metric_sources"], {"latency_ms": ["imported_metrics"]})
            finally:
                app.close()

    def test_cli_partial_exit_preserves_json_report(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            with patch.object(core, "load_config", return_value=cfg), patch.object(core.VeilbreakerApplication, "collect_passive", return_value=({}, [])), patch.object(core.HackRFCollector, "collect", return_value=({}, ["No device"], [])), patch("sys.stdout", io.StringIO()) as output:
                self.assertEqual(main(["run", "--sdr", "--json"]), 3)
            self.assertIn("Partial collection", json.loads(output.getvalue())["summary"][-1])
