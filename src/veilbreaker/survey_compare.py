"""Read-only comparisons of repeat survey visits."""
import json
import math
from pathlib import Path
from .survey import read_session


def compare_visits(before, after, settings_match=False):
    if before["survey_id"] == after["survey_id"]:
        raise ValueError("Choose two different survey visits")
    if before["site_id"] != after["site_id"]:
        raise ValueError("Survey visits must belong to the same site")
    indexed = []
    for session in (before, after):
        points = {}
        for step in session["steps"]:
            name = step["label"]
            if name in points:
                raise ValueError("Point labels must be unique within each visit to match them reliably")
            points[name] = step
        indexed.append(points)
    rows = []
    for label in dict.fromkeys([*indexed[0], *indexed[1]]):
        a, b = indexed[0].get(label), indexed[1].get(label)
        reasons = []
        if a is None or b is None:
            reasons.append("Point absent from one visit")
        else:
            if a["status"] != "complete" or b["status"] != "complete":
                reasons.append("Incomplete collection")
            if a.get("options") != b.get("options"):
                reasons.append("Test selections differ")
        if before.get("scenario") != after.get("scenario"):
            reasons.append("Scenarios differ")
        if not settings_match:
            reasons.append("Original settings differ or are unavailable")
        am, bm = (a or {}).get("metrics", {}), (b or {}).get("metrics", {})
        for key in sorted(am.keys() | bm.keys()) or ["(no measurements)"]:
            av, bv = am.get(key), bm.get(key)
            numeric = all(type(v) in (int, float) and math.isfinite(v) for v in (av, bv))
            delta = bv - av if numeric and not reasons else None
            if delta is not None and not math.isfinite(delta):
                delta = None
            row_reasons = list(reasons)
            if key not in am or key not in bm:
                row_reasons.append("Measurement absent")
            elif not numeric:
                row_reasons.append("Non-numeric measurement")
            rows.append({"point": label, "metric": key, "baseline": av, "current": bv,
                         "delta": delta, "notes": "; ".join(row_reasons),
                         "baseline_run": (a or {}).get("run_id"), "current_run": (b or {}).get("run_id")})
    return {"schema_version": 1, "site_id": before["site_id"],
            "baseline": {k: before.get(k) for k in ("survey_id", "name", "created_utc", "status")},
            "current": {k: after.get(k) for k in ("survey_id", "name", "created_utc", "status")},
            "settings_match": settings_match,
            "interpretation": "Delta is current minus baseline, not an improvement score. Matching settings do not establish identical antennas, devices or environmental conditions. Use the spectrum comparison tool for RF evidence.",
            "rows": rows}


def load_settings_snapshot(path):
    path = Path(path)
    try:
        value = json.loads((path.parent / "settings" / path.name).read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not value:
            return None
        value.pop("data_dir", None)
        return value or None
    except (OSError, ValueError):
        return None


def compare_saved_visits(config, baseline_path, current_path):
    before = load_settings_snapshot(baseline_path)
    after = load_settings_snapshot(current_path)
    return compare_visits(read_session(config, baseline_path), read_session(config, current_path),
                          before is not None and before == after)
