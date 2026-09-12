import os
import unittest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication

from core.presets import PROMPT_PRESETS, get_preset, list_presets
from core.app_config import AppConfig
from core.app_state import AppState
from core.context_manager import ContextManager
from core.chat_manager import ChatManager
from database.database import DatabaseManager
from database.repositories.conversation_repository import ConversationRepository
from database.repositories.message_repository import MessageRepository
from ui.preset_selector import PresetSelector

# Ensure offscreen Qt application exists for widget tests
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication([])

class TestPromptPresets(unittest.TestCase):
    
    def test_presets_definitions(self):
        expected_ids = {"general", "coding", "sql", "linux", "rpa", "datascience"}
        presets = list_presets()
        self.assertEqual(len(presets), 6)
        
        found_ids = {p["id"] for p in presets}
        self.assertEqual(found_ids, expected_ids)
        
        for p in presets:
            self.assertIn("name", p)
            self.assertIn("icon", p)
            self.assertIn("description", p)
            self.assertIn("system_prompt", p)
            self.assertGreater(len(p["system_prompt"]), 20)

    def test_get_preset(self):
        coding = get_preset("coding")
        self.assertEqual(coding["id"], "coding")
        self.assertIn("software engineer", coding["system_prompt"].lower())
        
        # Fallback to general for unknown or None
        fallback = get_preset("non_existent_preset")
        self.assertEqual(fallback["id"], "general")
        
        fallback_none = get_preset(None)
        self.assertEqual(fallback_none["id"], "general")

    def test_context_manager_uses_preset(self):
        config = AppConfig()
        app_state = AppState(config)
        memory_manager = MagicMock()
        memory_manager.get_relevant_memories.return_value = []
        msg_repo = MagicMock()
        msg_repo.get_messages.return_value = []
        
        cm = ContextManager(app_state, memory_manager, msg_repo, retriever=None)
        
        # Test general preset
        app_state.set("active_preset", "general")
        context = cm.build_context(1, "Hello")
        self.assertTrue(any("rootChat" in msg["content"] for msg in context if msg["role"] == "system"))
        
        # Test coding preset
        app_state.set("active_preset", "coding")
        context = cm.build_context(1, "How do I write a binary search?")
        self.assertTrue(any("senior software engineer" in msg["content"].lower() for msg in context if msg["role"] == "system"))
        
        # Test linux preset
        app_state.set("active_preset", "linux")
        context = cm.build_context(1, "List files")
        self.assertTrue(any("linux system administrator" in msg["content"].lower() for msg in context if msg["role"] == "system"))

    def test_database_persistence(self):
        test_db = "/tmp/test_presets_db.sqlite"
        if os.path.exists(test_db):
            os.remove(test_db)
            
        db_mgr = DatabaseManager(test_db)
        repo = ConversationRepository(db_mgr)
        
        # Default preset is 'general'
        cid1 = repo.create_conversation("Default Chat", "llama3.2")
        conv1 = repo.get_conversation(cid1)
        self.assertEqual(conv1["preset"], "general")
        
        # Explicit preset
        cid2 = repo.create_conversation("Coding Chat", "llama3.2", preset="coding")
        conv2 = repo.get_conversation(cid2)
        self.assertEqual(conv2["preset"], "coding")
        
        # Update preset
        repo.update_conversation(cid1, preset="sql")
        conv1_updated = repo.get_conversation(cid1)
        self.assertEqual(conv1_updated["preset"], "sql")
        
        if os.path.exists(test_db):
            os.remove(test_db)

    def test_chat_manager_preset_integration(self):
        test_db = "/tmp/test_chat_manager_presets.sqlite"
        if os.path.exists(test_db):
            os.remove(test_db)
            
        db_mgr = DatabaseManager(test_db)
        config = AppConfig()
        app_state = AppState(config)
        app_state.set("selected_model", "test-model")
        client = MagicMock()
        memory_manager = MagicMock()
        memory_manager.detect_and_save_explicit_memory.return_value = False
        context_manager = MagicMock()
        context_manager.build_context.return_value = []
        
        chat_mgr = ChatManager(app_state, client, db_mgr, memory_manager, context_manager)
        
        # Set active preset to sql
        app_state.set("active_preset", "sql")
        cid = chat_mgr._ensure_conversation_exists("SELECT * FROM users")
        
        conv = chat_mgr.conv_repo.get_conversation(cid)
        self.assertEqual(conv["preset"], "sql")
        
        # Start new conversation and switch preset to linux
        chat_mgr.start_new_conversation()
        app_state.set("active_preset", "linux")
        cid2 = chat_mgr._ensure_conversation_exists("uname -a")
        conv2 = chat_mgr.conv_repo.get_conversation(cid2)
        self.assertEqual(conv2["preset"], "linux")
        
        # Load conversation 1 -> app_state should switch back to 'sql'
        chat_mgr.load_conversation(cid)
        self.assertEqual(app_state.get("active_preset"), "sql")
        
        if os.path.exists(test_db):
            os.remove(test_db)

    def test_preset_selector_ui(self):
        selector = PresetSelector()
        self.assertEqual(selector.get_current_preset(), "general")
        
        selector.set_preset("datascience")
        self.assertEqual(selector.get_current_preset(), "datascience")
        
        emitted = []
        selector.preset_changed.connect(lambda p: emitted.append(p))
        
        # Trigger index change to 'rpa'
        for i in range(selector.combo_box.count()):
            if selector.combo_box.itemData(i) == "rpa":
                selector.combo_box.setCurrentIndex(i)
                break
                
        self.assertIn("rpa", emitted)


if __name__ == "__main__":
    unittest.main()
