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


def observations_html(session, photos=None):
    raw=session.get('observations',[])
    if not isinstance(raw,list):
        return '<h2>Operator observations</h2><p>Observation data is unavailable.</p>'
    rows=[row for row in raw if isinstance(row,dict) and not row.get('deleted_utc')]
    if not rows:
        return ''
    labels={step.get('run_id'):step.get('label','Unnamed point') for step in session.get('steps',[])}
    result = ('<h2>Operator observations</h2><p>These are operator observations, not measured signal loss or proven propagation effects.</p>'+
        table(['Observation ID','Recorded UTC','Last edited UTC','Point','Type / material','Description','Operator'],
              [[row.get('id'),row.get('recorded_utc'),row.get('updated_utc') or 'Not edited',labels.get(row.get('run_id'),'Survey-wide' if not row.get('run_id') else 'Point unavailable'),
                str(row.get('category','Unknown'))+' / '+str(row.get('material','Unknown')),
                row.get('description'),row.get('author') or 'Not supplied'] for row in rows]))
    if photos is not None:
        for row in rows:
            if not row.get('photo'): continue
            image = photos.get(row.get('id'))
            result += '<h3>Operator photo · observation '+text(row.get('id'))+'</h3>'
            if image:
                result += '<p><img width="640" src="data:image/png;base64,'+base64.b64encode(image).decode('ascii')+'" alt="Operator photo"></p>'
            else:
                result += '<p>Photo unavailable or failed integrity validation.</p>'
    return result


def calculations_html(session):
    records=session.get('calculations',[])
    if not isinstance(records,list):
        return '<h2>Operator calculations</h2><p>Calculation records are unavailable.</p>'
    rows=[row for row in records if isinstance(row,dict) and not row.get('deleted_utc') and isinstance(row.get('snapshot'),dict)]
    if not rows:return ''
    labels={step.get('run_id'):step.get('label','Unnamed point') for step in session.get('steps',[])}
    parts=['<h2>Operator calculations</h2><p>Calculated estimates based on operator-entered inputs; these are not measured evidence.</p>']
    for row in rows:
        snap=row['snapshot'];run=row.get('run_id')
        parts.append('<h3>'+text(snap.get('title','Calculation'))+'</h3>')
        parts.append('<p>Calculated estimate · Calculator version: '+text(snap.get('version'))+' · Attached UTC: '+text(row.get('attached_utc'))+' · Point: '+text(labels.get(run,'Survey-wide' if not run else 'Point unavailable'))+' · ID: '+text(row.get('id'))+'</p>')
        parts.append('<p>Operator notes: '+text(row.get('notes') or 'None recorded')+'</p>')
        inputs=snap.get('inputs') if isinstance(snap.get('inputs'),dict) else {}
        names=snap.get('input_labels') if isinstance(snap.get('input_labels'),dict) else {}
        outputs=snap.get('outputs') if isinstance(snap.get('outputs'),dict) else {}
        parts.append(table(['Input','Entered value'],[[names.get(key,key),value] for key,value in inputs.items()]))
        parts.append(table(['Calculated result','Value'],[[key,value] for key,value in outputs.items()]))
        notes=snap.get('result_notes')
        for note in notes if isinstance(notes,list) else []:parts.append('<p>'+text(note)+'</p>')
        parts.append('<p>Method: '+text(snap.get('method'))+'<br>Assumptions and limitations: '+text(snap.get('limitations'))+'</p>')
        if isinstance(snap.get('source'),dict):
            source=snap['source'];parts.append('<p>Calculation input source: '+text(source.get('title'))+' · '+text(source.get('output'))+': '+text(source.get('value'))+'<br>Source inputs: '+text(source.get('inputs'))+'<br>Source method: '+text(source.get('method'))+'<br>Source limitations: '+text(source.get('limitations'))+'</p>')
    return '\n'.join(parts)


def report_html(session, imagery=None, cell_context="", photos=None):
    steps = session.get('steps', [])
    states = Counter(s.get('status', 'unknown') for s in steps)
    parts = ['<!doctype html><html><head><meta charset="utf-8"><title>Site survey report</title>',
             '<style>body{font-family:Arial,sans-serif;color:#172131;background:white;margin:28px;} '
             'h1,h2{color:#126759;} table{border-collapse:collapse;border-color:#ccd6df;} '
             'th{background:#e8f3f0;} td{vertical-align:top;} </style></head><body>',
             '<h1>Site survey report</h1>', f'<h2>{text(session.get("name", "Survey"))}</h2>',
             table(['Site', 'Scenario', 'Created (UTC)', 'Survey ID', 'Session state'], [[session.get(k, 'Unknown') for k in ('site_id', 'scenario', 'created_utc', 'survey_id', 'status')]]),
             '<p>Operator lifecycle: ' + text(session.get('lifecycle', 'completed' if session.get('status')=='complete' else 'open')) + '. ' + text(session.get('notes','')) + '</p>',
             imagery_html(imagery), cell_context, observations_html(session, photos), calculations_html(session),
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
