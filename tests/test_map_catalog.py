import tempfile
import unittest
from pathlib import Path
from test_map_pack import pack_bytes
from veilbreaker.map_catalog import PackCatalog


class CatalogTests(unittest.TestCase):
    def test_register_replace_missing_and_remove_preserves_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pack = root / 'region.pmtiles'
            pack.write_bytes(pack_bytes())
            catalog = PackCatalog(root / 'catalog.json')
            entry = catalog.register(pack)
            self.assertEqual(entry['bounds'], [-180, -85, 180, 85])
            catalog.register(pack)
            self.assertEqual(len(catalog.entries()), 1)
            self.assertTrue(catalog.entries()[0]['available'])
            catalog.remove(pack)
            self.assertTrue(pack.is_file())
            self.assertEqual(catalog.entries(), [])
            catalog.register(pack)
            pack.unlink()
            self.assertFalse(catalog.entries()[0]['available'])

    def test_bad_archive_does_not_replace_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pack = root / 'region.pmtiles'
            pack.write_bytes(pack_bytes())
            catalog = PackCatalog(root / 'catalog.json')
            catalog.register(pack)
            before = catalog.path.read_bytes()
            pack.write_bytes(b'bad')
            with self.assertRaises(ValueError):
                catalog.register(pack)
            self.assertEqual(catalog.path.read_bytes(), before)
