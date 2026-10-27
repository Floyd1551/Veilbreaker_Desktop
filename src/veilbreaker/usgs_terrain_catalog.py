"""Bounded product discovery from the official USGS TNM Access API."""
import json
import urllib.parse
import urllib.request

from .regional_pack_download import sanitized_source_url
from .regional_packs import MAX_TERRAIN_BYTES, _bounds

API = 'https://tnmaccess.nationalmap.gov/api/v1/products'
DATASET = 'National Elevation Dataset (NED) 1/3 arc-second'


def search_terrain_products(bounds_wgs84, cancelled=lambda: False, progress=lambda _: None, opener=None):
    west, south, east, north = _bounds(bounds_wgs84)
    if east - west > 2 or north - south > 2:
        raise ValueError('Search an area no larger than 2° × 2° at a time.')
    if cancelled():
        raise ValueError('Terrain product search cancelled.')
    query = urllib.parse.urlencode({'bbox': f'{west:g},{south:g},{east:g},{north:g}',
                                    'datasets': DATASET, 'max': 100})
    request = urllib.request.Request(API + '?' + query, headers={'User-Agent': 'Veilbreaker/TerrainCatalog'})
    opener = opener or urllib.request.urlopen
    with opener(request, timeout=20) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if cancelled():
        raise ValueError('Terrain product search cancelled.')
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('USGS product response is too large.')
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError('USGS product response is invalid.') from exc
    if not isinstance(document, dict) or not isinstance(document.get('items'), list):
        raise ValueError('USGS product response has no items list.')
    products = []
    for item in document['items'][:100]:
        if not isinstance(item, dict) or item.get('format') != 'GeoTIFF':
            continue
        url, title, size = item.get('downloadURL'), item.get('title'), item.get('sizeInBytes')
        if not isinstance(title, str) or not title.strip() or len(title) > 240 or type(size) is not int or not 0 < size <= MAX_TERRAIN_BYTES:
            continue
        try:
            sanitized_source_url(url)
        except ValueError:
            continue
        if not urllib.parse.urlsplit(url).path.lower().endswith(('.tif', '.tiff')):
            continue
        reported = item.get('boundingBox')
        try:
            coverage = _bounds([reported['minX'], reported['minY'], reported['maxX'], reported['maxY']])
        except (TypeError, KeyError, ValueError):
            coverage = None
        products.append(dict(title=title.strip(), source_date=item.get('publicationDate') or 'Unknown',
                             bytes=size, url=url, reported_bounds_wgs84=coverage,
                             source='USGS The National Map · 3DEP 1/3 arc-second', license='USGS public domain',
                             product_id=item.get('sourceId')))
    products.sort(key=lambda value: (value['source_date'], value['title']), reverse=True)
    total = document.get('total')
    return {'products': products, 'total': total if type(total) is int and total >= 0 else len(products),
            'query_bounds_wgs84': [west, south, east, north],
            'catalog_source': API, 'truncated': len(document['items']) >= 100}
