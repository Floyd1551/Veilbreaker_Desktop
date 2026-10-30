"""Build a regional physical-structure pack from an FCC ASR registration ZIP.

The FCC's ASR public access documentation describes RA and CO records joined
on registration number: https://wireless.fcc.gov/uls/documentation/towintro-1.pdf
ASR is incomplete and neither identifies a serving cell nor proves a structure
still exists. Coordinates are filed as NAD83; they are used as an approximate
WGS84 position here, without a datum transformation or accuracy claim.
"""
import datetime
import hashlib
import json
import math
import re
import tempfile
import zipfile
from pathlib import Path

from .regional_packs import _bounds

FCC_URL = 'https://data.fcc.gov/download/pub/uls/complete/r_tower.zip'
MAX_ARCHIVE = 2 * 1024 ** 3
MAX_MEMBER = 2 * 1024 ** 3
MAX_LINE = 16384


def _check(cancelled):
    if cancelled():
        raise ValueError('FCC ASR import cancelled.')


def _lines(zf, member, code, minimum, cancelled):
    info = member
    if info.file_size > MAX_MEMBER:
        raise ValueError('FCC ASR archive member exceeds the size limit.')
    with zf.open(info) as stream:
        while True:
            _check(cancelled)
            raw = stream.readline(MAX_LINE + 1)
            if not raw:
                break
            if len(raw) > MAX_LINE:
                raise ValueError('FCC ASR record exceeds the line size limit.')
            fields = raw.decode('utf-8', errors='replace').rstrip('\r\n').split('|')
            if fields[0] != code or len(fields) < minimum:
                raise ValueError('Unsupported FCC ASR record schema in ' + info.filename)
            if fields[1].strip() != 'REG':
                raise ValueError('Use the FCC complete registration archive, not applications or determinations.')
            yield fields


def _coordinate(degrees, minutes, seconds, direction, latitude):
    try:
        deg, minute, sec = int(degrees), int(minutes), float(seconds)
    except ValueError:
        return None
    limit = 90 if latitude else 180
    allowed = ('N', 'S') if latitude else ('E', 'W')
    if (direction not in allowed or not math.isfinite(sec) or deg < 0 or minute < 0
            or minute >= 60 or sec < 0 or sec >= 60 or deg > limit
            or (deg == limit and (minute or sec))):
        return None
    value = deg + minute / 60 + sec / 3600
    return -value if direction in ('S', 'W') else value


def install_fcc_asr(store, archive, bounds, source_date, name, cancelled, progress=lambda _: None):
    """Select constructed registrations with valid tower points and install atomically."""
    _check(cancelled)
    bounds = _bounds(bounds)
    west, south, east, north = bounds
    if east - west > 5 or north - south > 5:
        raise ValueError('Select a region no larger than 5° × 5°.')
    try:
        datetime.date.fromisoformat(source_date)
    except (ValueError, TypeError):
        raise ValueError('Enter the FCC archive publication date as YYYY-MM-DD.') from None
    source = Path(archive)
    if not source.is_file() or source.is_symlink() or source.stat().st_size > MAX_ARCHIVE:
        raise ValueError('Choose a local FCC ASR ZIP within the 2 GiB limit.')
    digest = hashlib.sha256()
    with source.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            _check(cancelled)
            digest.update(chunk)
    archive_hash = digest.hexdigest()
    progress('Reading FCC coordinates…')
    try:
        with zipfile.ZipFile(source) as zf:
            members = {}
            for info in zf.infolist():
                if info.filename.replace('\\', '/').split('/')[-1].upper() in ('RA.DAT', 'CO.DAT'):
                    key = info.filename.replace('\\', '/').split('/')[-1].upper()
                    if key in members or info.is_dir():
                        raise ValueError('FCC archive has duplicate data members.')
                    members[key] = info
            if set(members) != {'RA.DAT', 'CO.DAT'}:
                raise ValueError('FCC registration ZIP must contain RA.dat and CO.dat.')
            positions = {}
            for row in _lines(zf, members['CO.DAT'], 'CO', 15, cancelled):
                reg = row[3].strip()
                if row[5].strip() != 'T' or not re.fullmatch(r'\d{7}', reg):
                    continue
                lat = _coordinate(*row[6:10], True)
                # FCC CO.dat includes latitude_total_seconds at index 10.
                lon = _coordinate(*row[11:15], False)
                if lat is None or lon is None or not west <= lon <= east or not south <= lat <= north:
                    continue
                if reg in positions:
                    raise ValueError('FCC archive contains multiple tower coordinates for registration ' + reg)
                positions[reg] = [lon, lat]
                if len(positions) > 100000:
                    raise ValueError('Too many regional structures; choose a smaller region.')
            progress('Reading constructed registrations…')
            features, seen = [], set()
            for row in _lines(zf, members['RA.DAT'], 'RA', 31, cancelled):
                reg = row[3].strip()
                if reg not in positions or row[8].strip() != 'C' or row[13].strip():
                    continue
                if reg in seen:
                    raise ValueError('FCC archive contains duplicate constructed registrations: ' + reg)
                seen.add(reg)
                properties = {'structure_id': 'FCC ASR ' + reg, 'registration_number': reg,
                              'registration_status': 'Constructed', 'position_source': 'FCC ASR NAD83 (approximate WGS84)'}
                try:
                    height = float(row[30])
                    if math.isfinite(height) and 0 <= height <= 2000:
                        properties['height_agl_m'] = height
                except ValueError:
                    pass
                features.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': positions[reg]},
                                 'properties': properties})
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise ValueError('Unable to read FCC ASR ZIP: ' + str(exc)) from exc
    if not features:
        raise ValueError('No constructed FCC tower points found in the selected region.')
    metadata = {'name': name, 'source': 'FCC ASR registrations; ' + FCC_URL + '; input ZIP SHA-256 ' + archive_hash,
                'license': 'FCC public access data; U.S. government content; verify rights for third-party submissions',
                'source_date': source_date, 'bounds_wgs84': bounds}
    progress('Installing regional structure pack…')
    with tempfile.TemporaryDirectory(prefix='veilbreaker-asr-') as temporary:
        path = Path(temporary) / 'structures.geojson'
        path.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}), encoding='utf-8')
        installed = store.install_local('structures', path, metadata, cancelled)
    return {'installed': installed, 'archive_sha256': archive_hash}
