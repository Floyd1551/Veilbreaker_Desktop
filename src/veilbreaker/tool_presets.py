"""Local, operator-entered calculator presets; never diagnostic evidence."""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .field_tools import REGISTRY, calculate


def _read(path):
    path = Path(path)
    if not path.exists():
        return []
    try:
        if path.stat().st_size > 1_000_000:
            raise ValueError('Preset file is too large.')
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'Could not read calculator presets: {exc}') from exc
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('presets'), list):
        raise ValueError('Calculator presets have an unsupported or invalid format.')
    records = data['presets']
    if len(records) > 200 or any(not isinstance(item, dict) or not isinstance(item.get('id'), str)
                                or item.get('kind') != 'operator preset'
                                or not isinstance(item.get('name'), str) or not item['name'].strip()
                                or not isinstance(item.get('notes'), str)
                                or not isinstance(item.get('tool_id'), str) or not isinstance(item.get('inputs'), dict)
                                or not isinstance(item.get('units'), dict) or not isinstance(item.get('saved_at'), str)
                                for item in records):
        raise ValueError('Calculator presets contain invalid entries.')
    if len({item['id'] for item in records}) != len(records):
        raise ValueError('Calculator presets contain duplicate identities.')
    return records


def _write(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name + '.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({'version': 1, 'presets': records}, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def list_presets(path, tool_id=None):
    """Return saved presets in insertion order, optionally for one calculator."""
    return tuple(item for item in _read(path) if tool_id is None or item['tool_id'] == tool_id)


def save_preset(path, name, tool_id, inputs, notes=''):
    """Validate entered specifications and persist one named input set."""
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        raise ValueError('Preset name must be 1–80 characters.')
    if not isinstance(notes, str) or len(notes) > 1000:
        raise ValueError('Preset notes must be at most 1000 characters.')
    tool = REGISTRY.get(tool_id)
    if tool is None or not isinstance(inputs, dict) or set(inputs) != {field.key for field in tool.fields}:
        raise ValueError('Preset inputs do not match a known calculator.')
    snapshot = calculate(tool_id, inputs)
    records = _read(path)
    if len(records) >= 200:
        raise ValueError('The calculator preset limit of 200 has been reached.')
    record = {'id': uuid4().hex, 'kind': 'operator preset', 'name': name.strip(),
              'tool_id': tool_id, 'inputs': snapshot['inputs'],
              'units': snapshot['input_labels'], 'notes': notes.strip(),
              'saved_at': datetime.now(timezone.utc).isoformat()}
    _write(path, [*records, record])
    return record


def delete_preset(path, preset_id):
    records = _read(path)
    kept = [item for item in records if item['id'] != preset_id]
    if len(kept) == len(records):
        return False
    _write(path, kept)
    return True
