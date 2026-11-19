import os
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from veilbreaker.core import AppConfig
from veilbreaker.nearby_structures_ui import NearbyStructuresDialog
from veilbreaker.path_assessment_report import assessment_html
from tests.test_nearby_structures_ui import candidate, receiver
import tests.test_path_structure_report as report_fixtures


class StructureDuplicateDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_identical_records_are_disclosed_in_results_and_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            dialog = NearbyStructuresDialog(None, AppConfig(data_dir=tmp), receiver())
            try:
                selected = candidate()
                selected['alternate_packs'] = [dict(pack_id='b'*32, pack_name='Other pack',
                    sha256='d'*64, source='FCC', source_date='2026-10-25', license='Public')]
                dialog.job_ready({'kind': 'search', 'result': dict(candidates=[selected], total_matches=1,
                    duplicate_records=1, warnings=[], truncated=False)})
                self.assertIn('1 duplicate', dialog.status.text().lower())
                dialog.table.selectRow(0)
                self.assertIn('Other pack', dialog.details.text())
                self.assertIn('search time', dialog.details.text().lower())
            finally:
                dialog.close()

    def test_report_preserves_alternate_pack_provenance_and_escapes_html(self):
        selected = candidate()
        selected.update(selection_method='operator_selected', alternate_packs=[dict(pack_id='b'*32,
            pack_name='<other>', sha256='d'*64, source='FCC & registry', source_date='2026-10-25',
            license='Public')])
        report = assessment_html(report_fixtures.PhysicalStructureAssessmentTests().assessment(selected))
        self.assertIn('&lt;other&gt;', report)
        self.assertIn('FCC &amp; registry', report)
        self.assertIn('d'*64, report)
        self.assertIn('search time', report.lower())


if __name__ == '__main__':
    unittest.main()
