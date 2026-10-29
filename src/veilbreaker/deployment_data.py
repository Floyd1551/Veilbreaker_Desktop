"""Discover optional offline files installed beside the desktop executable."""
import hashlib
import json
import re
import shutil
import sys
import uuid
from pathlib import Path

from .cell_reference import active_reference, activate_reference


def deployment_root():
    base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]
    return base / 'offline-data'


def bundled_map(base=None):
    path = Path(base) / 'maps' / 'CONUS-overview.pmtiles' if base is not None else deployment_root() / 'maps' / 'CONUS-overview.pmtiles'
    return path if path.is_file() else None


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def seed_reference(user_root, base=None):
    """Install a bundled immutable snapshot once; never replace an active choice."""
    user_root = Path(user_root)
    current = active_reference(user_root)
    if current:
        return current
    if (user_root / 'active.json').exists():
        return None
    included = Path(base) if base is not None else deployment_root()
    source_root = included / 'cell-reference'
    if not source_root.is_dir():
        return None
    entries = [p for p in source_root.iterdir() if p.is_dir() and re.fullmatch(r'[a-f0-9]{32}', p.name)]
    if len(entries) != 1:
        raise ValueError('Bundled cell reference must contain exactly one snapshot.')
    source = entries[0]
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    bundle_manifest = json.loads((included / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('dataset_id') != source.name or manifest.get('format') != 'opencellid':
        raise ValueError('Bundled cell reference manifest is invalid.')
    checksum = bundle_manifest.get('cell_database_sha256')
    if not isinstance(checksum, str) or not re.fullmatch(r'[a-f0-9]{64}', checksum) or _sha256(source / 'cells.sqlite') != checksum:
        raise ValueError('Bundled cell reference checksum does not match.')
    target = user_root / source.name
    if not target.exists():
        user_root.mkdir(parents=True, exist_ok=True)
        staging = user_root / ('.' + uuid.uuid4().hex)
        try:
            shutil.copytree(source, staging)
            if _sha256(staging / 'cells.sqlite') != checksum:
                raise ValueError('Copied cell reference checksum does not match.')
            staging.rename(target)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    elif _sha256(target / 'cells.sqlite') != checksum:
        raise ValueError('Existing cell reference differs from the included snapshot.')
    activate_reference(user_root, source.name)
    return active_reference(user_root)
