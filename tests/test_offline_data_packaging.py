import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from veilbreaker.deployment_data import seed_reference, install_bundled_structures
from tools.prepare_offline_data import prepare
from test_cell_reference import HEADER, ROW
from veilbreaker.map_smoke import synthetic_pack


class OfflinePackagingTests(unittest.TestCase):
    def test_prepare_includes_installable_fcc_structure_snapshot(self):
        from veilbreaker.core import AppConfig
        from tests.test_fcc_asr import archive, ra, co
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); map_file=root/'map.pmtiles'; map_file.write_bytes(synthetic_pack())
            (root/'map.json').write_text(json.dumps({'sha256':hashlib.sha256(map_file.read_bytes()).hexdigest()}))
            cells=root/'311.csv';cells.write_text(HEADER+ROW,encoding='utf-8')
            source=archive(root,[ra()],[co()]);dest=root/'bundle'
            result=prepare(map_file,root/'map.json',cells,dest,{'source':'OpenCellID','license':'test','date':'2026-10-27'},
                           fcc_archive=source,fcc_date='2026-10-25')
            self.assertEqual(result['structure_record_count'],1)
            self.assertEqual(len(result['structure_packs']),1)
            self.assertEqual(install_bundled_structures(AppConfig(data_dir=root/'user'),dest)['records'],1)

    def test_verified_map_and_cell_export_are_prepared_for_installer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            map_file = root / 'map.pmtiles'
            map_file.write_bytes(synthetic_pack())
            (root / 'map.json').write_text(json.dumps({'sha256': hashlib.sha256(map_file.read_bytes()).hexdigest(),
                'source_build': '2026-10-19', 'source_url': 'https://example.com/map'}))
            cells = root / '311.csv'
            cells.write_text(HEADER + ROW, encoding='utf-8')
            destination = root / 'bundle'
            result = prepare(map_file, root / 'map.json', cells, destination,
                {'source': 'OpenCellID country export', 'license': 'CC BY-SA 4.0', 'date': '2026-10-27'})
            self.assertEqual(result['cell_rows'], 1)
            self.assertTrue((destination / 'maps' / 'CONUS-overview.pmtiles').exists())
            self.assertEqual(seed_reference(root / 'user', destination)['source'], 'OpenCellID country export')

    def test_bad_map_checksum_leaves_no_staged_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            map_file = root / 'map.pmtiles'
            map_file.write_bytes(synthetic_pack())
            (root / 'map.json').write_text(json.dumps({'sha256': '0' * 64}))
            cells = root / '311.csv'
            cells.write_text(HEADER + ROW, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                prepare(map_file, root / 'map.json', cells, root / 'bundle',
                    {'source': 'OpenCellID', 'license': 'CC BY-SA 4.0', 'date': 'Unknown'})
            self.assertFalse((root / 'bundle').exists())


if __name__ == '__main__':
    unittest.main()
