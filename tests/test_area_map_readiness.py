import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_map_pack import pack_bytes
from veilbreaker.area_map_readiness import check_catalog_maps
from veilbreaker.map_catalog import PackCatalog


class AreaMapReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalog = self.root / 'catalog.json'
        self.area = [-87, 34, -86, 35]

    def test_valid_registered_header_is_not_claimed_checksum_verified(self):
        path = self.root / 'map.pmtiles'
        path.write_bytes(pack_bytes())
        PackCatalog(self.catalog).register(path)
        report = check_catalog_maps(self.catalog, None, self.area, lambda: False)
        self.assertEqual(len(report['entries']), 1)
        self.assertEqual(report['entries'][0]['checksum_status'], 'not_checked')
        self.assertTrue(report['complete'])

    def test_changed_or_truncated_map_is_not_available(self):
        path = self.root / 'map.pmtiles'
        path.write_bytes(pack_bytes())
        PackCatalog(self.catalog).register(path)
        path.write_bytes(b'bad')
        report = check_catalog_maps(self.catalog, None, self.area, lambda: False)
        self.assertEqual(report['entries'], [])
        self.assertIn(report['rejected'][0]['status'], ('invalid', 'changed'))
        self.assertIn('not', report['rejected'][0]['detail'].lower())

    def test_replaced_valid_archive_with_new_bounds_is_not_silently_accepted(self):
        import struct
        path = self.root / 'map.pmtiles'
        raw = pack_bytes(); path.write_bytes(raw)
        PackCatalog(self.catalog).register(path)
        modified = bytearray(raw)
        struct.pack_into('<4i', modified, 102, -1000000000, 300000000, -900000000, 400000000)
        path.write_bytes(modified)
        report = check_catalog_maps(self.catalog, None, self.area, lambda: False)
        self.assertFalse(report['entries'])
        self.assertEqual(report['rejected'][0]['status'], 'changed')

    def test_malformed_catalog_or_included_does_not_hide_other_map(self):
        self.catalog.write_text('{broken', encoding='utf-8')
        path = self.root / 'included.pmtiles'
        path.write_bytes(pack_bytes())
        report = check_catalog_maps(self.catalog, path, self.area, lambda: False)
        self.assertFalse(report['complete'])
        self.assertEqual(len(report['entries']), 1)
        self.assertTrue(report['warnings'])
        path.write_bytes(b'broken')
        report = check_catalog_maps(self.root / 'missing.json', path, self.area, lambda: False)
        self.assertEqual(report['entries'], [])
        self.assertEqual(report['rejected'][0]['status'], 'invalid')
        self.assertFalse(report['complete'])

    def test_checksum_optional_local_sidecar_and_same_size_tamper(self):
        path = self.root / 'map.pmtiles'
        data = pack_bytes(); path.write_bytes(data)
        PackCatalog(self.catalog).register(path)
        report = check_catalog_maps(self.catalog, None, self.area, lambda: False, verify_checksum=True)
        self.assertEqual(report['entries'][0]['checksum_status'], 'unavailable')
        path.with_suffix('.json').write_text(json.dumps({'sha256': hashlib.sha256(data).hexdigest()}), encoding='utf-8')
        report = check_catalog_maps(self.catalog, None, self.area, lambda: False, verify_checksum=True)
        self.assertEqual(report['entries'][0]['checksum_status'], 'verified')
        altered = bytearray(data); altered[-1] ^= 1; path.write_bytes(altered)
        report = check_catalog_maps(self.catalog, None, self.area, lambda: False, verify_checksum=True)
        self.assertFalse(report['entries'])
        self.assertEqual(report['rejected'][0]['status'], 'checksum_mismatch')

    def test_included_manifest_digest_and_cancel(self):
        folder = self.root / 'offline-data' / 'maps'; folder.mkdir(parents=True)
        path = folder / 'CONUS-overview.pmtiles'; data = pack_bytes(); path.write_bytes(data)
        (folder.parent / 'manifest.json').write_text(json.dumps({'map_sha256': hashlib.sha256(data).hexdigest()}))
        report = check_catalog_maps(self.catalog, path, self.area, lambda: False, verify_checksum=True)
        self.assertEqual(report['entries'][0]['checksum_status'], 'verified')
        self.assertIn('included', report['entries'][0]['checksum_source'].lower())
        with self.assertRaisesRegex(ValueError, 'cancel'):
            check_catalog_maps(self.catalog, path, self.area, lambda: True)

    def test_registered_included_map_uses_manifest_even_with_different_path_spelling(self):
        folder = self.root / 'offline-data' / 'maps'; folder.mkdir(parents=True)
        path = folder / 'CONUS-overview.pmtiles'; data = pack_bytes(); path.write_bytes(data)
        (folder.parent / 'manifest.json').write_text(json.dumps({'map_sha256': hashlib.sha256(data).hexdigest()}))
        row = PackCatalog(self.catalog).register(path)
        # Equivalent path string, but not byte-for-byte equal to the canonical path.
        row['path'] = str(folder / '.' / '..' / 'maps' / path.name)
        self.catalog.write_text(json.dumps([row]), encoding='utf-8')
        report = check_catalog_maps(self.catalog, path, self.area, lambda: False, verify_checksum=True)
        self.assertEqual(len(report['entries']), 1)
        self.assertEqual(report['entries'][0]['checksum_status'], 'verified')
        self.assertEqual(report['entries'][0]['checksum_source'], 'included local manifest')

    def test_remote_paths_are_not_opened(self):
        self.catalog.write_text(json.dumps([{'path': r'\\\\server\share\map.pmtiles'}]), encoding='utf-8')
        with patch('veilbreaker.area_map_readiness.inspect_pack') as inspect:
            report = check_catalog_maps(self.catalog, None, self.area, lambda: False)
        inspect.assert_not_called()
        self.assertEqual(report['rejected'][0]['status'], 'unsupported_remote')
        self.assertFalse(report['complete'])

    def test_cancel_during_checksum_is_not_reported_as_damaged_map(self):
        path = self.root / 'map.pmtiles'; data = pack_bytes() + b'x' * (2 * 1024 * 1024)
        path.write_bytes(data)
        path.with_suffix('.json').write_text(json.dumps({'sha256': hashlib.sha256(data).hexdigest()}))
        PackCatalog(self.catalog).register(path)
        calls = iter([False, False, True])
        with self.assertRaisesRegex(ValueError, 'cancel'):
            check_catalog_maps(self.catalog, None, self.area, lambda: next(calls, True), verify_checksum=True)


if __name__ == '__main__':
    unittest.main()
