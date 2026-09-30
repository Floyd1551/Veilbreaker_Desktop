"""Stable executable entry point and actionable errors for the recovered CLI."""
import json
import os
import sqlite3
import sys
from . import core


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--desktop-job":
        from .jobs import worker_main
        return worker_main(args[1:])
    # Also used by packaged GUI smoke verification.
    if args and args[0] == "--gui-smoke":
        from .gui import smoke
        return smoke(args[1])
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        if args and args[0] == "verify":
            import argparse
            from .evidence import verify_bundle
            parser = argparse.ArgumentParser(prog="veilbreaker verify", description="Check evidence bundle integrity (not author authenticity).")
            parser.add_argument("bundle")
            options = parser.parse_args(args[1:])
            result = verify_bundle(options.bundle)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return {"verified": 0, "failed": 1, "unverified": 2}[result["status"]]
        return core.main(args)
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        print(f"Veilbreaker: {exc}", file=sys.stderr)
        return 2
