import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import time
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

    def test_usgs_catalog_suggests_adjacent_tiles_with_historical_access(self):
        from veilbreaker.usgs_terrain_catalog import plan_terrain_products
        def tile(title, date, bounds):
            return dict(title=title,source_date=date,reported_bounds_wgs84=bounds,bytes=1000000,
                        url='https://example.com/'+title+'.tif',source='USGS',license='Public domain')
        products=[tile('west old','2020-01-01',[0,0,1,1]),tile('west new','2026-01-01',[0,0,1,1]),tile('east','2026-01-01',[1,0,2,1])]
        with tempfile.TemporaryDirectory() as folder:
            dialog=RegionalPacksDialog(None,AppConfig(data_dir=folder))
            try:
                plan=plan_terrain_products([0,0,2,1],products)
                dialog.job_ready({'catalog':dict(products=products,total=3,truncated=False,plan=plan)})
                self.assertEqual(dialog.products.count(),2)
                self.assertIn('2 suggested',dialog.catalog_summary.text())
                self.assertIn('no-data',dialog.catalog_summary.text())
                dialog.catalog_view.setCurrentIndex(1)
                self.assertEqual(dialog.products.count(),3)
            finally: dialog.close()

    def test_catalog_marks_installed_downloads(self):
        from unittest.mock import patch
        item=dict(title='USGS tile',source_date='2026-01-01',reported_bounds_wgs84=[0,0,1,1],
                  bytes=1000000,url='https://example.com/tile.tif',source='USGS',license='Public domain')
        with tempfile.TemporaryDirectory() as folder:
            dialog=RegionalPacksDialog(None,AppConfig(data_dir=folder))
            try:
                with patch.object(dialog.store,'list_packs',return_value=[{'kind':'terrain','download_origin':item['url'],'status':'available'}]):
                    from veilbreaker.usgs_terrain_catalog import plan_terrain_products
                    plan=plan_terrain_products([0,0,1,1],[item])
                    dialog.job_ready({'catalog':dict(products=[item],total=1,plan=plan)})
                    self.assertIn('Installed',dialog.products.itemText(0))
                    self.assertIn('1 installed',dialog.catalog_summary.text())
                    dialog.use_product()
                    self.assertIn('verify its checksum',dialog.status.text())
            finally: dialog.close()

    def test_manager_tabs_fit_field_window(self):
        with tempfile.TemporaryDirectory() as folder:
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=folder))
            dialog.resize(900, 650)
            dialog.show()
            self.app.processEvents()
            self.assertLessEqual(dialog.width(), 900)
            self.assertLessEqual(dialog.height(), 700)
            self.assertEqual(dialog.workspace_tabs.count(), 3)
            dialog.workspace_tabs.setCurrentIndex(1)
            self.app.processEvents()
            self.assertEqual(dialog.workspace_tabs.widget(1).horizontalScrollBar().maximum(),0)
            dialog.workspace_tabs.setCurrentIndex(2)
            self.app.processEvents()
            for widget in (dialog.coverage_bounds,dialog.coverage_check,dialog.coverage_save,dialog.coverage_sample,dialog.coverage_grid,dialog.coverage_table,dialog.coverage_details):
                self.assertLessEqual(widget.mapTo(dialog,widget.rect().bottomRight()).x(),dialog.width())
                self.assertLessEqual(widget.mapTo(dialog,widget.rect().bottomRight()).y(),dialog.height())
            dialog.close()

    def test_area_preview_reports_bounds_and_cell_counts_without_coverage_claims(self):
        from veilbreaker.area_coverage import area_preview
        with tempfile.TemporaryDirectory() as folder:
            dialog=RegionalPacksDialog(None, AppConfig(data_dir=folder))
            try:
                dialog.coverage_huntsville()
                self.assertEqual(dialog.coverage_bounds.text(), '-87.2, 34.3, -86.2, 35.2')
                preview=area_preview([-87.2,34.3,-86.2,35.2],[],[],Path(folder)/'refs')
                dialog.job_ready({'coverage':preview})
                self.assertEqual(dialog.coverage_table.rowCount(),4)
                self.assertIn('no available terrain', dialog.coverage_table.item(1,1).text())
                dialog.coverage_table.selectRow(2)
                self.assertIn('not verified towers', dialog.coverage_details.toPlainText())
            finally:
                dialog.close()

    def test_area_preview_saves_readable_offline_report(self):
        from unittest.mock import patch
        from veilbreaker.area_coverage import area_preview
        with tempfile.TemporaryDirectory() as folder:
            dialog=RegionalPacksDialog(None,AppConfig(data_dir=folder)); target=Path(folder)/'preview.html'
            try:
                self.assertFalse(dialog.coverage_save.isEnabled())
                preview=area_preview([0,0,1,1],[],[],Path(folder)/'refs')
                dialog.job_ready({'coverage':preview})
                self.assertTrue(dialog.coverage_save.isEnabled())
                with patch('veilbreaker.regional_packs_ui.QFileDialog.getSaveFileName',return_value=(str(target),'HTML')):
                    dialog.save_coverage_report()
                html=target.read_text(encoding='utf-8')
                self.assertIn('Area readiness preview',html)
                self.assertIn('no active cell reference',html)
                dialog.coverage_bounds.setText('1, 1, 2, 2')
                self.assertFalse(dialog.coverage_save.isEnabled())
                self.assertIsNone(dialog.coverage_result)
            finally:dialog.close()

    def test_installing_pack_invalidates_previous_preview(self):
        from veilbreaker.area_coverage import area_preview
        with tempfile.TemporaryDirectory() as folder:
            cfg=AppConfig(data_dir=folder);dialog=RegionalPacksDialog(None,cfg)
            source=Path(folder)/'source.geojson';structures(source)
            try:
                dialog.job_ready({'coverage':area_preview([-97,32,-96,34],[],[],Path(folder)/'refs')})
                self.assertTrue(dialog.coverage_save.isEnabled())
                row=dialog.store.install_local('structures',source,dict(name='Test',source='Fixture',license='Test',
                    source_date='2026-10-30',bounds_wgs84=[-97.1,32.8,-96.8,33.1]),lambda:False)
                dialog.job_ready({'installed':row})
                self.assertIsNone(dialog.coverage_result)
                self.assertFalse(dialog.coverage_save.isEnabled())
            finally:dialog.close()

    def test_area_preview_worker_counts_local_reference_records(self):
        from veilbreaker.cell_reference import import_reference, activate_reference
        from test_cell_reference import HEADER, ROW, META
        with tempfile.TemporaryDirectory() as folder:
            config=AppConfig(data_dir=folder)
            source=Path(folder)/'cells.csv';source.write_text(HEADER+ROW,encoding='utf-8')
            root=config.root/'cell-references'
            imported=import_reference(root,source,META,lambda:False,lambda _:None)
            activate_reference(root,imported['dataset_id'])
            dialog=RegionalPacksDialog(None,config)
            try:
                dialog.coverage_bounds.setText('-97, 32, -96, 34')
                dialog.check_coverage()
                deadline=time.monotonic()+5
                while dialog.worker is not None and time.monotonic()<deadline:
                    self.app.processEvents();time.sleep(.01)
                self.assertIsNone(dialog.worker)
                self.assertIn('1 records',dialog.coverage_table.item(2,1).text())
                dialog.coverage_table.selectRow(2)
                self.assertIn('LTE 311/480: 1',dialog.coverage_details.toPlainText())
            finally:
                dialog.close()

    def test_area_preview_optional_terrain_sampling_reports_nodata(self):
        from tests.test_terrain_raster import make_dem, rasterio
        if rasterio is None:
            self.skipTest('terrain dependencies unavailable')
        with tempfile.TemporaryDirectory() as folder:
            config=AppConfig(data_dir=folder);source=Path(folder)/'dem.tif';make_dem(source,True)
            RegionalPackStore(config.root/'regional-packs').install_local('terrain',source,
                dict(name='Test',source='Fixture',license='Test',source_date='2026-10-29',vertical_datum='NAVD88',units='m'),lambda:False)
            dialog=RegionalPacksDialog(None,config)
            try:
                dialog.coverage_bounds.setText('-97, 32.99, -96.99, 33')
                self.assertFalse(dialog.coverage_grid.isEnabled())
                dialog.coverage_sample.setChecked(True)
                self.assertTrue(dialog.coverage_grid.isEnabled())
                dialog.coverage_grid.setCurrentIndex(dialog.coverage_grid.findData(41))
                dialog.check_coverage()
                deadline=time.monotonic()+10
                while dialog.worker is not None and time.monotonic()<deadline:
                    self.app.processEvents();time.sleep(.01)
                self.assertIsNone(dialog.worker)
                self.assertIn('sampled missing',dialog.coverage_table.item(1,1).text())
                self.assertEqual(dialog.coverage_result['terrain']['sample']['total'],1681)
                dialog.coverage_table.selectRow(1)
                self.assertIn('Sparse grid',dialog.coverage_details.toPlainText())
            finally:
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
