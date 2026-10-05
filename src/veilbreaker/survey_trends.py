"""Comparable, gap-preserving survey observations across saved visits."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
from .survey_compare import compare_visits


def finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def build_trend(baseline, baseline_settings, visits, point, metric):
    matches = [s for s in baseline["steps"] if s["label"] == point]
    if len(matches) != 1:
        raise ValueError("Choose a unique point label in the baseline visit")
    base = matches[0]
    if not finite_number(base.get("metrics", {}).get(metric)):
        raise ValueError("Choose a numeric baseline measurement")
    rows, seen = [], set()
    for session, settings in sorted(visits, key=lambda v: (v[0]["created_utc"], v[0]["survey_id"])):
        if session["site_id"] != baseline["site_id"] or session["survey_id"] in seen:
            continue
        seen.add(session["survey_id"])
        selected = [s for s in session["steps"] if s["label"] == point]
        step = selected[0] if len(selected) == 1 else None
        observed = (step or {}).get("metrics", {}).get(metric)
        value = observed if finite_number(observed) else None
        notes, delta, eligible = "", None, False
        if session["survey_id"] == baseline["survey_id"]:
            eligible = base["status"] == "complete" and baseline_settings is not None
            notes = "Baseline" if eligible else "Baseline incomplete or settings unavailable"
            delta = 0 if eligible else None
        else:
            try:
                result = compare_visits(baseline, session, baseline_settings is not None and settings == baseline_settings)
                row = next(r for r in result["rows"] if r["point"] == point and r["metric"] == metric)
                delta, notes = row["delta"], row["notes"]
                eligible = delta is not None and value is not None
            except ValueError as exc:
                notes = str(exc)
        rows.append({"survey_id": session["survey_id"], "name": session["name"], "created_utc": session["created_utc"],
                     "run_id": (step or {}).get("run_id"), "collection": (step or {}).get("status", "absent or ambiguous"),
                     "value": value, "delta": delta, "comparable": eligible, "notes": notes,
                     "point_notes": (step or {}).get("notes", "")})
    values = [r["value"] for r in rows if r["comparable"]]
    fingerprint = hashlib.sha256(json.dumps(baseline_settings, sort_keys=True).encode("utf-8")).hexdigest() if baseline_settings is not None else None
    return {"schema_version": 1, "site_id": baseline["site_id"], "baseline_id": baseline["survey_id"],
            "point": point, "metric": metric, "settings_fingerprint": fingerprint,
            "interpretation": "Visits are ordered by survey creation time. Changes are relative to the selected baseline, not improvement scores. Only comparable observations contribute to statistics and the plot; gaps are not interpolated. Matching settings do not verify identical hardware, antennas or conditions.",
            "summary": {"visits": len(rows), "comparable": len(values), "excluded": len(rows)-len(values),
                        "minimum": min(values) if values else None, "median": statistics.median(values) if values else None,
                        "maximum": max(values) if values else None}, "rows": rows}


def trend_csv(result):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["UTC", "Visit", "Survey ID", "Run ID", "Point", "Metric", "Value", "Change from baseline", "Comparable", "Notes", "Point notes"])
    for r in result["rows"]:
        # JSON-quote text fields so spreadsheet software does not treat them as formulas.
        text = lambda value: json.dumps(value or "", ensure_ascii=False)
        writer.writerow([text(r["created_utc"]), text(r["name"]), text(r["survey_id"]), text(r["run_id"]), text(result["point"]), text(result["metric"]),
                         r["value"] if r["value"] is not None else "", r["delta"] if r["delta"] is not None else "", r["comparable"], text(r["notes"]), text(r["point_notes"])])
    return stream.getvalue()


def saved_trend(config, baseline_path, point, metric):
    from .survey import read_session, list_sessions
    from .survey_compare import load_settings_snapshot
    baseline = read_session(config, baseline_path)
    visits = [(s,load_settings_snapshot(p)) for p,s in list_sessions(config) if s["site_id"] == baseline["site_id"]]
    return build_trend(baseline,load_settings_snapshot(baseline_path),visits,point,metric)
