"""Passive next-point guidance using the settings acquisition will actually use."""
import hashlib
import json
from . import core
from .survey import _session_path, _editable_session, session_lock, effective_step_config


def _next_point(config, path):
    path = _session_path(config, path)
    with session_lock(path):
        session = _editable_session(config, path)
        if session.get('lifecycle') == 'completed':
            raise ValueError('Reopen the survey before checking or capturing another point.')
        pending = [(i, step) for i, step in enumerate(session['steps']) if step['status'] in ('planned', 'not_run')]
        if not pending:
            raise ValueError('No unrun points remain. Review the report or add new tests.')
        snapshot = path.parent / 'settings' / path.name
        if not snapshot.exists():
            raise ValueError('This older session has no settings snapshot. Start a new survey to continue safely.')
        base = core.AppConfig.from_dict(json.loads(snapshot.read_text(encoding='utf-8')))
        base.data_dir = str(config.root)
        index, step = pending[0]
        cfg = effective_step_config(base, step)
        identity = dict(path=str(path), run_id=step['run_id'], options=step['options'],
                        settings=cfg.to_dict(), manual=session.get('manual', False))
        fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        context = dict(context=fingerprint, survey_path=str(path), run_id=step['run_id'],
                       index=index, label=step['label'], options=dict(step['options']),
                       manual=session.get('manual', False), remaining=len(pending))
    return context, cfg


def next_point_context(config, path):
    return _next_point(config, path)[0]


def check_next_readiness(config, path):
    from .readiness import check_selected
    context, cfg = _next_point(config, path)
    return dict(context, check=check_selected(cfg, context['options']))
