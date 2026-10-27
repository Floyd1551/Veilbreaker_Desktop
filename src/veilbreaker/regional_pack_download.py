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
    sanitized_source_url(url)
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
                    progress({'bytes': size})
        if not size:
            raise ValueError('Pack download is empty.')
        if expected_sha256 and digest.hexdigest().lower() != expected_sha256.lower():
            raise ValueError('Pack download checksum does not match the expected SHA-256.')
        details = dict(metadata, download_origin=origin,
                       download_integrity='expected SHA-256 matched' if expected_sha256 else 'computed SHA-256 only')
        return store.install_local(kind, temporary, details, cancelled, progress)
    finally:
        temporary.unlink(missing_ok=True)
