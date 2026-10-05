"""One isolated worker process per desktop task; SQLite connections stay local."""
import json
import os
from pathlib import Path
import traceback
from . import core


DEMO_METRICS = {
    "rsrp": -112, "rsrq": -12, "sinr": 16, "download_mbps": 5,
    "upload_mbps": 3, "latency_ms": 120, "gateway_latency_ms": 2,
    "packet_loss_pct": 2, "gateway_reachable": True,
    "internet_reachable": True, "dns_success": True,
}


def demo_payload():
    report = core.ProfessionalVeilbreakerEngine().analyze(DEMO_METRICS)
    return {"report": report.to_dict(), "metrics": DEMO_METRICS,
            "notes": ["Synthetic demonstration. No hardware was contacted and no run was saved."],
            "run_id": "demo", "evidence_zip": None, "site_id": "Demonstration"}


def execute(request, progress=None):
    cfg = core.AppConfig.from_dict(request["config"])
    action = request["action"]
    if action == "survey":
        from .survey import execute_survey
        return execute_survey(cfg, request["name"], request["steps"], progress, manual=request.get("manual", False))
    if action == "survey_resume":
        from .survey import resume_survey
        return resume_survey(cfg, request["survey_path"], progress)
    if action == "recover":
        from .recovery import recover_runs
        result = recover_runs(cfg)
        return {"text": json.dumps(result, indent=2), "returncode": bool(result["notes"])}
    if action == "verify":
        from .evidence import verify_bundle
        result = verify_bundle(request["input"])
        return {"text": json.dumps(result, indent=2, ensure_ascii=False),
                "returncode": 0 if result["status"] == "verified" else 1}
    if action == "doctor":
        rc, output = core.doctor(cfg)
        return {"text": output, "returncode": rc}
    if action == "ports":
        return {"text": json.dumps([core.asdict(p) for p in core.list_serial_ports()], indent=2)}
    if action == "hackrf_info":
        metrics, notes = core.HackRFCollector(cfg.sdr, cfg.artifacts_dir / "discovery").info()
        return {"text": json.dumps({"metrics": metrics, "notes": notes}, indent=2), "returncode": 0 if metrics.get("sdr_present") else 1}
    if action == "drivers":
        return {"text": json.dumps(core.CellularModemCollector.compatibility_matrix(), indent=2)}
    if action == "selftest":
        rc, output = core.selftest()
        return {"text": output, "returncode": rc}
    if action not in {"run", "analyze"}:
        raise ValueError(f"Unknown task: {action}")
    app = core.VeilbreakerApplication(cfg, progress=progress)
    try:
        result = (app.analyze_file(request["input"]) if action == "analyze"
                  else app.run(**request.get("options", {})))
        return {"report": result.report.to_dict(), "metrics": result.metrics,
                "notes": result.notes, "run_id": result.run_id,
                "site_id": cfg.site_id, "evidence_zip": str(result.evidence_zip),
                "sweeps": [core.asdict(s) for s in result.sweep_summaries], "collection": result.collection}
    finally:
        app.close()


def worker_main(args):
    if len(args) != 2:
        return 2
    if os.name != "nt":
        os.setsid()  # Give cancellation its own process group, including collector children.
    source, destination = map(Path, args)
    try:
        payload = {"ok": True, "result": execute(json.loads(source.read_text(encoding="utf-8")),
                    progress=lambda event: print(json.dumps(event, ensure_ascii=True), flush=True))}
        rc = 0
    except Exception as exc:
        payload = {"ok": False, "error": str(exc), "detail": traceback.format_exc()}
        rc = 1
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, default=str), encoding="utf-8")
    temporary.replace(destination)
    return rc
