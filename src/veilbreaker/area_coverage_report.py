"""Portable report for an offline area readiness preview."""
from .core import utcnow_iso
from .survey_report import table, text


def report_html(model):
    """Render saved preview results without promoting extents to field coverage."""
    parts=['<!doctype html><html><head><meta charset="utf-8"><title>Area readiness preview</title>',
           '<style>body{font:15px Arial,sans-serif;margin:28px;color:#172131}h1,h2{color:#126759}'
           'table{border-collapse:collapse;border-color:#ccd6df}th{background:#e8f3f0}td{vertical-align:top}</style>',
           '</head><body><h1>Area readiness preview</h1>',
           '<p>Checked (UTC): '+text(model.get('checked_utc') or 'Not recorded')+'<br>Report saved (UTC): '+text(utcnow_iso())+'<br>WGS84 bounds (west, south, east, north): '+text(model['bounds'])+'</p>',
           '<p>This is an offline snapshot of data availability and sparse checks. It is not a radio coverage prediction or a line-of-sight assessment.</p>']
    for key,title in (('map','Maps'),('terrain','Terrain'),('cell','Cell references'),('structures','Physical structures')):
        row=model[key]
        parts.append('<h2>'+title+'</h2><p><b>'+text(row['status'])+'</b><br>'+text(row['note'])+'</p>')
        if key=='cell':
            if row.get('source'):
                parts.append('<p>Source: '+text(row['source'])+' · Date: '+text(row.get('date'))+'<br>'+text(row.get('attribution'))+
                             '<br>Source snapshot SHA-256: '+text(row.get('sha256'))+'</p>')
            if row.get('groups'):
                parts.append(table(['Radio','MCC','MNC','Records'],[[r.get(k) for k in ('radio','mcc','mnc','count')] for r in row['groups']]))
        else:
            packs=row.get('packs') or []
            if packs:
                parts.append(table(['Name','Source','Source date','Bounds','License / terms','Attribution / SHA-256'],
                    [[p.get('name'),p.get('source','Map catalog'),p.get('source_date'),
                      p.get('bounds_wgs84',p.get('bounds')),p.get('license'),p.get('attribution',p.get('sha256'))] for p in packs]))
            if key=='terrain':
                if row.get('gaps'):
                    parts.append('<p>Extent gap count: '+text(row.get('gap_count',len(row['gaps'])))+'<br>Example extent gaps (west, south, east, north): '+text(row['gaps'][:10])+'</p>')
                sample=row.get('sample')
                if not sample:
                    parts.append('<p>No terrain sampling requested.</p>')
                elif sample['status']=='sampled':
                    parts.append('<p>'+text(sample['note'])+'</p>')
                    parts.append(table(['Grid','Total samples','Valid','Missing','Outside raster','No-data','Datum','Units','Declarations compatible'],
                        [[f"{sample['grid_size']} × {sample['grid_size']}",sample['total'],sample['valid'],sample['missing'],sample['outside'],
                          sample['nodata'],sample['datums'],sample['units'],sample['compatible']]]))
                    if sample.get('examples'):
                        parts.append('<p>Example missing coordinates (longitude, latitude): '+text(sample['examples'])+'</p>')
                else:
                    parts.append('<p>No overlapping available terrain packs were sampled.</p>')
    parts.append('</body></html>')
    return '\n'.join(parts)
