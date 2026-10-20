"""Survey-owned photographic context; original diagnostic evidence is untouched."""
import hashlib
import json
import math
import re
import uuid
from pathlib import Path
from .core import utcnow_iso
from .recovery import atomic_json

MAX_BYTES = 20 * 1024 * 1024
MAX_DIMENSION = 2048
RADIUS = 6378137.0
MERCATOR_EDGE = math.pi * RADIUS


def validate_metadata(value):
    if not isinstance(value, dict) or value.get('schema_version') != 1:
        raise ValueError('Imagery sidecar must use schema_version 1.')
    crs = value.get('crs')
    if crs not in ('EPSG:4326', 'EPSG:3857'):
        raise ValueError('Use EPSG:4326 or EPSG:3857 north-up imagery.')
    bounds = value.get('bounds')
    try:
        valid = (isinstance(bounds, list) and len(bounds) == 4 and
                 all(type(v) in (int, float) and math.isfinite(v) for v in bounds))
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError('Imagery bounds must contain four finite numbers.')
    west, south, east, north = bounds
    xlimit, ylimit = (180, 85.05112878) if crs == 'EPSG:4326' else (MERCATOR_EDGE, MERCATOR_EDGE)
    if not (-xlimit <= west < east <= xlimit and -ylimit <= south < north <= ylimit):
        raise ValueError('Invalid or reversed imagery bounds; date-line crossing is not supported.')
    result = dict(schema_version=1, crs=crs, bounds=list(bounds))
    for key, limit in (('source', 500), ('attribution', 2000), ('imagery_date', 200)):
        text = value.get(key)
        if key == 'imagery_date' and text is None:
            result[key] = None
        elif not isinstance(text, str) or not text.strip() or len(text) > limit:
            raise ValueError('Missing or invalid imagery ' + key + '.')
        else:
            result[key] = text.strip()
    kind = value.get('imagery_type', 'aerial')
    if kind not in ('aerial', 'satellite', 'vector', 'reference'):
        raise ValueError('Unknown imagery type.')
    result['imagery_type'] = kind
    return result


def decode_image(raw):
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice
    from PySide6.QtGui import QImageReader
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError('Image must be at most 20 MiB.')
    buffer = QBuffer()
    buffer.setData(QByteArray(raw))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buffer)
    size = reader.size()
    if bytes(reader.format()).lower() not in (b'png', b'jpeg', b'jpg'):
        raise ValueError('Use a PNG or JPEG image.')
    if not (0 < size.width() <= MAX_DIMENSION and 0 < size.height() <= MAX_DIMENSION):
        raise ValueError('Image dimensions must not exceed 2048 pixels.')
    image = reader.read()
    if image.isNull():
        raise ValueError('Image cannot be decoded.')
    return image


def project(lon, lat, crs):
    if not (-180 <= lon <= 180 and -85.05112878 <= lat <= 85.05112878):
        raise ValueError('Position cannot be projected onto this map.')
    if crs == 'EPSG:4326':
        return lon, lat
    return RADIUS * math.radians(lon), RADIUS * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def pixel_position(lon, lat, meta, width, height):
    x, y = project(lon, lat, meta['crs'])
    west, south, east, north = meta['bounds']
    if not (west <= x <= east and south <= y <= north):
        raise ValueError('A survey point is outside the image extent. Expand the area.')
    return ((x - west) / (east - west) * width, (north - y) / (north - south) * height)


def survey_points(config, path):
    from .map_sources import load_survey_map_data
    session = json.loads(Path(path).read_text(encoding='utf-8'))
    model = load_survey_map_data(config, path)
    selected = {f['properties']['run_id']: f for f in model['features']['features']
                if f['id'] in model['representatives'] and f['properties']['renderable']}
    result = []
    for number, step in enumerate(session['steps'], 1):
        feature = selected.get(step['run_id'])
        if feature:
            lon, lat = feature['geometry']['coordinates']
            result.append(dict(number=number, run_id=step['run_id'], label=step['label'],
                               lon=lon, lat=lat, fix_utc=feature['properties'].get('fix_utc')))
    return result


def fingerprint(points):
    return hashlib.sha256(json.dumps(points, sort_keys=True, allow_nan=False).encode()).hexdigest()


