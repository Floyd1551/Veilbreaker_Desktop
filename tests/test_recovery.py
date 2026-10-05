import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from veilbreaker import core
from veilbreaker.acquisition import Acquisition
from veilbreaker.evidence import verify_bundle
from veilbreaker.recovery import atomic_json, checkpoint_writer, process_alive, recover_runs


class RecoveryTests(unittest.TestCase):
    def test_checkpoint_retries_transient_windows_file_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "checkpoint.json"
            original = Path.replace
            attempts = []
            def replace(path, destination):
                attempts.append(1)
                if len(attempts) < 3:
                    raise PermissionError("Temporary reader lock")
                return original(path, destination)
            with patch.object(Path, "replace", replace), patch("veilbreaker.recovery.time.sleep"):
                atomic_json(target, {"complete": True})
            self.assertEqual(len(attempts), 3)
            self.assertTrue(json.loads(target.read_text())["complete"])

    def test_expected_measurements_keep_false_and_zero(self):
        tracker = Acquisition()
        tracker.collect("radio", lambda: ({"modem_registered": False, "rssi": 0}, []),
                        expected=(("modem_registered",), ("rsrp", "rssi"), ("sinr",)))
        self.assertEqual(tracker.records[0]["missing_measurements"], ["sinr"])
        self.assertEqual(tracker.to_dict()["status"], "partial")

    def test_current_process_is_alive(self):
        self.assertTrue(process_alive(os.getpid()))

    def test_running_worker_is_not_recovered(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            directory = cfg.artifacts_dir / "active"
            directory.mkdir(parents=True)
            tracker = Acquisition(checkpoint=checkpoint_writer(directory / "recovery.json", cfg, "active"))
            tracker.collect("host", lambda: ({"host_os": "test"}, []))
            result = recover_runs(cfg)
            self.assertEqual(result["recovered"], [])
            self.assertIn("still active", result["notes"][0])

    def test_killed_process_recovers_checkpoint_once_without_hardware(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            directory = cfg.artifacts_dir / "cancelled-test"
            directory.mkdir(parents=True)
            checkpoint = directory / "recovery.json"
            script = '''
import sys, time
from pathlib import Path
from veilbreaker import core
from veilbreaker.acquisition import Acquisition
from veilbreaker.recovery import checkpoint_writer
cfg=core.AppConfig(data_dir=sys.argv[1])
t=Acquisition(checkpoint=checkpoint_writer(Path(sys.argv[2]),cfg,'cancelled-test'))
t.collect('host',lambda: ({'latency_ms': 15},[]))
t.collect('slow-device',lambda: time.sleep(60))
'''
            worker = subprocess.Popen([sys.executable, "-c", script, folder, str(checkpoint)])
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    try:
                        if checkpoint.exists() and json.loads(checkpoint.read_text(encoding="utf-8"))["active_collector"] == "slow-device":
                            break
                    except PermissionError:
                        # Windows can briefly deny reads while the worker replaces the file.
                        pass
                    time.sleep(0.02)
                else:
                    self.fail("Worker did not checkpoint")
            finally:
                worker.terminate()
                worker.wait(timeout=5)
            with patch.object(core.HackRFCollector, "collect", side_effect=AssertionError("Recovery must be offline")):
                result = recover_runs(cfg)
            self.assertEqual(len(result["recovered"]), 1)
            self.assertEqual(verify_bundle(result["recovered"][0]["evidence_zip"])["status"], "verified")
            collection = json.loads((directory / "collection.json").read_text())
            self.assertEqual(collection["status"], "interrupted")
            self.assertEqual(collection["metric_sources"]["latency_ms"], ["host"])
            self.assertEqual(recover_runs(cfg)["recovered"], [])

    def test_partial_sdr_csv_can_be_reopened_after_interruption(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            directory = cfg.artifacts_dir / "partial-sweep"
            directory.mkdir(parents=True)
            tracker = Acquisition(checkpoint=checkpoint_writer(directory / "recovery.json", cfg, "partial-sweep"))
            tracker.active = "hackrf"
            tracker.persist()
            (directory / "sweep.csv").write_text("date,time,2400000000,2404000000,1000000,4,-60,-40,-50,-65\n")
            atomic_json(directory / "sweep.capture.json", {"range": {"label": "wifi24", "min_mhz": 2400, "max_mhz": 2500}})
            with patch("veilbreaker.recovery.process_alive", return_value=False):
                result = recover_runs(cfg)
            self.assertEqual(len(result["recovered"]), 1)
            sweeps = json.loads((directory / "sdr_summaries.json").read_text())
            self.assertEqual(sweeps[0]["bins"], 4)
            self.assertEqual(json.loads((directory / "collection.json").read_text())["status"], "interrupted")

    def test_retry_rediscovery_creates_new_run_preserving_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = core.AppConfig(data_dir=folder)
            cfg.sdr.ranges = [core.SDRRange("wifi24", 2400, 2500)]
            csv = Path(folder) / "sample.csv"
            csv.write_text("d,t,2400000000,2402000000,1000000,2,-60,-40\n")
            summary = core.HackRFCollector.summarize("wifi24", cfg.sdr.ranges[0], core.HackRFCollector.parse_sweep_csv(csv), csv)
            app = core.VeilbreakerApplication(cfg)
            try:
                with patch.object(app, "collect_passive", return_value=({}, [])), patch.object(core.HackRFCollector, "collect", side_effect=[({}, ["disconnected"], []), ({"sdr_wifi24_median_db": -50}, [], [summary])]) as collect:
                    failed = app.run(sdr=True)
                    retried = app.run(sdr=True)
                self.assertEqual(collect.call_count, 2)
                self.assertNotEqual(failed.run_id, retried.run_id)
                self.assertEqual(failed.collection["status"], "partial")
                self.assertEqual(retried.collection["status"], "complete")
                self.assertEqual(len(app.store.list_runs()), 2)
            finally:
                app.close()
