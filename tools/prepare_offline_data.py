"""Prepare optional, attributed offline deployment files from local downloads."""
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from veilbreaker.cell_reference import import_reference
from veilbreaker.map_pack import inspect_pack


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def prepare(map_file, map_sidecar, cell_file, destination, cell_metadata):
    map_file, map_sidecar, cell_file, destination = map(Path, (map_file, map_sidecar, cell_file, destination))
    if destination.exists():
        raise ValueError('Offline deployment destination already exists.')
    sidecar = json.loads(map_sidecar.read_text(encoding='utf-8'))
    actual_map_hash = _hash(map_file)
    if sidecar.get('sha256') != actual_map_hash:
        raise ValueError('CONUS map checksum does not match its sidecar.')
    map_info = inspect_pack(map_file)
    for key in ('source', 'license', 'date'):
        if not isinstance(cell_metadata.get(key), str) or not cell_metadata[key].strip():
            raise ValueError('Cell reference source, license and date are required.')
    staging = destination.with_name('.offline-data-' + uuid.uuid4().hex)
    try:
        staging.mkdir(parents=True)
        maps = staging / 'maps'
        maps.mkdir()
        staged_map = maps / 'CONUS-overview.pmtiles'
        shutil.copy2(map_file, staged_map)
        if _hash(staged_map) != actual_map_hash:
            raise ValueError('Copied CONUS map checksum does not match.')
        (maps / 'CONUS-overview.json').write_text(json.dumps(sidecar, indent=2), encoding='utf-8')
        reference = import_reference(staging / 'cell-reference', cell_file, cell_metadata,
                                     lambda: False, lambda _progress: None)
        db = staging / 'cell-reference' / reference['dataset_id'] / 'cells.sqlite'
        manifest = {
            'schema_version': 1, 'map_sha256': actual_map_hash,
            'map_source': sidecar.get('source_url'), 'map_source_build': sidecar.get('source_build'),
            'map_attribution': map_info['attribution'], 'map_bounds': map_info['bounds'],
            'cell_source_sha256': _hash(cell_file), 'cell_database_sha256': _hash(db),
            'cell_dataset_id': reference['dataset_id'], 'cell_rows': reference['accepted'],
            'cell_rejected': reference['rejected'], 'cell_unsupported': reference['unsupported'],
            'cell_source': cell_metadata['source'], 'cell_license': cell_metadata['license'],
            'cell_date': cell_metadata['date'],
            'cell_coverage': reference.get('coverage'),
            'cell_attribution': reference['attribution'],
            'limitations': ('Map bounds are not proof of detail at every zoom. OpenCellID positions are '
                            'community estimates, not verified physical towers or complete cell coverage.'),
        }
        (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        staging.rename(destination)
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)
