"""Derived location views; source evidence is never changed."""
import json
import math
from .location_report import qualify_location

MERCATOR_LIMIT = 85.05112878

def finite(value):
    try: return type(value) in (int, float) and math.isfinite(value)
    except OverflowError: return False

def build_map_data(runs):
    rows, features, representatives, warnings = [], [], [], []
    unpositioned = 0
    for run in runs:
        representative = None
        start_count = len(rows)
        locations = run.get('locations') or []
        if not isinstance(locations, list):
            locations = []; warnings.append('Invalid location evidence: ' + str(run.get('run_id')))
        for location in locations[:1000]:
            if not isinstance(location, dict):
                warnings.append('Invalid location observation: ' + str(run.get('run_id'))); continue
            lat, lon = location.get('latitude_deg'), location.get('longitude_deg')
            valid = finite(lat) and finite(lon) and abs(lat)<=90 and abs(lon)<=180
            quality = qualify_location(location)
            row = dict(id='p'+str(len(rows)), run_id=str(run.get('run_id','')), label=str(run.get('label') or run.get('run_id','')),
                       observation_id=str(location.get('observation_id') or 'Unknown'), quality=quality,
                       renderable=bool(valid and abs(lat)<=MERCATOR_LIMIT))
            for key in ('latitude_deg','longitude_deg','horizontal_accuracy_m','fix_age_ms','source','provider','fix_utc','received_utc','mock'):
                value = location.get(key)
                row[key] = value if isinstance(value,(str,bool)) or finite(value) else None
            rows.append(row)
            if valid:
                features.append(dict(type='Feature',id=row['id'],geometry=dict(type='Point',coordinates=[lon,lat]),properties=dict(row)))
                if representative is None and quality['qualified']:
                    representative = row['id']
            else:
                warnings.append('No valid coordinates: ' + row['label'] + ' / ' + row['observation_id'])
        if representative is not None: representatives.append(representative)
        else:
            unpositioned += 1
            if len(rows)==start_count:
                rows.append(dict(id='p'+str(len(rows)),run_id=str(run.get('run_id','')),label=str(run.get('label') or run.get('run_id','')),
                                 observation_id='No GPS evidence',quality=qualify_location({}),renderable=False))
    return dict(features=dict(type='FeatureCollection',features=features), rows=rows,representatives=representatives,warnings=warnings,
                counts=dict(observations=sum(len(r.get('locations') or []) if isinstance(r.get('locations'),list) else 0 for r in runs),
                            mapped=sum(r['renderable'] and r['quality']['qualified'] for r in rows),
                            questionable=sum(not f['properties']['quality']['qualified'] for f in features),unpositioned_runs=unpositioned))

def map_bounds(features):
    coords=[f['geometry']['coordinates'] for f in features if f['properties'].get('renderable')]
    if not coords: return None
    xs=sorted(c[0]%360 for c in coords)
    gaps=[((xs[(i+1)%len(xs)]-xs[i])%360 if len(xs)>1 else 360,i) for i in range(len(xs))]
    _,i=max(gaps)
    west=xs[(i+1)%len(xs)]; east=xs[i]
    if east<west: east+=360
    if west>180: west-=360; east-=360
    return [west,min(c[1] for c in coords),east,max(c[1] for c in coords)]

def export_geojson(model,feature_ids):
    allowed=set(feature_ids)
    return json.dumps(dict(type='FeatureCollection',features=[f for f in model['features']['features'] if f['id'] in allowed]),ensure_ascii=False,allow_nan=False,indent=2)+'\n'