def render_image(raw, meta, points):
    from PySide6.QtCore import Qt, QBuffer, QIODevice, QPointF, QRectF
    from PySide6.QtGui import QPainter, QPen, QColor, QFont, QImage
    meta = validate_metadata(meta)
    image = decode_image(raw).scaled(1440, 800, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_RGB32)
    positions = [pixel_position(p['lon'], p['lat'], meta, image.width()-1, image.height()-1) for p in points]
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        for point, (x, y) in zip(points, positions):
            # Keep edge labels visible while the marker center remains georeferenced.
            painter.setPen(QPen(QColor('white'), 2))
            painter.setBrush(QColor('#126759'))
            painter.drawEllipse(QPointF(x, y), 12, 12)
            painter.setPen(QColor('white'))
            painter.drawText(QRectF(max(0, min(x-12, image.width()-24)),
                                   max(0, min(y-12, image.height()-24)), 24, 24),
                             Qt.AlignmentFlag.AlignCenter, str(point['number']))
        painter.fillRect(8, 8, 40, 46, QColor('white'))
        painter.setPen(QPen(QColor('#172131'), 2))
        painter.drawText(20, 25, 'N')
        painter.drawLine(28, 48, 28, 30)
        painter.drawLine(28, 30, 23, 36)
        painter.drawLine(28, 30, 33, 36)
        west, south, east, north = meta['bounds']
        mid = (south+north)/2
        lat = mid if meta['crs']=='EPSG:4326' else math.degrees(2*math.atan(math.exp(mid/RADIUS))-math.pi/2)
        span = (math.radians(east-west)*RADIUS if meta['crs']=='EPSG:4326' else east-west)*math.cos(math.radians(lat))
        target = span/5
        power = 10**math.floor(math.log10(target))
        distance = max(v*power for v in (0.1, 0.2, 0.5, 1, 2, 5) if v*power <= target)
        pixels = max(1, round(distance/span*(image.width()-1)))
        painter.fillRect(8, image.height()-53, max(210,pixels+24), 46, QColor('white'))
        painter.drawLine(18,image.height()-23,18+pixels,image.height()-23)
        painter.drawText(18,image.height()-31, f'{distance/1000:g} km' if distance>=1000 else f'{distance:g} m')
        painter.setFont(QFont('Arial', 8))
        painter.drawText(18,image.height()-10,'Approximate scale at image center')
    finally:
        painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, 'PNG'):
        raise ValueError('Cannot create the report image.')
    return bytes(buffer.data())


def asset_directory(config, path, asset_id):
    from .survey import _session_path
    path = _session_path(config, path)
    if not isinstance(asset_id, str) or not re.fullmatch('[a-f0-9]{32}', asset_id):
        raise ValueError('Invalid imagery asset identifier.')
    base = (config.root / 'survey-assets').resolve()
    target = (base / path.stem / asset_id).resolve()
    if not target.is_relative_to(base):
        raise ValueError('Invalid imagery asset location.')
    return target


def save_imagery(config, path, raw, meta, points):
    from .survey import _session_path, session_lock, _editable_session
    meta = validate_metadata(meta)
    overlay = render_image(raw, meta, points)
    path = _session_path(config, path)
    with session_lock(path):
        session = _editable_session(config, path)
        if fingerprint(survey_points(config, path)) != fingerprint(points):
            raise ValueError('Survey positions changed. Reopen Prepare report map.')
        asset_id = uuid.uuid4().hex
        folder = asset_directory(config, path, asset_id)
        folder.mkdir(parents=True, exist_ok=False)
        meta.update(asset_id=asset_id, prepared_utc=utcnow_iso(), points=points,
                    position_fingerprint=fingerprint(points),
                    missing_points=len(session['steps'])-len(points), manual_area=not bool(points),
                    survey_steps=[s['run_id'] for s in session['steps']],
                    sha256=hashlib.sha256(overlay).hexdigest(), source_sha256=hashlib.sha256(raw).hexdigest())
        (folder/'source.image').write_bytes(raw)
        (folder/'overlay.png').write_bytes(overlay)
        atomic_json(folder/'metadata.json', meta)
        session['report_imagery'] = asset_id
        atomic_json(path, session)
        return meta


def load_imagery(config, path):
    session = json.loads(Path(path).read_text(encoding='utf-8'))
    asset_id = session.get('report_imagery')
    if not asset_id:
        return None
    folder = asset_directory(config, path, asset_id)
    if (folder/'metadata.json').stat().st_size > 65536:
        raise ValueError('Imagery metadata exceeds its size limit.')
    meta = json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    validate_metadata(meta)
    for filename, key, limit in (('source.image','source_sha256',MAX_BYTES),('overlay.png','sha256',5*1024*1024)):
        source = folder/filename
        if source.stat().st_size > limit:
            raise ValueError('Cached imagery exceeds its size limit.')
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta.get(key):
            raise ValueError('Cached imagery integrity check failed.')
    meta['image'] = raw
    meta['asset_dir'] = folder
    return meta


def report_context(config, path):
    try:
        meta = load_imagery(config, path)
        if meta:
            session = json.loads(Path(path).read_text(encoding='utf-8'))
            meta['stale'] = (fingerprint(survey_points(config,path)) != meta['position_fingerprint'] or
                             [s['run_id'] for s in session['steps']] != meta.get('survey_steps', []))
            meta['warning'] = 'Survey positions changed; prepare the report map again.' if meta['stale'] else ''
        return meta
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return dict(warning='Survey imagery unavailable: '+str(exc), image=None)
