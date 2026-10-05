"""Portable survey plans, independent of settings, sessions and evidence."""
import json
from pathlib import Path
from .survey import validate_steps
from .recovery import atomic_json


def validate_template(value):
    if not isinstance(value, dict) or value.get("format") != "veilbreaker-survey-template" or type(value.get("version")) is not int or value["version"] != 1:
        raise ValueError("Choose a supported Veilbreaker survey template")
    name = value.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        raise ValueError("Template name must contain 1–100 characters")
    if type(value.get("manual")) is not bool:
        raise ValueError("Template pause mode must be a boolean")
    # Reconstruct the plan: never import session IDs, results or executable settings.
    steps = validate_steps(value.get("steps"))
    return {"format": "veilbreaker-survey-template", "version": 1,
            "name": name.strip(), "manual": value["manual"],
            "steps": [{"label": s["label"], "options": s["options"]} for s in steps]}


def save_template(path, name, steps, manual):
    value = validate_template({"format": "veilbreaker-survey-template", "version": 1,
                               "name": name, "steps": steps, "manual": manual})
    atomic_json(Path(path), value)
    return value


def load_template(path):
    with Path(path).open("rb") as stream:
        data = stream.read(128 * 1024 + 1)
    if len(data) > 128 * 1024:
        raise ValueError("Survey template exceeds 128 KiB")
    return validate_template(json.loads(data.decode("utf-8-sig")))
