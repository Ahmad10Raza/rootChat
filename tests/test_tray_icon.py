import os
import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QCloseEvent

import tempfile
from core.app_config import AppConfig
from core.app_state import AppState
from ui.tray_icon import RootChatTrayIcon

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication([])


class TestTrayIcon(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = AppConfig(os.path.join(self.temp_dir.name, "config.json"))
        self.app_state = AppState(self.config)
        self.dummy_window = QWidget()

    def tearDown(self):
        self.dummy_window.close()
        self.temp_dir.cleanup()

    def test_init_tray_icon(self):
        tray = RootChatTrayIcon(self.dummy_window, self.app_state)
        self.assertIsNotNone(tray.menu)
        self.assertEqual(len(tray.menu.actions()), 8)  # 5 actions + 3 separators
        self.assertEqual(tray.toolTip(), "rootChat — Private AI for Linux")

    def test_toggle_window_visibility(self):
        tray = RootChatTrayIcon(self.dummy_window, self.app_state)
        
        # Initially dummy_window is hidden
        self.assertFalse(self.dummy_window.isVisible())
        tray._toggle_window()
        self.assertTrue(self.dummy_window.isVisible())
        self.assertEqual(tray.toggle_action.text(), "Hide rootChat")

        tray._toggle_window()
        self.assertFalse(self.dummy_window.isVisible())
        self.assertEqual(tray.toggle_action.text(), "Show rootChat")

    def test_tray_signals(self):
        tray = RootChatTrayIcon(self.dummy_window, self.app_state)
        
        new_chat_called = []
        mini_chat_called = []
        settings_called = []

        tray.new_chat_requested.connect(lambda: new_chat_called.append(True))
        tray.mini_chat_requested.connect(lambda: mini_chat_called.append(True))
        tray.settings_requested.connect(lambda: settings_called.append(True))

        tray._on_new_chat()
        tray._on_mini_chat()
        tray._on_settings()

        self.assertEqual(len(new_chat_called), 1)
        self.assertEqual(len(mini_chat_called), 1)
        self.assertEqual(len(settings_called), 1)

    @patch("ui.tray_icon.RootChatTrayIcon.showMessage")
    def test_notify_response_ready(self, mock_show_message):
        tray = RootChatTrayIcon(self.dummy_window, self.app_state)

        # Enabled by default
        self.app_state.set("notifications_enabled", True)
        tray.notify_response_ready("llama3.2", "Here is the code you asked for.")
        mock_show_message.assert_called_once()
        self.assertIn("llama3.2", mock_show_message.call_args[0][1])

        # Disabled in settings
        mock_show_message.reset_mock()
        self.app_state.set("notifications_enabled", False)
        tray.notify_response_ready("llama3.2", "Another response")
        mock_show_message.assert_not_called()

    def test_minimize_to_tray_on_close(self):
        from ui.main_window import MainWindow
        from core.ollama_client import OllamaClient
        from database.database import DatabaseManager

        test_db = "/tmp/test_tray_main_db.sqlite"
        if os.path.exists(test_db):
            os.remove(test_db)

        db_mgr = DatabaseManager(test_db)
        client = OllamaClient()
        main_win = MainWindow(self.app_state, client, db_mgr)
        # Ensure tray_icon is attached for offscreen test environment
        main_win.tray_icon = RootChatTrayIcon(main_win, self.app_state)
        main_win.tray_icon.showMessage = MagicMock()
        main_win.show()

        # Default minimize_to_tray is False
        self.app_state.set("minimize_to_tray", False)
        event = QCloseEvent()
        main_win.closeEvent(event)
        self.assertTrue(event.isAccepted())

        # Enable minimize_to_tray
        self.app_state.set("minimize_to_tray", True)
        self.app_state.set("tray_icon_enabled", True)
        event2 = QCloseEvent()
        main_win.closeEvent(event2)
        self.assertFalse(event2.isAccepted())  # event.ignore() was called
        self.assertFalse(main_win.isVisible())

        main_win.close()
        if os.path.exists(test_db):
            os.remove(test_db)


if __name__ == "__main__":
    unittest.main()
