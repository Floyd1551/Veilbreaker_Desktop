import unittest
import tempfile
from pathlib import Path

from veilbreaker.regional_pack_download import download_terrain_batch


def product(index):
    return dict(title=f'Tile {index}', source='USGS', license='Public domain',
                source_date='2026-01-01', bytes=1000,
                url=f'https://example.org/{index}.tif')


class Store:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def list_packs(self):
        return self.rows

    def verify(self, pack_id, cancelled):
        return True


class TerrainBatchTests(unittest.TestCase):
    def test_skips_installed_and_duplicate_sources_and_reports_stages(self):
        store = Store([dict(status='available', kind='terrain', pack_id='test', download_origin=product(1)['url'],
                            vertical_datum='NAVD88', units='m')])
        calls, events = [], []
        def install(store, kind, url, metadata, cancelled, progress):
            calls.append((url, metadata))
            progress({'bytes': 512, 'phase': 'download'})
            return dict(name=metadata['name'])
        result = download_terrain_batch(store, [product(1), product(2), product(2)],
                                        'NAVD88', 'm', lambda: False, events.append, install)
        self.assertEqual([row['status'] for row in result], ['skipped', 'installed', 'skipped'])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]['source'], 'USGS')
        self.assertEqual(calls[0][1]['vertical_datum'], 'NAVD88')
        self.assertTrue(any(e.get('phase') == 'download' and e.get('bytes') == 512 for e in events))

    def test_stops_on_error_or_cancel_and_retains_completed(self):
        for cancel in (False, True):
            active = [False]
            def install(store, kind, url, metadata, cancelled, progress):
                if metadata['name'] == 'Tile 1':
                    if cancel: active[0] = True
                    return {'name': 'Tile 1'}
                raise ValueError('bad tile')
            result = download_terrain_batch(Store(), [product(1), product(2), product(3)],
                                            'NAVD88', 'm', lambda: active[0], install=install)
            expected = ['installed', 'cancelled', 'not attempted'] if cancel else ['installed', 'failed', 'not attempted']
            self.assertEqual([row['status'] for row in result], expected)
            if not cancel: self.assertIn('bad tile', result[1]['error'])

    def test_rejects_missing_metadata_and_excessive_selection_before_install(self):
        for products, datum, units in [([product(1)], '', 'm'), ([product(1)], 'NAVD88', 'Select elevation units'),
                                      ([product(i) for i in range(21)], 'NAVD88', 'm')]:
            with self.assertRaises(ValueError):
                download_terrain_batch(Store(), products, datum, units, lambda: False)

    def test_real_installer_preserves_completed_tile_and_retry_skips_it(self):
        from tests.test_terrain_raster import make_dem, rasterio
        from tests.test_regional_pack_download import Response
        from veilbreaker.regional_packs import RegionalPackStore
        from veilbreaker.regional_pack_download import download_and_install
        if rasterio is None:
            self.skipTest('terrain dependencies unavailable')
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'fixture.tif'
            make_dem(source, True)
            data = source.read_bytes()
            store = RegionalPackStore(Path(folder) / 'packs')
            def install(store, kind, url, metadata, cancelled, progress):
                if url == product(2)['url']:
                    raise ValueError('fixture failure')
                return download_and_install(store, kind, url, metadata, cancelled, progress,
                                            opener=lambda request, timeout: Response(data, url))
            result = download_terrain_batch(store, [product(1), product(2)], 'NAVD88', 'm', lambda: False, install=install)
            self.assertEqual([row['status'] for row in result], ['installed', 'failed'])
            rows = store.list_packs()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['source'], 'USGS')
            self.assertEqual(rows[0]['download_origin'], product(1)['url'])
            self.assertEqual(rows[0]['download_integrity'], 'computed SHA-256 only')
            self.assertEqual(list(store.root.glob('.download-*')), [])
            again = download_terrain_batch(store, [product(1), product(2)], 'NAVD88', 'm', lambda: False, install=install)
            self.assertEqual([row['status'] for row in again], ['skipped', 'failed'])

    def test_redirect_retry_verifies_and_reinstalls_same_size_corruption(self):
        from tests.test_terrain_raster import make_dem, rasterio
        from tests.test_regional_pack_download import Response
        from veilbreaker.regional_packs import RegionalPackStore
        from veilbreaker.regional_pack_download import download_and_install
        if rasterio is None:
            self.skipTest('terrain dependencies unavailable')
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'fixture.tif'
            make_dem(source, True)
            data = source.read_bytes()
            store = RegionalPackStore(Path(folder) / 'packs')
            requests = []
            def install(store, kind, url, metadata, cancelled, progress):
                requests.append(url)
                return download_and_install(store, kind, url + '?secret=value', metadata, cancelled, progress,
                                           opener=lambda request, timeout: Response(data, 'https://cdn.example.org/tile.tif?token=secret'))
            tile = product(1)
            first = download_terrain_batch(store, [tile], 'NAVD88', 'm', lambda: False, install=install)
            row = first[0]['pack']
            self.assertEqual(row['download_requested_origin'], tile['url'])
            self.assertEqual(row['download_origin'], 'https://cdn.example.org/tile.tif')
            self.assertNotIn('secret', (store.root / row['pack_id'] / 'manifest.json').read_text())
            second = download_terrain_batch(store, [tile], 'NAVD88', 'm', lambda: False, install=install)
            self.assertEqual(second[0]['status'], 'skipped')
            self.assertEqual(len(requests), 1)
            path = store.data_path(row['pack_id'])
            data_changed = bytearray(path.read_bytes()); data_changed[-1] ^= 1
            path.write_bytes(data_changed)
            self.assertEqual(store.list_packs()[0]['status'], 'available')
            third = download_terrain_batch(store, [tile], 'NAVD88', 'm', lambda: False, install=install)
            self.assertEqual(third[0]['status'], 'installed')
            self.assertEqual(len(requests), 2)

    def test_structure_with_same_url_does_not_suppress_terrain(self):
        rows = [dict(status='available', kind='structures', pack_id='test', download_origin=product(1)['url'])]
        calls = []
        def install(store, kind, url, metadata, cancelled, progress):
            calls.append(url)
            return {'name': metadata['name']}
        result = download_terrain_batch(Store(rows), [product(1)], 'NAVD88', 'm', lambda: False, install=install)
        self.assertEqual(result[0]['status'], 'installed')
        self.assertEqual(len(calls), 1)

    def test_legacy_manifest_final_origin_still_deduplicates_after_verification(self):
        rows = [dict(status='available', kind='terrain', pack_id='legacy', download_origin=product(1)['url'],
                     vertical_datum='NAVD88', units='m')]
        store = Store(rows)
        result = download_terrain_batch(store, [product(1)], 'NAVD88', 'm', lambda: False,
                                        install=lambda *args: self.fail('legacy pack should be verified and skipped'))
        self.assertEqual(result[0]['status'], 'skipped')

    def test_confirmed_datum_or_units_conflict_stops_without_installing(self):
        for datum, units in [('EGM96', 'm'), ('NAVD88', 'ft'), ('', 'm')]:
            rows = [dict(status='available', kind='terrain', pack_id='existing',
                         download_origin=product(1)['url'], vertical_datum=datum, units=units)]
            result = download_terrain_batch(Store(rows), [product(1), product(2)], 'NAVD88', 'm', lambda: False,
                                            install=lambda *args: self.fail('conflict must not install'))
            self.assertEqual([row['status'] for row in result], ['failed', 'not attempted'])
            self.assertIn('datum or units', result[0]['error'])

    def test_matching_verified_declaration_is_used_despite_another_conflict(self):
        rows = [dict(status='available', kind='terrain', pack_id='wrong', download_origin=product(1)['url'],
                     vertical_datum='EGM96', units='m'),
                dict(status='available', kind='terrain', pack_id='right', download_origin=product(1)['url'],
                     vertical_datum='  navd88 ', units='m')]
        result = download_terrain_batch(Store(rows), [product(1)], 'NAVD88', 'm', lambda: False,
                                        install=lambda *args: self.fail('matching pack should be reused'))
        self.assertEqual(result[0]['status'], 'skipped')


