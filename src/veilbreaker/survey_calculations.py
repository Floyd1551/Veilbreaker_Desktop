"""Attach validated operator calculations without changing measurement evidence."""
import json
import math
import re
import uuid
from pathlib import Path

from . import core
from .field_tools import REGISTRY, calculate
from .recovery import atomic_json
from .survey import _editable_session, _session_path, session_lock

MAX_SNAPSHOT_BYTES=256*1024
MAX_CALCULATIONS=100


def _same_number(actual,expected):
    return type(actual) in (int,float) and math.isfinite(actual) and math.isclose(actual,expected,rel_tol=1e-12,abs_tol=0.0)


def validate_snapshot(value):
    """Recalculate supported version-1 snapshots and reject mismatched outputs."""
    if not isinstance(value,dict) or value.get('kind')!='calculated estimate' or type(value.get('version')) is not int or value['version']!=1:
        raise ValueError('Choose a supported version 1 calculated estimate snapshot.')
    tool=REGISTRY.get(value.get('tool_id')) if isinstance(value.get('tool_id'),str) else None
    inputs=value.get('inputs')
    if tool is None or not isinstance(inputs,dict) or set(inputs)!={field.key for field in tool.fields}:
        raise ValueError('Snapshot does not match a supported calculator and its inputs.')
    if any(type(value) not in (int,float) or not math.isfinite(value) for value in inputs.values()):
        raise ValueError('Snapshot inputs must be finite numeric values.')
    try:
        expected=calculate(tool.key,inputs)
    except (ValueError,TypeError,OverflowError) as exc:
        raise ValueError('Calculator inputs are invalid: '+str(exc)) from exc
    outputs=value.get('outputs')
    if (not isinstance(outputs,dict) or set(outputs)!=set(expected['outputs']) or
        any(not _same_number(outputs[key],expected['outputs'][key]) for key in expected['outputs'])):
        raise ValueError('Saved calculation results do not match the current calculator inputs.')
    for key in ('title','input_labels','method','limitations','result_notes'):
        if value.get(key) != expected.get(key):
            raise ValueError('Saved calculation metadata differs from this calculator version; review it before attaching.')
    # Keep the saved numeric values after validation; no recalculation silently
    # replaces the operator's recorded estimate when the snapshot is attached.
    expected['inputs']=dict(inputs)
    expected['outputs']=dict(outputs)
    if 'source' in value:
        source=value['source']
        from .tool_handoff import fspl_to_link_budget
        if tool.key!='link_budget' or not isinstance(source,dict) or source.get('tool_id')!='fspl':
            raise ValueError('Unsupported calculation source.')
        try:
            fspl=calculate('fspl',source.get('inputs',{}))
            handoff=fspl_to_link_budget(fspl)
            canonical=handoff['source']
            if (set(source)!=set(canonical) or any(source.get(key)!=canonical[key] for key in canonical if key!='value') or
                not _same_number(source.get('value'),canonical['value']) or not _same_number(inputs.get('path_loss'),handoff['inputs']['path_loss'])):
                raise ValueError('Handoff value does not match inputs.')
            expected['source']=dict(source,inputs=dict(source['inputs']))
        except (ValueError,TypeError,KeyError,OverflowError) as exc:
            raise ValueError('Calculation handoff is invalid: '+str(exc)) from exc
    return expected


def read_snapshot(path):
    path=Path(path)
    try:
        if path.stat().st_size>MAX_SNAPSHOT_BYTES:
            raise ValueError('Calculation snapshot exceeds the size limit.')
        value=json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError,UnicodeError,json.JSONDecodeError,RecursionError) as exc:
        raise ValueError('Could not read a calculation JSON snapshot.') from exc
    return validate_snapshot(value)


def _records(session):
    records=session.setdefault('calculations',[])
    if not isinstance(records,list) or len(records)>MAX_CALCULATIONS:
        raise ValueError('Survey calculations are invalid or exceed the limit.')
    return records


def attach_calculation(config,path,snapshot,run_id=None,notes=''):
    validated=validate_snapshot(snapshot)
    if not isinstance(notes,str) or len(notes)>1000:
        raise ValueError('Calculation notes must contain at most 1000 characters.')
    path=_session_path(config,path)
    with session_lock(path):
        session=_editable_session(config,path)
        if session.get('lifecycle')=='completed':
            raise ValueError('Reopen the survey before attaching calculations.')
        if run_id is not None and (not isinstance(run_id,str) or run_id not in {step['run_id'] for step in session['steps']}):
            raise ValueError('Choose a point from this survey.')
        records=_records(session)
        if len(records)>=MAX_CALCULATIONS:
            raise ValueError('Survey calculation limit reached.')
        row=dict(id=uuid.uuid4().hex,kind='operator calculation',attached_utc=core.utcnow_iso(),run_id=run_id,
                 notes=notes.strip(),snapshot=validated)
        records.append(row);atomic_json(path,session)
    return row


def remove_calculation(config,path,calculation_id):
    if not isinstance(calculation_id,str) or not re.fullmatch(r'[a-f0-9]{32}',calculation_id):
        raise ValueError('Invalid calculation ID.')
    path=_session_path(config,path)
    with session_lock(path):
        session=_editable_session(config,path)
        if session.get('lifecycle')=='completed':
            raise ValueError('Reopen the survey before removing calculations.')
        row=next((r for r in _records(session) if isinstance(r,dict) and r.get('id')==calculation_id and not r.get('deleted_utc')),None)
        if row is None:raise ValueError('Calculation was not found or was already removed.')
        row['deleted_utc']=core.utcnow_iso();atomic_json(path,session)
