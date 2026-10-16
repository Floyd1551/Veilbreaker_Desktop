"""Recoverable library removal: atomic tombstones, no evidence-file deletion."""
import json
import uuid
from . import core


def run_dependencies(config, run_id, store=None):
    own = store is None
    store = store or core.VeilbreakerStore(config.db_path)
    try:
        cases = [r[0] for r in store.db.execute('SELECT case_id FROM cases WHERE source_run_id=?',(run_id,))]
        surveys = []
        removed = {r[0] for r in store.db.execute("SELECT item_id FROM trash_entries WHERE kind='survey'")}
        for path in (config.root/'surveys').glob('survey-*.json'):
            data = json.loads(path.read_text(encoding='utf-8'))
            if data['survey_id'] not in removed and any(s['run_id']==run_id for s in data['steps']):
                surveys.append(data['survey_id'])
        return dict(cases=cases, surveys=surveys)
    finally:
        if own: store.close()


def _insert(store, kind, item_id, metadata):
    existing = store.db.execute('SELECT entry_id FROM trash_entries WHERE kind=? AND item_id=?',(kind,item_id)).fetchone()
    if existing: return existing[0]
    entry = uuid.uuid4().hex
    store.db.execute('INSERT INTO trash_entries VALUES (?,?,?,?,?)',(entry,kind,item_id,core.utcnow_iso(),json.dumps(metadata)))
    return entry


def trash_run(config, run_id):
    store = core.VeilbreakerStore(config.db_path)
    try:
        with store.db:
            store.db.execute('BEGIN IMMEDIATE')
            row = store.db.execute('SELECT * FROM runs WHERE run_id=?',(run_id,)).fetchone()
            if row is None: raise ValueError('Test no longer exists')
            deps = run_dependencies(config,run_id,store)
            if deps['cases'] or deps['surveys']: raise ValueError('Test is referenced by '+', '.join(deps['surveys']+deps['cases'])+'. Manage it through the owning survey or case.')
            return _insert(store,'run',run_id,dict(row))
    finally: store.close()


def list_trash(config):
    if not config.db_path.exists(): return []
    store = core.VeilbreakerStore(config.db_path)
    try: return [dict(r) for r in store.db.execute('SELECT * FROM trash_entries ORDER BY removed_utc DESC')]
    finally: store.close()


def restore_entry(config, entry_id):
    store = core.VeilbreakerStore(config.db_path)
    try:
        with store.db:
            store.db.execute('BEGIN IMMEDIATE')
            row = store.db.execute('SELECT * FROM trash_entries WHERE entry_id=?',(entry_id,)).fetchone()
            if not row: raise ValueError('Removal no longer exists')
            metadata = json.loads(row['metadata_json'])
            if row['kind']=='run':
                current = store.db.execute('SELECT * FROM runs WHERE run_id=?',(row['item_id'],)).fetchone()
                if current is None or dict(current)!=metadata: raise ValueError('Restore conflict: original test was changed or is missing')
            else:
                path = config.root/'surveys'/(row['item_id']+'.json')
                if not path.is_file() or path.read_text(encoding='utf-8')!=metadata['journal']:
                    raise ValueError('Restore conflict: original survey was changed or is missing')
                original = json.loads(metadata['journal'])
                owned = set(metadata.get('children', []))
                for step in original['steps']:
                    removal = store.db.execute("SELECT entry_id FROM trash_entries WHERE kind='run' AND item_id=?", (step['run_id'],)).fetchone()
                    if removal and removal[0] not in owned:
                        raise ValueError('Restore the independently removed test first: ' + step['run_id'])
                for child in metadata.get('children',[]):
                    removed = store.db.execute("SELECT * FROM trash_entries WHERE entry_id=? AND kind='run'", (child,)).fetchone()
                    if removed:
                        current = store.db.execute('SELECT * FROM runs WHERE run_id=?', (removed['item_id'],)).fetchone()
                        if current is None or dict(current) != json.loads(removed['metadata_json']):
                            raise ValueError('Restore conflict: associated test was changed or is missing')
                for child in metadata.get('children',[]):
                    # Independently restored tests remain restored.
                    store.db.execute('DELETE FROM trash_entries WHERE entry_id=? AND kind=?',(child,'run'))
            store.db.execute('DELETE FROM trash_entries WHERE entry_id=?',(entry_id,))
    finally: store.close()


def trash_survey(config, path, include_owned_runs=False):
    from .survey import _session_path, session_lock, read_session
    path = _session_path(config,path)
    with session_lock(path):
        data = read_session(config,path)
        if data['status']=='running': raise ValueError('Wait for the active survey to finish')
        store = core.VeilbreakerStore(config.db_path)
        try:
            with store.db:
                store.db.execute('BEGIN IMMEDIATE')
                children=[]
                if include_owned_runs:
                    for step in data['steps']:
                        deps=run_dependencies(config,step['run_id'],store)
                        if deps['cases'] or any(s!=data['survey_id'] for s in deps['surveys']): continue
                        row=store.db.execute('SELECT * FROM active_runs WHERE run_id=?',(step['run_id'],)).fetchone()
                        if row: children.append(_insert(store,'run',step['run_id'],dict(row)))
                return _insert(store,'survey',data['survey_id'],dict(journal=path.read_text(encoding='utf-8'),children=children))
        finally: store.close()
