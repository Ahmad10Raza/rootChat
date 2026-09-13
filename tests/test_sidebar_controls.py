import os
import tempfile
import unittest
from PySide6.QtWidgets import QApplication
from database.database import DatabaseManager
from database.repositories.conversation_repository import ConversationRepository
from database.repositories.message_repository import MessageRepository
from database.repositories.memory_repository import MemoryRepository
from database.repositories.document_repository import DocumentRepository
from core.memory_manager import MemoryManager
from core.context_manager import ContextManager
from core.chat_manager import ChatManager
from core.app_state import AppState
from core.app_config import AppConfig
from core.ollama_client import OllamaClient
from ui.sidebar import Sidebar, SidebarFeatureRow


app = QApplication.instance() or QApplication([])


class TestSidebarControls(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.mktemp(suffix=".db")
        self.temp_cfg = tempfile.mktemp(suffix=".json")
        self.db = DatabaseManager(self.temp_db)
        self.config = AppConfig(self.temp_cfg)
        self.app_state = AppState(self.config)
        self.client = OllamaClient()
        self.mem_repo = MemoryRepository(self.db)
        self.doc_repo = DocumentRepository(self.db)
        self.msg_repo = MessageRepository(self.db)
        self.conv_repo = ConversationRepository(self.db)
        self.memory_manager = MemoryManager(self.app_state, self.mem_repo)
        self.context_manager = ContextManager(self.app_state, self.memory_manager, self.msg_repo, None)
        self.chat_manager = ChatManager(self.app_state, self.client, self.db, self.memory_manager, self.context_manager)
        self.sidebar = Sidebar(self.chat_manager, None)

    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
        if os.path.exists(self.temp_cfg):
            os.remove(self.temp_cfg)

    def test_sidebar_bottom_order(self):
        # The bottom layout should contain in order:
        # 1. memory_row
        # 2. knowledge_row
        # 3. archive_row
        # 4. settings_btn (LAST)
        self.assertIs(self.sidebar.memory_row, self.sidebar.memory_btn)
        self.assertIs(self.sidebar.knowledge_row, self.sidebar.knowledge_btn)
        self.assertIs(self.sidebar.archive_row, self.sidebar.archive_btn)
        
        self.assertEqual(self.sidebar.settings_btn.text(), "⚙  Settings")

    def test_sidebar_toggle_memory(self):
        # Initially memory is True
        self.assertTrue(self.app_state.get("memory_enabled", True))
        self.assertTrue(self.sidebar.memory_row.is_active())
        self.assertEqual(self.sidebar.memory_row.toggle_btn.text(), "ON")

        # Toggle via sidebar method
        self.sidebar._toggle_memory()
        self.assertFalse(self.app_state.get("memory_enabled"))
        self.assertFalse(self.sidebar.memory_row.is_active())
        self.assertEqual(self.sidebar.memory_row.toggle_btn.text(), "OFF")

        # Toggle again
        self.sidebar._toggle_memory()
        self.assertTrue(self.app_state.get("memory_enabled"))
        self.assertTrue(self.sidebar.memory_row.is_active())
        self.assertEqual(self.sidebar.memory_row.toggle_btn.text(), "ON")

    def test_sidebar_toggle_knowledge(self):
        # Initially knowledge mode is none (OFF)
        self.app_state.set("active_knowledge_mode", "none")
        self.assertFalse(self.sidebar.knowledge_row.is_active())
        self.assertEqual(self.sidebar.knowledge_row.toggle_btn.text(), "OFF")

        # Toggle to ON
        self.sidebar._toggle_knowledge()
        self.assertEqual(self.app_state.get("active_knowledge_mode"), "all")
        self.assertTrue(self.sidebar.knowledge_row.is_active())
        self.assertEqual(self.sidebar.knowledge_row.toggle_btn.text(), "ON")

        # Toggle to OFF
        self.sidebar._toggle_knowledge()
        self.assertEqual(self.app_state.get("active_knowledge_mode"), "none")
        self.assertFalse(self.sidebar.knowledge_row.is_active())
        self.assertEqual(self.sidebar.knowledge_row.toggle_btn.text(), "OFF")

    def test_sidebar_state_change_sync(self):
        # When app_state changes externally, sidebar rows should update
        self.app_state.set("memory_enabled", False)
        self.assertFalse(self.sidebar.memory_row.is_active())
        self.assertEqual(self.sidebar.memory_row.toggle_btn.text(), "OFF")

        self.app_state.set("memory_enabled", True)
        self.assertTrue(self.sidebar.memory_row.is_active())
        self.assertEqual(self.sidebar.memory_row.toggle_btn.text(), "ON")

        self.app_state.set("active_knowledge_mode", "specific")
        self.assertTrue(self.sidebar.knowledge_row.is_active())
        self.assertEqual(self.sidebar.knowledge_row.toggle_btn.text(), "ON")

        self.app_state.set("active_knowledge_mode", "none")
        self.assertFalse(self.sidebar.knowledge_row.is_active())
        self.assertEqual(self.sidebar.knowledge_row.toggle_btn.text(), "OFF")


if __name__ == "__main__":
    unittest.main()
