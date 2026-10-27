import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from veilbreaker.core import AppConfig
from veilbreaker.regional_packs import RegionalPackStore
from veilbreaker.regional_packs_ui import RegionalPacksDialog
from tests.test_regional_packs import structures


class RegionalPacksUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_manager_shows_coverage_provenance_and_structure_separation(self):
        with tempfile.TemporaryDirectory() as folder:
            config = AppConfig(data_dir=folder)
            source = Path(folder) / 'source.geojson'
            structures(source)
            store = RegionalPackStore(config.root / 'regional-packs')
            store.install_local('structures', source,
                                dict(name='Dallas structures', source='Operator fixture', license='Test only',
                                     source_date='2026-10-27', bounds_wgs84=[-97.1, 32.8, -96.8, 33.1]), lambda: False)
            dialog = RegionalPacksDialog(None, config)
            self.assertEqual(dialog.table.rowCount(), 1)
            dialog.table.selectRow(0)
            self.assertIn('Operator fixture', dialog.details.text())
            self.assertIn('not completeness', dialog.details.text())
            self.assertIn('No serving-cell', dialog.details.text())
            dialog.show_structure_records()
            self.assertEqual(dialog.structures_table.rowCount(), 1)
            self.assertEqual(dialog.structures_table.item(0, 0).text(), 'ASR-100')
            dialog.close()

    def test_usgs_product_selection_fills_source_but_requires_datum_and_units(self):
        with tempfile.TemporaryDirectory() as folder:
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=folder))
            product = dict(title='USGS 1/3 Arc Second n33w097 20260406', source='USGS The National Map · 3DEP',
                           license='USGS public domain', source_date='2026-04-06', bytes=400000000,
                           url='https://prd-tnm.s3.amazonaws.com/example.tif', reported_bounds_wgs84=[-97, 32, -96, 33])
            dialog.job_ready({'catalog': dict(products=[product], total=1)})
            dialog.use_product()
            self.assertEqual(dialog.url.text(), product['url'])
            self.assertEqual(dialog.date.text(), '2026-04-06')
            self.assertEqual(dialog.datum.text(), '')
            self.assertEqual(dialog.units.currentIndex(), 0)
            dialog.close()

    def test_manager_tabs_fit_field_window(self):
        with tempfile.TemporaryDirectory() as folder:
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=folder))
            dialog.resize(900, 650)
            dialog.show()
            self.app.processEvents()
            self.assertLessEqual(dialog.width(), 900)
            self.assertLessEqual(dialog.height(), 700)
            self.assertEqual(dialog.workspace_tabs.count(), 2)
            dialog.close()

    def test_huntsville_preset_sets_search_area_without_claiming_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=folder))
            dialog.use_huntsville_area()
            self.assertEqual(dialog._entered_bounds(), [-87.2, 34.3, -86.2, 35.2])
            self.assertIn('search area', dialog.status.text().lower())
            self.assertEqual(dialog.store.list_packs(), [])
            dialog.close()


if __name__ == '__main__':
    unittest.main()
