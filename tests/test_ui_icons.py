import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest

from PySide6.QtWidgets import QApplication
from veilbreaker.tool_cards import ToolCard
from veilbreaker.tool_registry import ToolRecord


class IconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_tool_card_category_icon_renders(self):
        record = ToolRecord('calculator:fspl', 'FSPL', 'RF', 'calculator',
                            'Calculate free-space loss.', (), 'fspl')
        card = ToolCard(record)
        self.assertFalse(card.category_icon.pixmap().isNull())
        self.assertFalse(card.open_button.icon().isNull())
        card.close()


if __name__ == '__main__':
    unittest.main()
