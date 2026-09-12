import os
import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from core.app_config import AppConfig
from core.app_state import AppState
from core.ollama_client import OllamaClient
from core.chat_manager import ChatManager
from database.database import DatabaseManager
from ui.mini_chat_dialog import MiniChatDialog

import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication([])


class TestMiniChatDialog(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.config = AppConfig(os.path.join(self.tmp_dir.name, "config.json"))
        self.app_state = AppState(self.config)
        self.app_state.set("selected_model", "test-llama:latest")
        self.app_state.set("active_preset", "coding")
        self.client = OllamaClient("http://localhost:11434")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_init_dialog(self):
        dialog = MiniChatDialog(self.client, self.app_state)
        self.assertIsNotNone(dialog.input_field)
        self.assertIsNotNone(dialog.response_browser)
        self.assertFalse(dialog.response_browser.isVisible())
        self.assertIn("test-llama:latest", dialog.badge_lbl.text())

    @patch("core.stream_worker.StreamWorker.start")
    def test_submit_query(self, mock_start):
        dialog = MiniChatDialog(self.client, self.app_state)
        dialog.show()
        dialog.input_field.setText("What is a quicksort algorithm?")
        dialog._on_submit()

        self.assertFalse(dialog.response_browser.isHidden())
        self.assertFalse(dialog.footer_widget.isHidden())
        self.assertFalse(dialog.stop_btn.isHidden())
        self.assertEqual(dialog.last_query, "What is a quicksort algorithm?")
        mock_start.assert_called_once()
        dialog.close()

    def test_chunk_and_finished(self):
        dialog = MiniChatDialog(self.client, self.app_state)
        dialog.input_field.setText("Test prompt")
        dialog.response_browser.setVisible(True)

        dialog._on_chunk("Hello ")
        dialog._on_chunk("world!")
        self.assertEqual(dialog.full_response, "Hello world!")

        dialog._on_finished("Hello world!")
        self.assertFalse(dialog.stop_btn.isVisible())
        self.assertEqual(dialog.status_lbl.text(), "✓ Finished")

    def test_copy_response(self):
        dialog = MiniChatDialog(self.client, self.app_state)
        dialog.full_response = "Copied text content"
        dialog._on_copy()

        clipboard = QApplication.clipboard()
        self.assertEqual(clipboard.text(), "Copied text content")
        self.assertEqual(dialog.copy_btn.text(), "✓ Copied!")

    def test_promote_to_full_chat(self):
        test_db = "/tmp/test_mini_chat_db.sqlite"
        if os.path.exists(test_db):
            os.remove(test_db)

        db_mgr = DatabaseManager(test_db)
        memory_mgr = MagicMock()
        context_mgr = MagicMock()
        chat_mgr = ChatManager(self.app_state, self.client, db_mgr, memory_mgr, context_mgr)

        dialog = MiniChatDialog(self.client, self.app_state, chat_manager=chat_mgr)
        dialog.last_query = "Quick question about Python"
        dialog.full_response = "Python is a high-level programming language."

        promoted_ids = []
        dialog.chat_promoted.connect(lambda cid: promoted_ids.append(cid))

        dialog._on_promote_to_full_chat()

        self.assertEqual(len(promoted_ids), 1)
        cid = promoted_ids[0]

        # Verify conversation in database
        conv = chat_mgr.conv_repo.get_conversation(cid)
        self.assertIsNotNone(conv)
        self.assertIn("Quick: Quick question about", conv["title"])
        self.assertEqual(conv["preset"], "coding")

        messages = chat_mgr.msg_repo.get_messages(cid)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["content"], "Quick question about Python")
        self.assertEqual(messages[1]["content"], "Python is a high-level programming language.")

        if os.path.exists(test_db):
            os.remove(test_db)

    @patch("core.stream_worker.StreamWorker.start")
    def test_enter_key_submission(self, mock_start):
        dialog = MiniChatDialog(self.client, self.app_state)
        dialog.show()
        dialog.input_field.setText("What is local AI?")
        
        # Simulate pressing Enter in input_field
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        app.sendEvent(dialog.input_field, event)

        self.assertTrue(dialog.input_field.isReadOnly())
        self.assertTrue(dialog.stop_btn.isVisible())
        self.assertFalse(dialog.stop_btn.isDefault())
        self.assertFalse(dialog.stop_btn.autoDefault())
        self.assertEqual(dialog.last_query, "What is local AI?")
        mock_start.assert_called_once()
        dialog.close()

    def test_stop_behavior(self):
        dialog = MiniChatDialog(self.client, self.app_state)
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = True
        dialog.worker = mock_worker
        dialog.stop_btn.setVisible(True)
        dialog.input_field.setReadOnly(True)

        dialog._on_stop()

        mock_worker.stop.assert_called_once()
        self.assertTrue(dialog._was_stopped)
        self.assertEqual(dialog.status_lbl.text(), "■ Stopped")
        self.assertFalse(dialog.stop_btn.isVisible())
        self.assertFalse(dialog.input_field.isReadOnly())

        # When finished signal arrives after stop, it should NOT overwrite "■ Stopped" with "✓ Finished"
        dialog._on_finished("")
        self.assertEqual(dialog.status_lbl.text(), "■ Stopped")


if __name__ == "__main__":
    unittest.main()

