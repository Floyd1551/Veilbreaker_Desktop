"""Atomic checkpoints for interrupted acquisitions; never resume active traffic."""
import json
import os
import time
from pathlib import Path


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    for attempt in range(8):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(min(0.025 * 2 ** attempt, 0.2))


def process_alive(pid):
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() != 87  # Access denied is not evidence of death.
        try:
            code = wintypes.DWORD()
            return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def checkpoint_writer(path, config, run_id):
    def save(tracker):
        atomic_json(path, {"schema_version": 1, "run_id": run_id, "site_id": config.site_id,
                          "scenario": config.scenario, "pid": os.getpid(), "state": "running",
                          "active_collector": tracker.active, "metrics": tracker.metrics,
                          "collection": tracker.to_dict()})
    return save


def recover_runs(config):
    from . import core
    recovered, skipped = [], []
    app = core.VeilbreakerApplication(config)
    try:
        for checkpoint in sorted(config.artifacts_dir.glob("*/recovery.json")):
            try:
                state = json.loads(checkpoint.read_text(encoding="utf-8"))
                run_id = checkpoint.parent.name
                if state.get("state") != "running" or app.store.get_run(run_id):
                    continue
                if state.get("schema_version") != 1 or state.get("run_id") != run_id:
                    raise ValueError("Unsupported or mismatched checkpoint")
                if process_alive(int(state["pid"])):
                    skipped.append(f"{run_id}: worker still active; left untouched")
                    continue
                collection = state["collection"]
                collection["status"] = "interrupted"
                active = state.get("active_collector") or "finalization"
                collection["collectors"].append({"source": active, "required": True, "status": "interrupted",
                    "duration_s": 0, "metric_keys": [], "missing_measurements": ["Acquisition did not finish"],
                    "notes": ["Worker stopped before completion; recovered data may be incomplete."]})
                sweeps = []
                notes = ["Recovered interrupted acquisition. No hardware was contacted or traffic resumed."]
                for record in collection["collectors"]:
                    notes.extend(f"{record['source']}: {n}" for n in record["notes"])
                for metadata in checkpoint.parent.glob("*.capture.json"):
                    try:
                        capture = json.loads(metadata.read_text(encoding="utf-8"))
                        csv_path = metadata.with_name(metadata.name.replace(".capture.json", ".csv"))
                        r = core.SDRRange(**capture["range"])
                        bins = [b for b in core.HackRFCollector.parse_sweep_csv(csv_path)
                                if r.min_mhz * 1e6 <= b.hz < r.max_mhz * 1e6]
                        sweeps.append(core.HackRFCollector.summarize(r.label, r, bins, csv_path))
                    except (OSError, ValueError, KeyError, TypeError) as exc:
                        notes.append(f"Could not reconstruct {metadata.name}: {exc}")
                report = core.ProfessionalVeilbreakerEngine(core.profile_for_scenario(state["scenario"])).analyze(state["metrics"])
                report.summary.insert(0, "INTERRUPTED ACQUISITION: recovered measurements are incomplete. Repeat collection after resolving the interruption.")
                recovered_config = core.AppConfig.from_dict(config.to_dict())
                recovered_config.site_id, recovered_config.scenario = state["site_id"], state["scenario"]
                state["state"] = "recovered"
                # Keep the checkpoint pending until both pack and database are durable.
                atomic_json(checkpoint.parent / "collection.json", collection)
                pack = core.write_evidence_pack(recovered_config, run_id, state["metrics"], report, notes, sweeps, collection)
                app.store.save_run(run_id, state["site_id"], state["scenario"], state["metrics"], report,
                                   artifact_dir=str(checkpoint.parent), note="Recovered interrupted acquisition")
                atomic_json(checkpoint, state)
                recovered.append({"run_id": run_id, "evidence_zip": str(pack)})
            except (OSError, ValueError, KeyError, TypeError) as exc:
                skipped.append(f"{checkpoint.parent.name}: {exc}")
    finally:
        app.close()
    return {"recovered": recovered, "notes": skipped}
