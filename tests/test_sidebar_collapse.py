import os
import unittest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication

from core.chat_manager import ChatManager
from ui.sidebar import Sidebar

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication([])


class TestSidebarCollapse(unittest.TestCase):

    def setUp(self):
        self.chat_mgr = MagicMock()
        self.chat_mgr.conv_repo.list_conversations.return_value = []
        self.sidebar = Sidebar(self.chat_mgr)

    def test_initial_expanded_state(self):
        self.assertFalse(self.sidebar.is_collapsed)
        self.assertEqual(self.sidebar.maximumWidth(), 260)
        self.assertEqual(self.sidebar.minimumWidth(), 260)
        self.assertFalse(self.sidebar.title_label.isHidden())
        self.assertFalse(self.sidebar.search_bar.isHidden())
        self.assertFalse(self.sidebar.chat_list.isHidden())
        self.assertIn("New Chat", self.sidebar.new_chat_btn.text())

    def test_collapse_and_expand_cycle(self):
        toggled_events = []
        self.sidebar.sidebar_toggled.connect(lambda c: toggled_events.append(c))

        # 1. Collapse
        self.sidebar.toggle_collapse()
        self.assertTrue(self.sidebar.is_collapsed)
        self.assertEqual(self.sidebar.maximumWidth(), 56)
        self.assertEqual(self.sidebar.minimumWidth(), 56)
        self.assertTrue(self.sidebar.title_label.isHidden())
        self.assertTrue(self.sidebar.search_bar.isHidden())
        self.assertTrue(self.sidebar.chat_list.isHidden())
        self.assertTrue(self.sidebar.archive_btn.isHidden())

        # Check compact icon buttons
        self.assertEqual(self.sidebar.new_chat_btn.text(), "＋")
        self.assertEqual(self.sidebar.memory_btn.text(), "🧠")
        self.assertEqual(self.sidebar.knowledge_btn.text(), "📚")
        self.assertEqual(self.sidebar.settings_btn.text(), "⚙")
        self.assertEqual(toggled_events, [True])

        # 2. Expand
        self.sidebar.toggle_collapse()
        self.assertFalse(self.sidebar.is_collapsed)
        self.assertEqual(self.sidebar.maximumWidth(), 260)
        self.assertEqual(self.sidebar.minimumWidth(), 260)
        self.assertFalse(self.sidebar.title_label.isHidden())
        self.assertFalse(self.sidebar.search_bar.isHidden())
        self.assertFalse(self.sidebar.chat_list.isHidden())
        self.assertFalse(self.sidebar.archive_btn.isHidden())

        # Check full text buttons restored
        self.assertIn("New Chat", self.sidebar.new_chat_btn.text())
        self.assertIn("Memory", self.sidebar.memory_btn.text())
        self.assertIn("Knowledge Base", self.sidebar.knowledge_btn.text())
        self.assertIn("Settings", self.sidebar.settings_btn.text())
        self.assertEqual(toggled_events, [True, False])


if __name__ == "__main__":
    unittest.main()
