"""Portable survey snapshots; no acquisition or changes to original evidence."""
from collections import Counter
from html import escape
import json
import math
import statistics
import base64


def text(value):
    if value is None:
        return 'Not observed'
    if isinstance(value, (dict, list, bool)):
        value = json.dumps(value, ensure_ascii=False)
    return escape(str(value)).replace('\n', '<br>')


def table(headers, rows):
    return '<table width="100%" cellspacing="0" cellpadding="7" border="1"><tr>' + ''.join(
        f'<th align="left">{text(h)}</th>' for h in headers) + '</tr>' + ''.join(
        '<tr>' + ''.join(f'<td>{text(v)}</td>' for v in row) + '</tr>' for row in rows) + '</table>'


def imagery_html(imagery):
    if not imagery:
        return ''
    parts = ['<h2>Survey area</h2>']
    if imagery.get('warning'):
        parts.append('<p><b>'+text(imagery['warning'])+'</b></p>')
    if imagery.get('image'):
        encoded = base64.b64encode(imagery['image']).decode('ascii')
        parts.append('<p><img width="960" src="data:image/png;base64,'+encoded+'" alt="Survey area with numbered measurement locations"></p>')
        parts.append(table(['Image type', 'Source', 'Imagery date', 'Prepared (UTC)'], [[
            imagery.get('imagery_type','reference').capitalize()+' imagery', imagery.get('source'),
            imagery.get('imagery_date') or 'Unknown (not the preparation date)', imagery.get('prepared_utc')]]))
        parts.append('<p>'+text(imagery.get('attribution'))+'</p>')
        parts.append('<p>Extent: '+text(imagery.get('bounds'))+' · '+text(imagery.get('crs'))+
                     '. '+str(len(imagery.get('points',[])))+' mapped points; '+text(imagery.get('missing_points',0))+' without qualified GPS.</p>')
        if imagery.get('manual_area'):
            parts.append('<p>Manually selected area; no receiver position is implied.</p>')
        if imagery.get('points'):
            parts.append(table(['Marker', 'Survey point', 'Run'], [[p.get('number'),p.get('label'),p.get('run_id')] for p in imagery['points']]))
        parts.append('<p>Historical geographic context; imagery does not establish current conditions, tower identity or line of sight.</p>')
    return '\n'.join(parts)


def report_html(session, imagery=None):
    steps = session.get('steps', [])
    states = Counter(s.get('status', 'unknown') for s in steps)
    parts = ['<!doctype html><html><head><meta charset="utf-8"><title>Site survey report</title>',
             '<style>body{font-family:Arial,sans-serif;color:#172131;background:white;margin:28px;} '
             'h1,h2{color:#126759;} table{border-collapse:collapse;border-color:#ccd6df;} '
             'th{background:#e8f3f0;} td{vertical-align:top;} </style></head><body>',
             '<h1>Site survey report</h1>', f'<h2>{text(session.get("name", "Survey"))}</h2>',
             table(['Site', 'Scenario', 'Created (UTC)', 'Survey ID', 'Session state'], [[session.get(k, 'Unknown') for k in ('site_id', 'scenario', 'created_utc', 'survey_id', 'status')]]),
             '<p>Operator lifecycle: ' + text(session.get('lifecycle', 'completed' if session.get('status')=='complete' else 'open')) + '. ' + text(session.get('notes','')) + '</p>',
             imagery_html(imagery),
             '<h2>Collection overview</h2>',
             f'<p>{states.get("complete", 0)} / {len(steps)} tests complete. ' + text(', '.join(f'{n} {s}' for s, n in sorted(states.items()))) + '.</p>',
             '<p>Collection completion is separate from service health. Missing measurements remain unknown. '
             'This report is a snapshot; save point notes before generating it.</p>',
             table(['Point', 'Collection', 'Assessment', 'Run'], [[s.get('label'), s.get('status'), s.get('assessment', 'Not assessed'), s.get('run_id', 'Unavailable')] for s in steps]),
             '<h2>Numeric measurement summary</h2>',
             '<p>Finite numeric measurements from complete tests only. Observed counts are relative to all planned points. '
             'These descriptive statistics do not establish comparability or improvement. Compare equivalent selections, '
             'receiver settings, antennas and conditions. RF power remains relative and uncalibrated.</p>']
    values = {}
    for step in steps:
        if step.get('status') == 'complete':
            for key, value in step.get('metrics', {}).items():
                if type(value) in (int, float) and math.isfinite(value):
                    values.setdefault(key, []).append(value)
    if values:
        parts.append(table(['Metric (native key / units)', 'Observed / planned', 'Minimum', 'Median', 'Maximum'],
                           [[k, f'{len(v)} / {len(steps)}', min(v), statistics.median(v), max(v)] for k, v in sorted(values.items())]))
    else:
        parts.append('<p>No numeric measurements from complete tests.</p>')
    keys = sorted({k for s in steps for k in s.get('metrics', {})})
    parts.append('<h2>Point details and measurement gaps</h2>')
    for index, step in enumerate(steps, 1):
        parts.extend([f'<h3>{index}. {text(step.get("label", "Point"))}</h3>',
                      f'<p>Collection: {text(step.get("status", "unknown"))} · Assessment: {text(step.get("assessment", "Not assessed"))}</p>',
                      '<p>Requested tests: ' + text(', '.join(k for k, v in sorted(step.get('options', {}).items()) if v) or 'Passive host/network') + '</p>',
                      '<p>Operator notes: ' + text(step.get('notes') or 'None recorded') + '</p>'])
        for key in ('error', 'export_note'):
            if step.get(key):
                parts.append(f'<p>{text(step[key])}</p>')
        if step.get('status') != 'complete':
            parts.append('<p>Incomplete test: available values below are retained but excluded from the numeric summary.</p>')
        parts.append(table(['Metric', 'Observed value'], [[k, step.get('metrics', {}).get(k)] for k in keys]) if keys else '<p>No measurements available.</p>')
    parts.append('<p>Original run evidence remains separate. Viewing this report does not verify evidence integrity. '
                 'Use the survey evidence ZIP for original bundles and the integrity manifest.</p></body></html>')
    return '\n'.join(parts)
