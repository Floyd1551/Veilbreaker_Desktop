import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from veilbreaker.area_coverage_report import report_html
from veilbreaker.core import AppConfig
from veilbreaker.regional_packs_ui import RegionalPacksDialog, _coverage_job


class MapIntegrityPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_unchecked_map_still_gets_header_check_and_report_limitations(self):
        from test_map_pack import pack_bytes
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / 'map.pmtiles'; path.write_bytes(pack_bytes())
            from veilbreaker.map_catalog import PackCatalog
            catalog = root / 'catalog.json'; PackCatalog(catalog).register(path)
            with patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                model = _coverage_job(root, catalog, [-97,32,-96,34], None, lambda:False, lambda _:None)['coverage']
            self.assertEqual(model['map_inspection']['entries'][0]['checksum_status'], 'not_checked')
            self.assertEqual(model['map']['status'], 'bounds contain area')
            self.assertIn('not checked', report_html(model).lower())
            self.assertIn('not coverage', report_html(model).lower())
            self.assertIn('mapped network drive', report_html(model).lower())

    def test_broken_catalog_and_included_map_do_not_block_other_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); catalog = root / 'catalog.json'; catalog.write_text('{invalid', encoding='utf-8')
            broken = root / 'broken.pmtiles'; broken.write_bytes(b'invalid')
            with patch('veilbreaker.deployment_data.bundled_map', return_value=broken):
                model = _coverage_job(root, catalog, [-97,32,-96,34], None, lambda:False, lambda _:None,
                                      verify_integrity=True)['coverage']
            self.assertEqual(model['map']['status'], 'no available map bounds')
            self.assertTrue(model['map_inspection']['warnings'])
            self.assertFalse(model['map_inspection']['complete'])
            self.assertIn('integrity', model)
            self.assertIn('terrain', model)
            self.assertIn('map', report_html(model).lower())
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=tmp))
            try:
                dialog.job_ready({'coverage':model})
                self.assertIn('inspection incomplete',dialog.coverage_table.item(0,1).text().lower())
            finally:
                dialog.close()

    def test_checkbox_invalidates_old_results_and_exposes_map_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            dialog = RegionalPacksDialog(None, AppConfig(data_dir=tmp))
            try:
                self.assertFalse(dialog.coverage_verify_map.isChecked())
                with patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                    model = _coverage_job(Path(tmp), Path(tmp)/'catalog.json', [-97,32,-96,34], None,
                                          lambda:False, lambda _:None)['coverage']
                dialog.job_ready({'coverage':model})
                dialog.coverage_table.selectRow(0)
                self.assertIn('header', dialog.coverage_details.toPlainText().lower())
                dialog.coverage_verify_map.setChecked(True)
                self.assertIsNone(dialog.coverage_result)
                self.assertFalse(dialog.coverage_save.isEnabled())
                dialog.resize(760,650);dialog.workspace_tabs.setCurrentIndex(2);dialog.show();self.app.processEvents()
                self.assertLessEqual(dialog.width(),760)
                bottom=dialog.coverage_verify_map.mapTo(dialog,dialog.coverage_verify_map.rect().bottomRight())
                self.assertLessEqual(bottom.x(),dialog.width());self.assertLessEqual(bottom.y(),dialog.height())
            finally:
                dialog.close()

    def test_optional_checksum_flag_is_dispatched_and_rejections_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=dict(entries=[],rejected=[dict(name='<broken>',path='x',status='checksum_mismatch',detail='bad & changed')],
                        warnings=[],complete=True,checked_utc='2026-11-20T00:00:00Z')
            with patch('veilbreaker.area_map_readiness.check_catalog_maps', return_value=result) as verify, \
                 patch('veilbreaker.deployment_data.bundled_map', return_value=None):
                model = _coverage_job(Path(tmp),Path(tmp)/'catalog.json',[-97,32,-96,34],None,
                                      lambda:False,lambda _:None,verify_map=True)['coverage']
            self.assertTrue(verify.call_args.kwargs['verify_checksum'])
            self.assertEqual(model['map']['status'],'no available map bounds')
            html=report_html(model)
            self.assertIn('&lt;broken&gt;',html);self.assertIn('bad &amp; changed',html)
            self.assertIn('checksum_mismatch',html)


if __name__ == '__main__':unittest.main()
