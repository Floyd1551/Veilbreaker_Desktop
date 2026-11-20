"""Discover optional offline files installed beside the desktop executable."""
import hashlib
import json
import re
import shutil
import sys
import uuid
from pathlib import Path

from .cell_reference import (active_reference, activate_reference, list_references,
                             reference_database_signature, verify_reference_database,
                             _json, _link_or_reparse)


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


def _copy_bundled_database(source, destination, expected_size, cancelled, progress):
    """Copy a bounded database into an unpublished staging directory."""
    count = 0
    with source.open('rb') as src, destination.open('xb') as dst:
        while chunk := src.read(1024 * 1024):
            if cancelled(): raise ValueError('Bundled reference installation cancelled.')
            count += len(chunk)
            if count > expected_size: raise ValueError('Bundled database changed during copy.')
            dst.write(chunk)
            progress(f'Copying included reference: {count / 1024**2:.1f} / {expected_size / 1024**2:.1f} MiB')
    if count != expected_size:
        raise ValueError('Bundled database changed during copy.')


def _verify_copied_database(path, cancelled):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            if cancelled(): raise ValueError('Bundled reference installation cancelled.')
            digest.update(chunk)
    return digest.hexdigest()


def install_bundled_reference(user_root, base=None, cancelled=lambda: False, progress=lambda _: None):
    """Install a verified bundled cell snapshot without changing the active selection.

    Source and destination are checked independently. A legacy active reference
    remains intact until the operator explicitly selects a replacement.
    """
    if not callable(cancelled) or not callable(progress):
        raise ValueError('Invalid installation callback.')
    def check():
        if cancelled(): raise ValueError('Bundled reference installation cancelled.')
    check()
    included = Path(base) if base is not None else deployment_root()
    source_root = included / 'cell-reference'
    if not source_root.exists():
        return {'status': 'unavailable', 'dataset_id': None}
    if _link_or_reparse(source_root) or not source_root.is_dir():
        raise ValueError('Bundled cell reference storage is invalid.')
    entries = [p for p in source_root.iterdir() if re.fullmatch(r'[a-f0-9]{32}', p.name)]
    if len(entries) != 1 or _link_or_reparse(entries[0]) or not entries[0].is_dir():
        raise ValueError('Bundled cell reference must contain exactly one snapshot.')
    source = entries[0]
    index_path = included / 'manifest.json'
    if _link_or_reparse(index_path): raise ValueError('Bundled cell index is invalid.')
    index = _json(index_path)
    if not isinstance(index, dict): raise ValueError('Bundled cell index is invalid.')
    checksum = index.get('cell_database_sha256')
    manifest_path = source / 'manifest.json'
    if _link_or_reparse(manifest_path): raise ValueError('Bundled cell manifest is invalid.')
    manifest = _json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get('dataset_id') != source.name or manifest.get('format') != 'opencellid':
        raise ValueError('Bundled cell reference manifest is invalid.')
    fields = {'cell_dataset_id':'dataset_id', 'cell_source_sha256':'sha256',
              'cell_source':'source', 'cell_license':'license', 'cell_date':'date',
              'cell_rows':'accepted', 'cell_rejected':'rejected', 'cell_unsupported':'unsupported',
              'cell_coverage':'coverage', 'cell_attribution':'attribution'}
    for index_key, manifest_key in fields.items():
        if index_key in index and (type(index[index_key]) is not type(manifest.get(manifest_key)) or
                                   index[index_key] != manifest.get(manifest_key)):
            raise ValueError('Bundled cell reference provenance metadata conflicts with its index.')
    if (not isinstance(checksum, str) or not re.fullmatch(r'[a-f0-9]{64}', checksum)
            or manifest.get('database_sha256') != checksum
            or type(manifest.get('database_bytes')) is not int or manifest['database_bytes'] <= 0):
        raise ValueError('Bundled cell database checksum metadata is missing or inconsistent.')
    progress('Verifying the included cell reference…')
    source_check = verify_reference_database(source_root, source.name, cancelled)
    if source_check['status'] != 'verified' or source_check['actual_sha256'] != checksum:
        raise ValueError('Bundled cell reference checksum verification failed.')
    check()
    user_root = Path(user_root)
    target = user_root / source.name
    # A matching source and database with the same provenance can be reused even
    # when a later build assigned a different snapshot ID.
    ignored = {'dataset_id', 'imported_utc'}
    for entry in list_references(user_root):
        check()
        if {k:v for k,v in entry.items() if k not in ignored} != {k:v for k,v in manifest.items() if k not in ignored}:
            continue
        if verify_reference_database(user_root, entry['dataset_id'], cancelled)['status'] == 'verified':
            return {'status': 'existing', 'dataset_id': entry['dataset_id']}
    if target.exists() or _link_or_reparse(target):
        raise ValueError('Existing reference ID collision; the current files were not changed.')
    user_root.mkdir(parents=True, exist_ok=True)
    staging = user_root / ('.staging-' + uuid.uuid4().hex)
    try:
        staging.mkdir()
        (staging / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
        _copy_bundled_database(source / 'cells.sqlite', staging / 'cells.sqlite', manifest['database_bytes'], cancelled, progress)
        check()
        progress('Verifying the copied reference…')
        if (_verify_copied_database(staging / 'cells.sqlite', cancelled) != checksum or _json(manifest_path) != manifest
                or _json(index_path) != index or reference_database_signature(source_root, source.name) != source_check['file_signature']):
            raise ValueError('Bundled reference changed or copied database checksum does not match.')
        if target.exists() or _link_or_reparse(target):
            raise ValueError('Existing reference ID collision; the current files were not changed.')
        check()
        staging.rename(target)
        return {'status': 'installed', 'dataset_id': source.name}
    finally:
        if staging.exists(): shutil.rmtree(staging)


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
