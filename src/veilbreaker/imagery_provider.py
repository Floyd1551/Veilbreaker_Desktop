"""Explicit, bounded USGS NAIP acquisition. Report viewing never calls this module."""
import json
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import build_opener, HTTPRedirectHandler
from .survey_imagery import MAX_BYTES, validate_metadata

SERVICE = 'https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer'


def check_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'imagery.nationalmap.gov'
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError('Imagery URL is not an approved USGS HTTPS endpoint.')


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = build_opener(Redirects())


def _read(url, cancelled, limit):
    check_url(url)
    chunks, length = [], 0
    deadline = time.monotonic() + 45
    if cancelled():
        raise ValueError('Imagery preparation cancelled.')
    with OPENER.open(url, timeout=10) as response:
        while True:
            if cancelled():
                raise ValueError('Imagery preparation cancelled.')
            if time.monotonic() > deadline:
                raise ValueError('Imagery request timed out.')
            chunk = response.read(min(65536, limit + 1 - length))
            if not chunk:
                break
            length += len(chunk)
            if length > limit:
                raise ValueError('Imagery response exceeds its size limit.')
            chunks.append(chunk)
    return b''.join(chunks)


def _json(url, cancelled):
    value = json.loads(_read(url, cancelled, 1024*1024))
    if not isinstance(value, dict):
        raise ValueError('Invalid USGS response.')
    if value.get('error'):
        raise ValueError('USGS imagery: ' + str(value['error'].get('message', 'Unavailable'))[:500])
    return value


def fetch_naip(bounds, cancelled):
    meta = validate_metadata(dict(schema_version=1, crs='EPSG:4326', bounds=bounds,
                                 source='USGS NAIP', attribution='USGS / USDA', imagery_date=None))
    if cancelled():
        raise ValueError('Imagery preparation cancelled.')
    service = _json(SERVICE+'?f=json', cancelled)
    query = urlencode(dict(bbox=','.join(map(str, bounds)), bboxSR=4326, imageSR=3857,
                           size='1600,1000', format='jpg', f='json', adjustAspectRatio='true'))
    result = _json(SERVICE+'/exportImage?'+query, cancelled)
    extent = result.get('extent', {})
    reference = extent.get('spatialReference', {})
    if reference.get('latestWkid', reference.get('wkid')) not in (3857, 102100):
        raise ValueError('USGS returned an unsupported image projection.')
    meta.update(crs='EPSG:3857', bounds=[extent.get(k) for k in ('xmin','ymin','xmax','ymax')],
                attribution=service.get('copyrightText') or 'USGS, USDA, The National Map')
    meta = validate_metadata(meta)
    href = result.get('href')
    if not isinstance(href, str):
        raise ValueError('USGS did not return an image.')
    return _read(href, cancelled, MAX_BYTES), meta
