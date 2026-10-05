"""Draft queue editing and saved-session filtering without acquisition."""
from copy import deepcopy
from .survey import validate_steps


def rename_point(steps, index, name):
    if not 0 <= index < len(steps):
        raise ValueError("Select a queued point")
    result = deepcopy(steps)
    result[index]["label"] = name.strip()
    validate_steps(result)
    if any(i != index and s["label"] == result[index]["label"] for i,s in enumerate(result)):
        raise ValueError("Use a unique point label so repeat visits can be compared")
    return result


def move_point(steps, index, direction):
    if direction not in (-1,1) or not 0 <= index < len(steps) or not 0 <= index+direction < len(steps):
        raise ValueError("Point cannot move in that direction")
    result = deepcopy(steps)
    result[index],result[index+direction] = result[index+direction],result[index]
    return result


def session_matches(session, query="", status="All states"):
    if status != "All states" and session["status"] != status:
        return False
    text = " ".join(str(session.get(k,"")) for k in ("name","site_id","survey_id","created_utc","scenario"))
    text += " " + " ".join(str(s.get("label","")) for s in session["steps"])
    return query.strip().casefold() in text.casefold()
