import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication

from ui.status_bar import StatusBar
from core.stream_worker import StreamWorker
from core.chat_manager import ChatManager
from core.app_state import AppState
from core.app_config import AppConfig
from database.database import DatabaseManager

app = QApplication.instance()
if not app:
    app = QApplication([])

class TestStatusBar(unittest.TestCase):
    def setUp(self):
        self.status_bar = StatusBar()

    def test_initial_state(self):
        self.assertEqual(self.status_bar.status_text.text(), "Ollama: Offline")
        self.assertEqual(self.status_bar.model_text.text(), "Model: None")
        self.assertEqual(self.status_bar.msg_count_text.text(), "💬 0 messages")
        self.assertTrue(self.status_bar.speed_text.isHidden())
        self.assertTrue(self.status_bar.context_text.isHidden())

    def test_connection_status(self):
        self.status_bar.update_connection_status(True, "Connected")
        self.assertEqual(self.status_bar.status_text.text(), "Ollama: Connected")
        self.assertIn("#35C759", self.status_bar.status_dot.styleSheet())

        self.status_bar.update_connection_status(False, "Offline")
        self.assertEqual(self.status_bar.status_text.text(), "Ollama: Offline")
        self.assertIn("#FF5555", self.status_bar.status_dot.styleSheet())

    def test_model_selection(self):
        self.status_bar.update_selected_model("llama3.2:1b")
        self.assertEqual(self.status_bar.model_text.text(), "Model: llama3.2:1b")

        self.status_bar.update_selected_model("")
        self.assertEqual(self.status_bar.model_text.text(), "Model: None")

    def test_message_counts(self):
        self.status_bar.set_message_count(1)
        self.assertEqual(self.status_bar.msg_count_text.text(), "💬 1 message")

        self.status_bar.increment_message_count()
        self.assertEqual(self.status_bar.msg_count_text.text(), "💬 2 messages")

        self.status_bar.decrement_message_count()
        self.assertEqual(self.status_bar.msg_count_text.text(), "💬 1 message")

        self.status_bar.decrement_message_count(5)
        self.assertEqual(self.status_bar.msg_count_text.text(), "💬 0 messages")

    def test_generation_active_toggle(self):
        self.status_bar.set_generation_active(True)
        self.assertEqual(self.status_bar.speed_text.text(), "⚡ Generating...")
        self.assertFalse(self.status_bar.speed_text.isHidden())

        self.status_bar.set_generation_active(False)
        self.assertEqual(self.status_bar.speed_text.text(), "")
        self.assertTrue(self.status_bar.speed_text.isHidden())

    def test_update_generation_stats(self):
        stats = {
            "eval_count": 282,
            "eval_duration": 4799927000,
            "prompt_eval_count": 26,
            "prompt_eval_duration": 383809000,
            "total_duration": 5191566416,
            "eval_rate": 58.8
        }
        self.status_bar.update_generation_stats(stats)
        self.assertIn("282 tokens", self.status_bar.speed_text.text())
        self.assertIn("58.8 tok/s", self.status_bar.speed_text.text())
        self.assertFalse(self.status_bar.speed_text.isHidden())
        self.assertIn("Prompt context: 26 tokens", self.status_bar.speed_text.toolTip())

        # Empty stats hides speed meter
        self.status_bar.update_generation_stats({})
        self.assertTrue(self.status_bar.speed_text.isHidden())

    def test_context_stats(self):
        # 1 memory, 0 sources
        self.status_bar.set_context_stats(1, 0)
        self.assertEqual(self.status_bar.context_text.text(), "🧠 1 memory")
        self.assertFalse(self.status_bar.context_text.isHidden())

        # 3 memories, 2 sources
        self.status_bar.set_context_stats(3, 2)
        self.assertEqual(self.status_bar.context_text.text(), "🧠 3 memories • 📚 2 sources")

        # 0 memories, 0 sources -> hidden
        self.status_bar.set_context_stats(0, 0)
        self.assertTrue(self.status_bar.context_text.isHidden())

    def test_reset_session_stats(self):
        self.status_bar.set_message_count(5)
        self.status_bar.set_context_stats(2, 1)
        self.status_bar.update_generation_stats({"eval_count": 100, "eval_rate": 25.0, "eval_duration": 4000000000})

        self.status_bar.reset_session_stats()
        self.assertEqual(self.status_bar.msg_count_text.text(), "💬 0 messages")
        self.assertTrue(self.status_bar.context_text.isHidden())
        self.assertTrue(self.status_bar.speed_text.isHidden())


class TestStreamWorkerStats(unittest.TestCase):
    def test_stream_worker_extracts_stats(self):
        mock_client = MagicMock()
        mock_client.stream_chat.return_value = [
            {"message": {"role": "assistant", "content": "Hello"}},
            {"message": {"role": "assistant", "content": " world!"}},
            {
                "done": True,
                "eval_count": 100,
                "eval_duration": 2000000000,  # 2 seconds -> 50 tok/s
                "prompt_eval_count": 10,
                "prompt_eval_duration": 500000000,
                "total_duration": 2500000000
            }
        ]

        worker = StreamWorker(mock_client, "test-model", [{"role": "user", "content": "hi"}])
        received_stats = []
        worker.stats_received.connect(lambda s: received_stats.append(s))
        
        # Run worker synchronously
        worker.run()

        self.assertEqual(len(received_stats), 1)
        s = received_stats[0]
        self.assertEqual(s["eval_count"], 100)
        self.assertEqual(s["eval_rate"], 50.0)
        self.assertEqual(s["prompt_eval_count"], 10)


class TestChatManagerStatsIntegration(unittest.TestCase):
    @patch("core.chat_manager.StreamWorker")
    def test_chat_manager_stats_wiring(self, MockStreamWorker):
        db = DatabaseManager(":memory:")
        config = AppConfig()
        state = AppState(config)
        client = MagicMock()
        mem_mgr = MagicMock()
        ctx_mgr = MagicMock()
        ctx_mgr.build_context.return_value = [{"role": "user", "content": "test"}]

        manager = ChatManager(state, client, db, mem_mgr, ctx_mgr)
        
        # Test start_new_conversation resets stats
        state.set("last_memories_used", 3)
        state.set("last_sources_used", 2)
        state.set("last_generation_stats", {"eval_count": 50})
        manager.start_new_conversation()

        self.assertEqual(state.get("last_memories_used"), 0)
        self.assertEqual(state.get("last_sources_used"), 0)
        self.assertEqual(state.get("last_generation_stats"), {})

        # Test stats_received emission
        emitted = []
        manager.stats_received.connect(lambda s: emitted.append(s))
        manager._on_stats_received({"eval_count": 80, "eval_rate": 40.0})

        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0]["eval_count"], 80)
        self.assertEqual(state.get("last_generation_stats")["eval_rate"], 40.0)

if __name__ == "__main__":
    unittest.main()
