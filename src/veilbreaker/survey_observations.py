"""Operator-reported field observations kept separate from sensor evidence."""
import re
import uuid

from . import core
from .recovery import atomic_json
from .survey import _editable_session, _session_path, session_lock

CATEGORIES = ('Obstruction', 'Reflective surface', 'Foliage', 'Weather', 'Equipment / placement', 'Other')
MATERIALS = ('Unknown', 'Concrete', 'Reinforced concrete', 'Metal', 'Glass', 'Coated glass',
             'Interior wall', 'Foliage', 'Water', 'People / vehicles', 'Other')
MAX_OBSERVATIONS = 1000
MAX_EDITS = 100


def _text(value, name, limit, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValueError(f'{name} must contain ' + (f'1–{limit}' if required else f'at most {limit}') + ' characters.')
    return value.strip()


def _observations(session):
    rows=session.setdefault('observations',[])
    if not isinstance(rows,list) or len(rows)>MAX_OBSERVATIONS:
        raise ValueError('Survey observations are invalid or exceed the limit.')
    return rows


def _validated_values(values):
    if not isinstance(values,dict) or set(values)-{'run_id','category','material','description','author'}:
        raise ValueError('Invalid observation fields.')
    category,material=values.get('category'),values.get('material')
    if category not in CATEGORIES or material not in MATERIALS:
        raise ValueError('Choose an observation type and material.')
    description=_text(values.get('description'), 'Description', 2000, True)
    author=_text(values.get('author',''), 'Operator', 80)
    return dict(run_id=values.get('run_id'),category=category,material=material,description=description,author=author)


def _validate_point(session,run_id):
    if run_id is not None and (not isinstance(run_id,str) or run_id not in {s['run_id'] for s in session['steps']}):
        raise ValueError('Choose a point from this survey.')


def add_observation(config, path, values):
    clean=_validated_values(values)
    path=_session_path(config,path)
    with session_lock(path):
        session=_editable_session(config,path)
        if session.get('lifecycle')=='completed':
            raise ValueError('Reopen the survey before adding observations.')
        _validate_point(session,clean['run_id'])
        rows=_observations(session)
        if len(rows)>=MAX_OBSERVATIONS:
            raise ValueError('Survey observation limit reached.')
        record=dict(id=uuid.uuid4().hex,source='operator',recorded_utc=core.utcnow_iso(),**clean)
        rows.append(record)
        atomic_json(path,session)
    return record


def update_observation(config, path, observation_id, values, *, expected_revision):
    """Edit one record, preserving its identity and a bounded history of changes."""
    if not isinstance(observation_id,str) or not re.fullmatch(r'[a-f0-9]{32}',observation_id):
        raise ValueError('Invalid observation ID.')
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError('Invalid observation revision.')
    clean=_validated_values(values)
    path=_session_path(config,path)
    with session_lock(path):
        session=_editable_session(config,path)
        if session.get('lifecycle')=='completed':
            raise ValueError('Reopen the survey before editing observations.')
        _validate_point(session,clean['run_id'])
        row=next((r for r in _observations(session) if isinstance(r,dict) and r.get('id')==observation_id and not r.get('deleted_utc')),None)
        if row is None:
            raise ValueError('Observation was not found or was already removed.')
        revision=row.get('revision',0)
        if type(revision) is not int or revision < 0:
            raise ValueError('Observation revision is invalid.')
        if revision != expected_revision:
            raise ValueError('Observation changed since editing began. Reload it and review the current values.')
        previous={key:row.get(key, '' if key=='author' else None) for key in clean}
        if previous == clean:
            return dict(row)
        history=row.get('history',[])
        if not isinstance(history,list) or len(history)>=MAX_EDITS:
            raise ValueError('Observation edit history limit reached or invalid.')
        stamp=core.utcnow_iso()
        row['history']=history+[dict(timestamp=stamp,previous=previous,updated=dict(clean))]
        row.update(clean,updated_utc=stamp,revision=revision+1)
        atomic_json(path,session)
        return dict(row)


def remove_observation(config, path, observation_id, *, expected_revision=None):
    if not isinstance(observation_id,str) or not re.fullmatch(r'[a-f0-9]{32}',observation_id):
        raise ValueError('Invalid observation ID.')
    if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 0):
        raise ValueError('Invalid observation revision.')
    path=_session_path(config,path)
    with session_lock(path):
        session=_editable_session(config,path)
        if session.get('lifecycle')=='completed':
            raise ValueError('Reopen the survey before removing observations.')
        row=next((r for r in _observations(session) if isinstance(r,dict) and r.get('id')==observation_id and not r.get('deleted_utc')),None)
        if row is None:
            raise ValueError('Observation was not found or was already removed.')
        revision=row.get('revision',0)
        if type(revision) is not int or revision < 0:
            raise ValueError('Observation revision is invalid.')
        if expected_revision is not None and revision != expected_revision:
            raise ValueError('Observation changed since it was displayed. Review the current values before removing it.')
        row['deleted_utc']=core.utcnow_iso()
        atomic_json(path,session)
