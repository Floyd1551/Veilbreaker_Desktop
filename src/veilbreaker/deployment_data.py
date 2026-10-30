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


def install_bundled_structures(config, base=None, cancelled=lambda: False, progress=lambda _: None):
    """Copy verified bundled structure packs, keeping existing user packs untouched."""
    from .regional_packs import RegionalPackStore
    included = Path(base) if base is not None else deployment_root()
    source_root = included / 'regional-structures'
    if not source_root.is_dir():
        return None
    index_path = included / 'manifest.json'
    if index_path.is_symlink() or index_path.stat().st_size > 1024 * 1024:
        raise ValueError('Bundled structure index is invalid.')
    index = json.loads(index_path.read_text(encoding='utf-8')).get('structure_packs')
    if not isinstance(index, list) or not 1 <= len(index) <= 1000:
        raise ValueError('Bundled structure index is invalid.')
    source = RegionalPackStore(source_root)
    target = RegionalPackStore(config.root / 'regional-packs')
    existing = target.list_packs()
    installed = skipped = records = 0
    seen = set()
    for number, entry in enumerate(index, 1):
        if cancelled(): raise ValueError('Bundled structure installation cancelled; completed packs remain installed.')
        if not isinstance(entry, dict): raise ValueError('Bundled structure index is invalid.')
        pack_id, checksum = entry.get('pack_id'), entry.get('manifest_sha256')
        if not isinstance(pack_id,str) or not re.fullmatch(r'[a-f0-9]{32}',pack_id) or pack_id in seen or not isinstance(checksum,str) or not re.fullmatch(r'[a-f0-9]{64}',checksum):
            raise ValueError('Bundled structure index is invalid.')
        seen.add(pack_id)
        folder = source._folder(pack_id); manifest = folder / 'manifest.json'
        if manifest.is_symlink() or not manifest.is_file() or _sha256(manifest) != checksum:
            raise ValueError('Bundled structure manifest checksum does not match.')
        row = source._manifest(pack_id)
        if row.get('kind') != 'structures' or not source.verify(pack_id, cancelled):
            raise ValueError('Bundled structure data checksum does not match.')
        destination = target._folder(pack_id)
        equivalent = False
        for candidate in existing:
            keys = ('kind','source','license','source_date','bounds_wgs84','record_count','sha256')
            if candidate.get('status') != 'available' or any(candidate.get(key) != row.get(key) for key in keys):
                continue
            if target.verify(candidate['pack_id'], cancelled):
                equivalent = True
                break
        if equivalent:
            skipped += 1
        elif destination.exists():
            if ((destination / 'manifest.json').is_symlink() or not (destination / 'manifest.json').is_file()
                    or _sha256(destination / 'manifest.json') != checksum or not target.verify(pack_id, cancelled)):
                raise ValueError('Existing structure pack differs from the bundled pack; resolve it before retrying.')
            skipped += 1
        else:
            target.root.mkdir(parents=True, exist_ok=True)
            staging = target.root / ('.staging-' + uuid.uuid4().hex)
            try:
                staging.mkdir()
                shutil.copyfile(manifest, staging / 'manifest.json')
                shutil.copyfile(source.data_path(pack_id), staging / 'structures.geojson')
                if _sha256(staging / 'manifest.json') != checksum or _sha256(staging / 'structures.geojson') != row['sha256']:
                    raise ValueError('Copied structure pack checksum does not match.')
                if cancelled(): raise ValueError('Bundled structure installation cancelled; completed packs remain installed.')
                staging.rename(destination)
                installed += 1
                existing.append(dict(row,status='available'))
            finally:
                if staging.exists(): shutil.rmtree(staging)
        records += row['record_count']
        progress({'completed':number,'total':len(index),'installed':installed,'skipped':skipped})
    return {'installed':installed, 'skipped':skipped, 'records':records}
