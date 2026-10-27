import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from tests.test_regional_packs import structures
from veilbreaker.regional_packs import RegionalPackStore
from veilbreaker.regional_pack_download import download_and_install, sanitized_source_url


class Response(io.BytesIO):
    def __init__(self, data, url):
        super().__init__(data)
        self.url = url
        self.headers = {'Content-Length': str(len(data))}

    def geturl(self):
        return self.url


class RegionalDownloadTests(unittest.TestCase):
    def test_https_download_installs_and_scrubs_query(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'input.geojson'
            structures(source)
            data = source.read_bytes()
            store = RegionalPackStore(root / 'packs')
            url = 'https://example.org/structures.geojson?access_token=secret'
            meta = dict(name='Structures', source='Example', license='Test only', source_date='2026-10-27',
                        bounds_wgs84=[-97.1, 32.8, -96.8, 33.1])
            row = download_and_install(store, 'structures', url, meta, lambda: False,
                                       expected_sha256=hashlib.sha256(data).hexdigest(),
                                       opener=lambda request, timeout: Response(data, url))
            self.assertEqual(row['download_origin'], 'https://example.org/structures.geojson')
            self.assertNotIn('secret', (store.root / row['pack_id'] / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(len(store.list_packs()), 1)
            self.assertEqual(list(store.root.glob('.download-*')), [])

    def test_bad_scheme_hash_size_and_cancel_leave_no_pack(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'input.geojson'
            structures(source)
            data = source.read_bytes()
            store = RegionalPackStore(root / 'packs')
            meta = dict(name='Structures', source='Example', license='Test only', source_date='2026-10-27',
                        bounds_wgs84=[-97.1, 32.8, -96.8, 33.1])
            with self.assertRaises(ValueError):
                sanitized_source_url('http://example.org/file.geojson')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                download_and_install(store, 'structures', 'https://example.org/file.geojson', meta, lambda: False,
                                     expected_sha256='0' * 64,
                                     opener=lambda request, timeout: Response(data, 'https://example.org/file.geojson'))
            with self.assertRaisesRegex(ValueError, 'size'):
                download_and_install(store, 'structures', 'https://example.org/file.geojson', meta, lambda: False,
                                     max_bytes=10, opener=lambda request, timeout: Response(data, 'https://example.org/file.geojson'))
            with self.assertRaisesRegex(ValueError, 'cancelled'):
                download_and_install(store, 'structures', 'https://example.org/file.geojson', meta, lambda: True,
                                     opener=lambda request, timeout: Response(data, 'https://example.org/file.geojson'))
            self.assertEqual(store.list_packs(), [])
            self.assertEqual(list(store.root.glob('.download-*')), [])


if __name__ == '__main__':
    unittest.main()