class TerrainBatchReviewTests(unittest.TestCase):
    def test_review_excludes_installed_and_requires_explicit_metadata(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        from veilbreaker.regional_packs_ui import TerrainBatchReview
        app = QApplication.instance() or QApplication([])
        dialog = TerrainBatchReview(None, [product(1), product(2)], {product(1)['url']})
        try:
            self.assertEqual([p['title'] for p in dialog.selected_products()], ['Tile 1', 'Tile 2'])
            self.assertIn('2 selected', dialog.summary.text())
            self.assertFalse(dialog.download_button.isEnabled())
            dialog.datum.setText('NAVD88')
            dialog.units.setCurrentIndex(1)
            self.assertTrue(dialog.download_button.isEnabled())
            dialog.items.item(1).setCheckState(__import__('PySide6.QtCore', fromlist=['Qt']).Qt.CheckState.Unchecked)
            dialog.items.item(0).setCheckState(__import__('PySide6.QtCore', fromlist=['Qt']).Qt.CheckState.Unchecked)
            self.assertFalse(dialog.download_button.isEnabled())
        finally:
            dialog.close()

    def test_batch_result_refreshes_installed_summary_and_failure_message(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from unittest.mock import patch
        from PySide6.QtWidgets import QApplication
        from veilbreaker.core import AppConfig
        from veilbreaker.regional_packs_ui import RegionalPacksDialog
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=folder))
            item = dict(product(1), reported_bounds_wgs84=[0, 0, 1, 1])
            catalog = {'products': [item], 'total': 1, 'plan': {'products': [item], 'bytes': 1000,
                        'gap_count': 0, 'duplicate_count': 0}}
            try:
                dialog.job_ready({'catalog': catalog})
                with patch.object(dialog.store, 'list_packs', return_value=[]):
                    dialog.job_ready({'batch': [dict(status='installed'), dict(status='failed', error='fixture error')]})
                self.assertIn('1 installed', dialog.status.text())
                self.assertIn('fixture error', dialog.status.text())
                self.assertIn('Completed tiles remain installed', dialog.status.text())
            finally:
                dialog.close()

