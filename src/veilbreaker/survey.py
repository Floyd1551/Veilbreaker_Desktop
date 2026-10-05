"""Sequential site-survey sessions with independent evidence for every run."""
import csv
from dataclasses import asdict
from contextlib import contextmanager
import io
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import tempfile
import uuid
import zipfile

from . import core
from .evidence import write_manifest
from .recovery import atomic_json, process_alive

FLAGS = {"active", "guided", "cellular", "starlink", "sdr", "throughput"}


def validate_steps(steps):
    if not isinstance(steps, list) or not 1 <= len(steps) <= 20:
        raise ValueError("A survey requires 1–20 test steps")
    clean = []
    for index, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            raise ValueError("Each step must be an object")
        label = step.get("label", f"Test {index}")
        options = step.get("options", {})
        if not isinstance(label, str) or not label.strip() or len(label) > 100:
            raise ValueError("Test labels must contain 1–100 characters")
        if not isinstance(options, dict) or set(options) - FLAGS or any(type(v) is not bool for v in options.values()):
            raise ValueError("Test options must be supported boolean diagnostic flags")
        options = {flag: options.get(flag, False) for flag in sorted(FLAGS)}
        options["active"] = options["active"] or options["guided"]
        notes = step.get("notes", "")
        if not isinstance(notes, str) or len(notes) > 2000:
            raise ValueError("Point notes must be text up to 2000 characters")
        clean.append({"label": label.strip(), "options": options, "notes": notes})
    return clean


def execute_survey(config, name, steps, progress=None, manual=False):
    if type(manual) is not bool:
        raise ValueError("Manual progression must be a boolean")
    steps = validate_steps(steps)
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        raise ValueError("Name the survey using 1–100 characters")
    if any(s["options"]["throughput"] for s in steps) and not config.iperf3_server:
        raise ValueError("Configure an iperf3 server before adding throughput tests")
    survey_id = "survey-" + uuid.uuid4().hex[:12]
    folder = config.root / "surveys"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{survey_id}.json"
    session = {"schema_version": 1, "survey_id": survey_id, "name": name.strip(), "site_id": config.site_id,
               "scenario": config.scenario, "created_utc": core.utcnow_iso(), "pid": os.getpid(),
               "status": "running", "manual": manual, "sdr_settings": asdict(config.sdr), "steps": []}
    for index, step in enumerate(steps, 1):
        session["steps"].append({**step, "run_id": f"{survey_id}-{index:02d}", "status": "planned"})
    with session_lock(path):
        (path.parent / "settings").mkdir(exist_ok=True)
        atomic_json(path.parent / "settings" / path.name, config.to_dict())
        atomic_json(path, session)
        return _run_session(config, path, session, progress)


@contextmanager
def session_lock(path):
    """OS-owned lock is released even if a survey worker is killed."""
    with Path(path).with_suffix(".lock").open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError("This survey is already being modified by another worker") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def resume_survey(config, path, progress=None):
    path = _session_path(config, path)
    with session_lock(path):
        session = _editable_session(config, path)
        if not any(step["status"] in ("planned", "not_run") for step in session["steps"]):
            raise ValueError("No unrun tests remain. Completed, failed and interrupted tests are not repeated.")
        snapshot = path.parent / "settings" / path.name
        if not snapshot.exists():
            raise ValueError("This older session has no settings snapshot. Start a new survey to continue safely.")
        cfg = core.AppConfig.from_dict(json.loads(snapshot.read_text(encoding="utf-8")))
        cfg.data_dir = str(config.root)
        session["pid"] = os.getpid()
        session["status"] = "running"
        atomic_json(path, session)
        return _run_session(cfg, path, session, progress)


def _session_path(config, path):
    path = Path(path).resolve()
    if path.parent != (config.root / "surveys").resolve() or path.suffix != ".json" or path.name.endswith(".config.json"):
        raise ValueError("Choose a survey journal from this data directory")
    return path


