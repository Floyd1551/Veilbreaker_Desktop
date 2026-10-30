"""Explicit HTTPS transfer into the managed regional-pack validator."""
import hashlib
import re
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .regional_packs import MAX_STRUCTURES_BYTES, MAX_TERRAIN_BYTES


def sanitized_source_url(url):
    if not isinstance(url, str) or len(url) > 4096:
        raise ValueError('Enter an HTTPS download URL.')
    parsed = urlsplit(url)
    if parsed.scheme.lower() != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Download URL must use HTTPS without embedded credentials.')
    return urlunsplit(('https', parsed.hostname + (f':{parsed.port}' if parsed.port else ''), parsed.path, '', ''))


class _HttpsRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        sanitized_source_url(newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


def download_and_install(store, kind, url, metadata, cancelled, progress=lambda _: None,
                         expected_sha256=None, max_bytes=None, opener=None):
    """Download a user-selected pack; register it only after full validation."""
    requested_origin = sanitized_source_url(url)
    if kind not in ('terrain', 'structures'):
        raise ValueError('Choose terrain or physical structures.')
    limit = MAX_TERRAIN_BYTES if kind == 'terrain' else MAX_STRUCTURES_BYTES
    if max_bytes is not None:
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError('Invalid download size limit.')
        limit = min(limit, max_bytes)
    if expected_sha256 is not None and not re.fullmatch(r'[a-fA-F0-9]{64}', expected_sha256):
        raise ValueError('Expected checksum must be a SHA-256 hex digest.')
    if cancelled():
        raise ValueError('Pack download cancelled.')
    store.root.mkdir(parents=True, exist_ok=True)
    suffix = '.tif' if kind == 'terrain' else '.geojson'
    temporary = store.root / ('.download-' + uuid.uuid4().hex + suffix)
    opener = opener or urllib.request.build_opener(_HttpsRedirect()).open
    digest = hashlib.sha256()
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Veilbreaker/RegionalPacks'})
        with opener(request, timeout=20) as response:
            origin = sanitized_source_url(response.geturl())
            length = response.headers.get('Content-Length')
            if length is not None and (not length.isdigit() or int(length) > limit):
                raise ValueError('Pack download exceeds the size limit.')
            size = 0
            with temporary.open('wb') as output:
                while chunk := response.read(1024 * 1024):
                    if cancelled():
                        raise ValueError('Pack download cancelled.')
                    size += len(chunk)
                    if size > limit:
                        raise ValueError('Pack download exceeds the size limit.')
                    output.write(chunk)
                    digest.update(chunk)
                    progress({'bytes': size, 'phase': 'download'})
        if not size:
            raise ValueError('Pack download is empty.')
        if expected_sha256 and digest.hexdigest().lower() != expected_sha256.lower():
            raise ValueError('Pack download checksum does not match the expected SHA-256.')
        details = dict(metadata, download_origin=origin, download_requested_origin=requested_origin,
                       download_integrity='expected SHA-256 matched' if expected_sha256 else 'computed SHA-256 only')
        return store.install_local(kind, temporary, details, cancelled,
                                   lambda value: progress(dict(value, phase='install')))
    finally:
        temporary.unlink(missing_ok=True)


def download_terrain_batch(store, products, datum, units, cancelled, progress=lambda _: None,
                           install=None):
    """Install a reviewed, bounded selection; preserve completed tiles on interruption."""
    if not isinstance(products, (list, tuple)) or not 1 <= len(products) <= 20:
        raise ValueError('Select between 1 and 20 terrain tiles.')
    if not isinstance(datum, str) or not datum.strip() or units not in ('m', 'ft', 'us-ft'):
        raise ValueError('Confirm the vertical datum and elevation units for these tiles.')
    # Validate the whole selection before any transfer.
    for product in products:
        if not isinstance(product, dict) or any(not isinstance(product.get(key), str) or not product[key].strip()
                                                for key in ('title', 'source', 'license', 'source_date', 'url')):
            raise ValueError('Each selected tile must have a title, source, license, date and URL.')
        sanitized_source_url(product['url'])
    install = install or download_and_install
    candidates = [row for row in store.list_packs()
                  if row.get('status') == 'available' and row.get('kind') == 'terrain']
    verified_origins = set()
    seen, result = set(), []
    stopped = False
    total = len(products)
    for index, product in enumerate(products, 1):
        origin = sanitized_source_url(product['url'])
        entry = {'title': product['title'], 'url': origin}
        if stopped:
            entry['status'] = 'not attempted'
        elif cancelled():
            entry['status'] = 'cancelled'
            stopped = True
        elif origin in verified_origins or origin in seen:
            entry['status'] = 'skipped'
        else:
            metadata = dict(name=product['title'], source=product['source'], license=product['license'],
                            source_date=product['source_date'], vertical_datum=datum.strip(), units=units)
            progress(dict(event='starting', index=index, total=total, title=product['title']))
            def report(value):
                progress(dict(value, event='progress', index=index, total=total,
                              title=product['title'], estimated_bytes=product.get('bytes')))
            try:
                match = False
                metadata_conflict = False
                for candidate in candidates:
                    origins = {candidate.get('download_origin'), candidate.get('download_requested_origin')}
                    if origin not in origins:
                        continue
                    progress(dict(event='progress', phase='verify', index=index, total=total, title=product['title']))
                    try:
                        match = store.verify(candidate['pack_id'], cancelled)
                    except (OSError, ValueError, KeyError):
                        if cancelled():
                            raise ValueError('Pack verification cancelled.')
                        match = False
                    if match and (str(candidate.get('vertical_datum') or '').strip().casefold() != datum.strip().casefold()
                                  or candidate.get('units') != units):
                        metadata_conflict = True
                        match = False
                    if match:
                        verified_origins.update(o for o in origins if o)
                        break
                if cancelled():
                    raise ValueError('Pack verification cancelled.')
                if match:
                    entry['status'] = 'skipped'
                elif metadata_conflict:
                    raise ValueError('An existing verified tile has different or missing datum or units. Review the existing pack and remove or re-import it with the correct declaration before retrying.')
                else:
                    row = install(store, 'terrain', product['url'], metadata, cancelled, report)
                    entry.update(status='installed', pack=row)
                    verified_origins.update((origin, row.get('download_origin'), row.get('download_requested_origin')))
                seen.add(origin)
            except Exception as exc:
                entry.update(status='cancelled' if cancelled() else 'failed', error=str(exc))
                stopped = True
        result.append(entry)
        progress(dict(event='result', index=index, total=total, title=entry['title'], status=entry['status']))
    return result
