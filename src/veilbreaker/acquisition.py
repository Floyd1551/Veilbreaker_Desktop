"""Collection outcomes are separate from conclusions about network health."""
from datetime import datetime, timezone
import time


class Acquisition:
    def __init__(self, progress=None, checkpoint=None):
        self.progress = progress
        self.checkpoint = checkpoint
        self.metrics = {}
        self.active = None
        self.records = []
        self.sources = {}

    def notify(self, source, status):
        if self.progress:
            self.progress({"event": "collection", "source": source, "status": status})

    def collect(self, source, operation, *, required=True, complete=None, expected=()):
        self.active = source
        self.persist()
        self.notify(source, "running")
        started = datetime.now(timezone.utc).isoformat()
        clock = time.monotonic()
        try:
            result = operation()
            metrics, notes = result[:2]
            missing = [" / ".join(group) for group in expected if not any(metrics.get(key) is not None for key in group)]
            status = "collected" if metrics else "no_data"
            if missing:
                status = "partial" if metrics else "no_data"
            if complete is not None and not complete(result):
                status = "partial" if metrics else "no_data"
        except Exception as exc:
            metrics, notes = {}, [f"{type(exc).__name__}: {exc}"]
            result = (metrics, notes)
            status = "error"
            missing = [" / ".join(group) for group in expected]
        self.records.append({"source": source, "required": required, "status": status,
                             "started_utc": started, "duration_s": round(time.monotonic() - clock, 3),
                             "metric_keys": sorted(metrics), "missing_measurements": missing, "notes": list(notes)})
        for key in metrics:
            self.sources.setdefault(key, []).append(source)
        self.metrics.update(metrics)
        self.active = None
        self.persist()
        self.notify(source, status)
        return result

    def persist(self):
        if self.checkpoint:
            self.checkpoint(self)

    def to_dict(self):
        incomplete = any(r["required"] and r["status"] != "collected" for r in self.records)
        return {"schema_version": 1, "status": "partial" if incomplete else "complete",
                "collectors": self.records, "metric_sources": self.sources}


def collection_summary(collection):
    if not collection:
        return "Collection details unavailable for this run."
    if collection.get("status") == "interrupted":
        return "Interrupted acquisition — recovered data is incomplete. Reconnect hardware and repeat collection."
    failed = [r["source"] for r in collection["collectors"] if r["required"] and r["status"] != "collected"]
    if failed:
        return "Partial collection — missing or incomplete requested evidence: " + ", ".join(failed) + "."
    return "Collection complete — this describes acquisition, not network health or measurement accuracy."
