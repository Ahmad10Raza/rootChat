import unittest
import os
import tempfile
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from database.database import DatabaseManager
from database.repositories.message_repository import MessageRepository
from database.repositories.conversation_repository import ConversationRepository
from core.chat_manager import ChatManager
from core.app_state import AppState
from core.app_config import AppConfig
from ui.message_widget import MessageWidget
from ui.sidebar import Sidebar

app = QApplication.instance()
if not app:
    app = QApplication([])

class TestMessageActionsAndRepository(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_file.close()
        self.db = DatabaseManager(self.temp_file.name)
        self.msg_repo = MessageRepository(self.db)
        self.conv_repo = ConversationRepository(self.db)
        self.conv_id = self.conv_repo.create_conversation("Test Conv", "test-model")

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_delete_message_repository(self):
        m1 = self.msg_repo.create_message(self.conv_id, "user", "Hello")
        m2 = self.msg_repo.create_message(self.conv_id, "assistant", "World")
        m3 = self.msg_repo.create_message(self.conv_id, "user", "Third")

        self.assertEqual(len(self.msg_repo.get_messages(self.conv_id)), 3)

        # Delete m2
        self.msg_repo.delete_message(m2)
        remaining = self.msg_repo.get_messages(self.conv_id)
        self.assertEqual(len(remaining), 2)
        self.assertEqual([m["id"] for m in remaining], [m1, m3])

    def test_chat_manager_delete_message(self):
        config = AppConfig()
        state = AppState(config)
        client = MagicMock()
        mem_mgr = MagicMock()
        ctx_mgr = MagicMock()
        manager = ChatManager(state, client, self.db, mem_mgr, ctx_mgr)

        m1 = self.msg_repo.create_message(self.conv_id, "user", "Msg 1")
        removed_ids = []
        manager.message_removed.connect(lambda mid: removed_ids.append(mid))

        manager.delete_message(m1)
        self.assertEqual(removed_ids, [m1])
        self.assertEqual(len(self.msg_repo.get_messages(self.conv_id)), 0)


class TestMessageWidgetContextMenu(unittest.TestCase):
    def test_message_widget_signals_and_attributes(self):
        w = MessageWidget("assistant", "Hello world", msg_id=42)
        self.assertEqual(w.msg_id, 42)
        self.assertEqual(w.role, "assistant")
        self.assertEqual(w.content, "Hello world")

        delete_ids = []
        w.delete_requested.connect(lambda mid: delete_ids.append(mid))
        w.delete_requested.emit(42)
        self.assertEqual(delete_ids, [42])

        regen_fired = []
        w.regenerate_requested.connect(lambda: regen_fired.append(True))
        w.regenerate_requested.emit()
        self.assertEqual(regen_fired, [True])

    def test_copy_content_to_clipboard(self):
        w = MessageWidget("user", "Testing clipboard copy", msg_id=10)
        w._copy_content()
        self.assertEqual(QApplication.clipboard().text(), "Testing clipboard copy")


class TestSidebarContextMenuAndGrouping(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_file.close()
        self.db = DatabaseManager(self.temp_file.name)
        self.conv_repo = ConversationRepository(self.db)
        self.config = AppConfig()
        self.state = AppState(self.config)
        self.client = MagicMock()
        self.mem_mgr = MagicMock()
        self.ctx_mgr = MagicMock()
        self.chat_mgr = ChatManager(self.state, self.client, self.db, self.mem_mgr, self.ctx_mgr)
        self.sidebar = Sidebar(self.chat_mgr)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_grouping_pinned_and_archived(self):
        convs = [
            {"id": 1, "title": "Normal Chat", "is_pinned": 0, "is_archived": 0, "updated_at": "2026-09-12T10:00:00"},
            {"id": 2, "title": "Pinned Chat", "is_pinned": 1, "is_archived": 0, "updated_at": "2026-09-12T10:00:00"},
            {"id": 3, "title": "Archived Chat", "is_pinned": 0, "is_archived": 1, "updated_at": "2026-09-12T10:00:00"},
        ]
        groups = self.sidebar._group_by_date(convs)
        group_names = [name for name, items in groups]
        self.assertIn("PINNED", group_names)
        self.assertIn("ARCHIVED", group_names)

        pinned_group = next(items for name, items in groups if name == "PINNED")
        self.assertEqual(len(pinned_group), 1)
        self.assertEqual(pinned_group[0]["id"], 2)

        archived_group = next(items for name, items in groups if name == "ARCHIVED")
        self.assertEqual(len(archived_group), 1)
        self.assertEqual(archived_group[0]["id"], 3)

    def test_select_conversation_and_persistence(self):
        c1 = self.conv_repo.create_conversation("Chat 1", "model1")
        c2 = self.conv_repo.create_conversation("Chat 2", "model2")

        self.state.set("active_conversation_id", c2)
        self.sidebar.load_conversations()

        # Check that c2 is selected
        selected_item = self.sidebar.chat_list.currentItem()
        self.assertIsNotNone(selected_item)
        conv = selected_item.data(Qt.ItemDataRole.UserRole)
        self.assertEqual(conv["id"], c2)

        # Select c1 via helper
        self.sidebar.select_conversation(c1)
        self.assertEqual(self.sidebar.chat_list.currentItem().data(Qt.ItemDataRole.UserRole)["id"], c1)

        # Deselect via None
        self.sidebar.select_conversation(None)
        self.assertIsNone(self.sidebar.chat_list.currentItem())

    def test_pin_and_archive_toggle_updates(self):
        c1 = self.conv_repo.create_conversation("To Pin", "model1")
        self.conv_repo.update_conversation(c1, is_pinned=True)
        updated = self.conv_repo.get_conversation(c1)
        self.assertEqual(updated["is_pinned"], 1)

        self.conv_repo.update_conversation(c1, is_pinned=False, is_archived=True)
        updated = self.conv_repo.get_conversation(c1)
        self.assertEqual(updated["is_pinned"], 0)
        self.assertEqual(updated["is_archived"], 1)

if __name__ == "__main__":
    unittest.main()
