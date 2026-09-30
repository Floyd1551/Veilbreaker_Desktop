"""Portable evidence integrity. Hashes detect changes, not author authenticity."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

from . import __version__

MANIFEST = "evidence-manifest.json"
MAX_BYTES = 512 * 1024 * 1024


def write_manifest(folder, metadata):
    folder = Path(folder)
    files = {}
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.name != MANIFEST:
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            files[path.name] = {"bytes": path.stat().st_size,
                                "sha256": digest}
    manifest = {"schema_version": 1, "application_version": __version__,
                "metadata": metadata, "files": files}
    (folder / MANIFEST).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def verify_bundle(path):
    """Read without extraction; reject ambiguous archives and bound decompression."""
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)):
                raise ValueError("Duplicate archive entries")
            if any(PurePosixPath(n).name != n or "\\" in n or ":" in n or n in {".", ".."} for n in names):
                raise ValueError("Unexpected archive path")
            if sum(e.file_size for e in entries) > MAX_BYTES:
                raise ValueError("Bundle exceeds the 512 MiB verification limit")
            if MANIFEST not in names:
                return {"status": "unverified", "message": "Legacy bundle has no integrity manifest; contents cannot be verified."}
            manifest = json.loads(archive.read(MANIFEST))
            if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
                raise ValueError("Unsupported evidence manifest schema")
            files = manifest.get("files")
            if not isinstance(files, dict) or not files:
                raise ValueError("Manifest contains no file records")
            if set(files) != set(names) - {MANIFEST}:
                raise ValueError("Archive files do not match the manifest")
            for name, expected in files.items():
                if not isinstance(expected, dict):
                    raise ValueError(f"Invalid file record: {name}")
                with archive.open(name) as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                if archive.getinfo(name).file_size != expected.get("bytes") or digest != expected.get("sha256"):
                    raise ValueError(f"Integrity mismatch: {name}")
            return {"status": "verified", "message": f"All {len(files)} files match the SHA-256 manifest. This does not authenticate the author.",
                    "metadata": manifest.get("metadata", {}), "application_version": manifest.get("application_version")}
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        return {"status": "failed", "message": str(exc)}
