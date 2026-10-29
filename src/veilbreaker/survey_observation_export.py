"""Spreadsheet-safe survey observation export; the JSON journal stays exact."""
import csv
import io


def _safe(value):
    value='' if value is None else str(value)
    return "'"+value if value[:1] in ('\t','\r','\n') or value.lstrip().startswith(('=','+','-','@')) else value


def observations_csv(session):
    rows=session.get('observations',[])
    rows=[r for r in rows if isinstance(r,dict) and not r.get('deleted_utc')] if isinstance(rows,list) else []
    if not rows:
        return None
    labels={step.get('run_id'):step.get('label','Unnamed point') for step in session.get('steps',[])}
    buffer=io.StringIO(newline='')
    writer=csv.writer(buffer)
    writer.writerow(['Observation ID','Source','Recorded UTC','Last edited UTC','Point','Run ID',
                     'Type','Material','Description','Operator'])
    for row in rows:
        run=row.get('run_id')
        point=labels.get(run,'Survey-wide' if not run else 'Point unavailable')
        writer.writerow([_safe(value) for value in (row.get('id'),row.get('source'),row.get('recorded_utc'),
            row.get('updated_utc'),point,run,row.get('category'),row.get('material'),row.get('description'),row.get('author'))])
    return buffer.getvalue()
