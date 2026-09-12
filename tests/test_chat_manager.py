import unittest
import tempfile
import os
from unittest.mock import MagicMock, patch
from core.chat_manager import ChatManager
from core.app_state import AppState
from database.database import DatabaseManager

from core.app_config import AppConfig
from core.memory_manager import MemoryManager
from core.context_manager import ContextManager
from database.repositories.memory_repository import MemoryRepository
from database.repositories.message_repository import MessageRepository

class TestChatManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = os.path.join(self.temp_dir.name, "config.json")
        self.patcher = patch("core.app_config.CONFIG_FILE", self.config_file)
        self.patcher.start()
        
        self.db_path = os.path.join(self.temp_dir.name, "test_rootChat.db")
        self.db_manager = DatabaseManager(db_path=self.db_path)
        self.config = AppConfig()
        self.app_state = AppState(config=self.config)
        self.client_mock = MagicMock()
        self.mem_repo = MemoryRepository(self.db_manager)
        self.msg_repo = MessageRepository(self.db_manager)
        self.memory_manager = MemoryManager(self.app_state, self.mem_repo)
        self.context_manager = ContextManager(self.app_state, self.memory_manager, self.msg_repo)
        self.chat_manager = ChatManager(
            self.app_state, self.client_mock, self.db_manager, self.memory_manager, self.context_manager
        )

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_start_new_conversation(self):
        self.chat_manager.start_new_conversation()
        self.assertIsNone(self.app_state.get("active_conversation_id"))
        self.assertEqual(self.app_state.get("current_messages"), [])

    @patch('core.chat_manager.StreamWorker')
    def test_send_message_creates_conversation(self, MockStreamWorker):
        self.chat_manager.start_new_conversation()
        self.app_state.set("selected_model", "test_model:latest")
        
        # Track signal
        conv_id_received = None
        def on_conv_created(conv_id):
            nonlocal conv_id_received
            conv_id_received = conv_id
        self.chat_manager.conversation_created.connect(on_conv_created)
        
        self.chat_manager.send_message("Hello, how are you today?")
        
        self.assertIsNotNone(conv_id_received)
        self.assertEqual(self.app_state.get("active_conversation_id"), conv_id_received)
        
        conv = self.chat_manager.conv_repo.get_conversation(conv_id_received)
        self.assertEqual(conv["title"], f"Chat #{conv_id_received}: Hello, how...")
        self.assertEqual(conv["model"], "test_model:latest")
        
    @patch('core.chat_manager.StreamWorker')
    def test_load_conversation(self, MockStreamWorker):
        conv_id = self.chat_manager.conv_repo.create_conversation("Test", "modelX")
        self.chat_manager.msg_repo.create_message(conv_id, "user", "test")
        
        messages = self.chat_manager.load_conversation(conv_id)
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(self.app_state.get("active_conversation_id"), conv_id)
        self.assertEqual(self.app_state.get("selected_model"), "modelX")
