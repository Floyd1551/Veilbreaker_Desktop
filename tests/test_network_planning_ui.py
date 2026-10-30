import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest

from PySide6.QtWidgets import QApplication
from veilbreaker.rf_tools_ui import RFToolsDialog
from veilbreaker.toolbox_ui import ToolboxPage


class NetworkPlanningUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_tools_open_and_show_schematic_and_assumptions(self):
        dialog=RFToolsDialog()
        try:
            dialog.resize(760,650)
            for key in ('serialization_delay','tcp_window_rate','latency_budget','battery_runtime'):
                dialog.selector.setCurrentIndex(dialog.selector.findData(key))
                dialog.run_calculation()
                self.assertEqual(dialog.snapshot['tool_id'],key)
                self.assertEqual(dialog.flow_diagram.data['kind'],key)
                self.assertIn('not',dialog.snapshot['limitations'].lower())
                self.assertTrue(dialog.copy_button.isEnabled())
            dialog.show();self.app.processEvents()
            self.assertLessEqual(dialog.width(),760)
            self.assertLessEqual(dialog.height(),900)
        finally:dialog.close()

    def test_search_routes_new_tools_to_correct_categories(self):
        page=ToolboxPage()
        try:
            for query,key,category in [('serialization delay','serialization_delay','Networking'),
                                       ('battery runtime','battery_runtime','Fiber & Power')]:
                page.global_search.setText(query)
                found=[c.record for c in page.result_cards]
                self.assertTrue(any(r.target_id==key and r.category==category for r in found))
                page.open_record_tab('calculator:'+key)
                self.assertEqual(page.workspace_tabs.currentWidget().selector.currentData(),key)
        finally:page.close()


if __name__=='__main__':unittest.main()
