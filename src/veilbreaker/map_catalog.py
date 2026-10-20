"""Local registrations only; unregistering never deletes map archives."""
import json
from pathlib import Path
from .core import utcnow_iso
from .map_pack import inspect_pack
from .recovery import atomic_json


class PackCatalog:
    def __init__(self, path):
        self.path = Path(path)

    def entries(self):
        if not self.path.exists():
            return []
        if self.path.stat().st_size > 1024 * 1024:
            raise ValueError('Map catalog is too large.')
        rows = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(rows, list) or len(rows) > 100:
            raise ValueError('Invalid map catalog.')
        if any(not isinstance(row, dict) or not isinstance(row.get('path'), str) for row in rows):
            raise ValueError('Invalid map catalog entry.')
        return [dict(row, available=Path(row['path']).is_file()) for row in rows]

    def register(self, path):
        pack = inspect_pack(Path(path))
        row = {key: pack[key] for key in ('path', 'name', 'size', 'bounds', 'minzoom', 'maxzoom', 'attribution')}
        row['registered_utc'] = utcnow_iso()
        # Source date is optional provenance, never inferred from registration time.
        row['source_date'] = None
        sidecar = Path(path).with_suffix('.json')
        try:
            if sidecar.stat().st_size <= 65536:
                date = json.loads(sidecar.read_text(encoding='utf-8')).get('source_build')
                if isinstance(date, str) and len(date) <= 40:
                    row['source_date'] = date
        except (OSError, ValueError, AttributeError):
            pass
        rows = [r for r in self.entries() if r['path'] != row['path']]
        if len(rows) >= 100:
            raise ValueError('Remove a registration before adding more maps (limit 100).')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(self.path, rows + [row])
        return row

    def remove(self, path):
        target = str(Path(path).resolve())
        atomic_json(self.path, [r for r in self.entries() if r['path'] != target])
