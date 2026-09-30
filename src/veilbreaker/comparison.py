"""Describe measured changes without turning every delta into a diagnosis."""
import json
import math


def compare_runs(before, after):
    left, right = json.loads(before["metrics_json"]), json.loads(after["metrics_json"])
    lines = [f"Before: {before['run_id']}", f"After:  {after['run_id']}",
             "Deltas are after minus before; missing values are not zero.\n"]
    for key in sorted(set(left) | set(right)):
        if key not in left:
            lines.append(f"{key}: added {right[key]}")
        elif key not in right:
            lines.append(f"{key}: not collected (previously {left[key]})")
        elif left[key] != right[key]:
            a, b = left[key], right[key]
            delta = ""
            if all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (a, b)):
                delta = f" (Δ {b - a:+.3g})"
            lines.append(f"{key}: {a} → {b}{delta}")
    if len(lines) == 3:
        lines.append("No metric changes.")
    return "\n".join(lines)
