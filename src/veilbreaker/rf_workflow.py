"""Bounded receive presets and conservative comparison of saved RF evidence."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics

PRESETS = {"2.4 GHz (2400–2500 MHz)": ("wifi24", 2400, 2500),
           "Sub-1 GHz (600–1000 MHz)": ("sub1g", 600, 1000),
           "5 GHz (5150–5850 MHz)": ("wifi5", 5150, 5850)}
BIN_WIDTHS = (100_000, 250_000, 500_000, 1_000_000)


def apply_preset(config, preset, sweeps=3, bin_width_hz=1_000_000, lna_gain_db=16, vga_gain_db=20):
    from .core import SDRRange
    if preset not in PRESETS or type(sweeps) is not int or not 1 <= sweeps <= 20:
        raise ValueError("Choose a known preset and 1–20 sweeps")
    if bin_width_hz not in BIN_WIDTHS or lna_gain_db not in range(0, 41, 8) or vga_gain_db not in range(0, 63, 2):
        raise ValueError("Invalid preset bin width or receiver gain")
    config.sdr.ranges = [SDRRange(*PRESETS[preset])]
    config.sdr.sweeps, config.sdr.bin_width_hz = sweeps, bin_width_hz
    config.sdr.lna_gain_db, config.sdr.vga_gain_db = lna_gain_db, vga_gain_db
    config.sdr.amp_enable = config.sdr.antenna_power = False
    config.satellite.command = None


def read_trace(summary):
    from .core import HackRFCollector
    groups = defaultdict(list)
    for sample in HackRFCollector.parse_sweep_csv(Path(summary["csv_path"])):
        if summary["min_mhz"] <= sample.hz / 1e6 < summary["max_mhz"]:
            groups[sample.hz / 1e6].append(sample.power_db)
    return [(hz, statistics.median(values), max(values)) for hz, values in sorted(groups.items())]


def compare_sweeps(before, after, before_serial=None, after_serial=None):
    """Reject unknown settings and mismatched bin grids instead of interpolating."""
    captures = []
    for summary in (before, after):
        path = Path(summary["csv_path"])
        try:
            capture = json.loads(path.with_suffix(".capture.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("Capture settings are unavailable; numeric comparison is not reliable.") from exc
        if capture.get("returncode") != 0:
            raise ValueError("An interrupted or unsuccessful capture cannot be compared numerically.")
        captures.append(capture)
    before_serial = captures[0].get("device_serial") or before_serial
    after_serial = captures[1].get("device_serial") or after_serial
    if not before_serial or not after_serial or before_serial != after_serial:
        raise ValueError("Comparison requires the same recorded HackRF serial number.")
    for key in ("min_mhz", "max_mhz", "bin_width_hz"):
        if before.get(key) != after.get(key):
            raise ValueError(f"Capture ranges or frequency resolution differ ({key}).")
    keys = ("bin_width_hz", "sweeps", "lna_gain_db", "vga_gain_db", "amp_enable", "antenna_power")
    for key in keys:
        values = [capture.get("settings", {}).get(key) for capture in captures]
        if values[0] is None or values[1] is None or values[0] != values[1]:
            raise ValueError(f"Capture settings differ or are unknown: {key}.")
    traces = [read_trace(summary) for summary in (before, after)]
    if not traces[0] or [p[0] for p in traces[0]] != [p[0] for p in traces[1]]:
        raise ValueError("Frequency bins are missing or do not align; repeat both captures with the same preset.")
    width = before["bin_width_hz"] / 1e6
    frequencies = [p[0] for p in traces[0]]
    if width <= 0 or frequencies[0] - before["min_mhz"] > width or before["max_mhz"] - frequencies[-1] > width or any(b - a > width * 1.01 for a, b in zip(frequencies, frequencies[1:])):
        raise ValueError("The captures do not cover the full requested range; repeat acquisition.")
    rows = [{"frequency_mhz": a[0], "before_median_db": b[1], "after_median_db": a[1],
             "delta_db": round(a[1] - b[1], 4)} for b, a in zip(*traces)]
    sources = []
    for summary, capture in zip((before, after), captures):
        path = Path(summary["csv_path"])
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        sources.append({"csv_path": str(path), "sha256": digest, "timestamp": capture.get("timestamp"),
                        "settings": capture["settings"]})
    return {"schema_version": 1, "before": sources[0], "after": sources[1],
            "device_serial": before_serial, "bin_count": len(rows),
            "median_delta_db": round(statistics.median(r["delta_db"] for r in rows), 4),
            "largest_increase": max(rows, key=lambda r: r["delta_db"]), "rows": rows,
            "interpretation": "After minus before, relative uncalibrated dB. Keep antenna, cable and placement unchanged unless that change is the experiment. Differences do not identify a protocol or prove interference."}
