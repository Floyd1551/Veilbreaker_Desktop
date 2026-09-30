"""Per-user storage with compatibility for the recovered 0.9.x layout."""
import os
import sys
from pathlib import Path


def data_root() -> Path:
    if os.environ.get("VEILBREAKER_DATA_DIR"):
        return Path(os.environ["VEILBREAKER_DATA_DIR"]).expanduser().resolve()
    legacy = Path.home() / ".veilbreaker"
    if (legacy / "config.json").exists() or (legacy / "veilbreaker.db").exists():
        return legacy
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "Veilbreaker"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "veilbreaker"