def _editable_session(config, path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    observed = read_session(config, path)
    if observed["status"] == "running":
        raise ValueError("Wait for the current test to finish before changing this survey")
    for original, current in zip(raw["steps"], observed["steps"]):
        original["status"] = current["status"]
    raw["status"] = observed["status"]
    return raw


def update_point_notes(config, path, index, notes):
    if not isinstance(notes, str) or len(notes) > 2000:
        raise ValueError("Point notes must be text up to 2000 characters")
    path = _session_path(config, path)
    with session_lock(path):
        session = _editable_session(config, path)
        if type(index) is not int or not 0 <= index < len(session["steps"]):
            raise ValueError("Select a survey point")
        step = session["steps"][index]
        step.setdefault("note_history", []).append({"timestamp": core.utcnow_iso(), "previous": step.get("notes", ""), "updated": notes})
        step["notes"] = notes
        atomic_json(path, session)
    return read_session(config, path)


def _run_session(config, path, session, progress):
    for index, step in enumerate(session["steps"], 1):
        if step["status"] not in ("planned", "not_run"):
            continue
        step["status"] = "running"
        atomic_json(path, session)
        def notify(event):
            if progress:
                progress({**event, "source": f"Test {index}/{len(session['steps'])} · {step['label']} · {event['source']}"})
        notify({"event": "collection", "source": "starting", "status": "running"})
        cfg = core.AppConfig.from_dict(config.to_dict())
        cfg.cellular.enabled = step["options"]["cellular"]
        cfg.starlink.enabled = step["options"]["starlink"]
        cfg.sdr.enabled = step["options"]["sdr"]
        app = core.VeilbreakerApplication(cfg, progress=notify)
        try:
            result = app.run(**step["options"], run_id=step["run_id"], note=f"{session['name']} / {step['label']} — {step.get('notes', '')}")
            step["status"] = result.collection.get("status", "complete")
        except Exception as exc:
            step["status"] = "failed"
            step["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            app.close()
        atomic_json(path, session)
        if session.get("manual"):
            break
    pending = any(s["status"] in ("planned", "not_run") for s in session["steps"])
    session["status"] = "paused" if pending else ("complete" if all(s["status"] == "complete" for s in session["steps"]) else "partial")
    if not pending:
        session["finished_utc"] = core.utcnow_iso()
    atomic_json(path, session)
    bundle = export_session(config, path)
    return {"survey": read_session(config, path), "survey_path": str(path), "evidence_zip": str(bundle)}


def read_session(config, path):
    session = json.loads(Path(path).read_text(encoding="utf-8"))
    if session.get("schema_version") != 1:
        raise ValueError("Unsupported survey format")
    stopped = session["status"] == "running" and not process_alive(int(session["pid"]))
    if stopped:
        session["status"] = "interrupted"
    store = core.VeilbreakerStore(config.db_path)
    try:
        for step in session["steps"]:
            row = store.get_run(step["run_id"])
            step["metrics"] = {}
            if row:
                step["metrics"] = json.loads(row["metrics_json"])
                step["assessment"] = json.loads(row["report_json"])["status"]
                collection_file = Path(row["artifact_dir"]) / "collection.json"
                if collection_file.exists():
                    step["status"] = json.loads(collection_file.read_text(encoding="utf-8"))["status"]
                step["evidence_zip"] = str(config.reports_dir / f"{step['run_id']}_evidence.zip")
            elif stopped and step["status"] == "running":
                step["status"] = "interrupted"
            elif stopped and step["status"] == "planned":
                step["status"] = "not_run"
    finally:
        store.close()
    values = {}
    for step in session["steps"]:
        for key, value in step["metrics"].items():
            if type(value) in (int, float) and math.isfinite(value):
                values.setdefault(key, []).append(value)
    session["numeric_summary"] = {key: {"observed": len(v), "minimum": min(v), "median": statistics.median(v), "maximum": max(v)}
                                  for key, v in sorted(values.items())}
    return session


def list_sessions(config):
    sessions = []
    for path in sorted((config.root / "surveys").glob("survey-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            session = read_session(config, path)
            sessions.append((path, session))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sessions


def export_session(config, path, destination=None):
    session = read_session(config, path)
    target = Path(destination) if destination else config.reports_dir / f"{session['survey_id']}_survey.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="veilbreaker-survey-") as temporary:
        folder = Path(temporary)
        keys = sorted({key for step in session["steps"] for key in step["metrics"]})
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(["Test", "Point notes", "Run", "Collection", *[("'" + k if k.lstrip().startswith(("=", "+", "-", "@")) else k) for k in keys]])
        for step in session["steps"]:
            # JSON encoding keeps booleans/objects explicit and avoids interpreting metric strings as formulas.
            writer.writerow([json.dumps(step["label"], ensure_ascii=False), json.dumps(step.get("notes", ""), ensure_ascii=False), step["run_id"], step["status"],
                             *[json.dumps(step["metrics"][k], ensure_ascii=False) if k in step["metrics"] else "" for k in keys]])
            evidence = Path(step["evidence_zip"]) if step.get("evidence_zip") else None
            if evidence and evidence.exists():
                shutil.copyfile(evidence, folder / evidence.name)
            elif evidence:
                step["export_note"] = "Original evidence ZIP is missing"
        (folder / "comparison.csv").write_text(stream.getvalue(), encoding="utf-8-sig")
        atomic_json(folder / "survey.json", session)
        (folder / "README.txt").write_text("Each step retains its original evidence. Point notes are annotations; edits retain a history in survey.json and do not rewrite original run evidence. Missing values are blank, never zero. Compare equivalent tests and receiver settings; differing test flags or antenna placement can change results. This session workflow adds no GPS or mapping interface. Recovered/partial measurements remain explicitly labeled.\n", encoding="utf-8")
        write_manifest(folder, {"survey_id": session["survey_id"], "site_id": session["site_id"], "status": session["status"]})
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in folder.iterdir():
                archive.write(item, item.name)
    return target
