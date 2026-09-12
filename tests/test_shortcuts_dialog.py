import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication

from ui.shortcuts_dialog import ShortcutsDialog, SHORTCUTS_DATA
from ui.main_window import MainWindow
from core.app_state import AppState
from core.app_config import AppConfig

app = QApplication.instance()
if not app:
    app = QApplication([])


class TestShortcutsDialog(unittest.TestCase):
    def setUp(self):
        self.dialog = ShortcutsDialog()

    def test_initial_state(self):
        self.assertEqual(self.dialog.windowTitle(), "Keyboard Shortcuts")
        self.assertFalse(self.dialog.search_input.text())
        # Check all categories from data are populated
        self.assertTrue(len(self.dialog.rows) >= 12)
        category_names = [d["category"] for d in SHORTCUTS_DATA]
        self.assertIn("Navigation & Layout", category_names)
        self.assertIn("Quick Access & Popups", category_names)
        self.assertIn("Chat & Messaging", category_names)

    def test_filter_shortcuts(self):
        # Filter by "sidebar"
        self.dialog.search_input.setText("sidebar")
        visible_rows = [r for r, _, _ in self.dialog.rows if not r.isHidden()]
        self.assertTrue(len(visible_rows) >= 1)

        # Filter by something non-existent
        self.dialog.search_input.setText("xyz123nonsense")
        visible_rows = [r for r, _, _ in self.dialog.rows if not r.isHidden()]
        self.assertEqual(len(visible_rows), 0)

        # Clear filter
        self.dialog.search_input.setText("")
        visible_rows = [r for r, _, _ in self.dialog.rows if not r.isHidden()]
        self.assertEqual(len(visible_rows), len(self.dialog.rows))

    def test_close_button(self):
        self.assertEqual(self.dialog.close_btn.text(), "Close")


class TestMainWindowShortcutsIntegration(unittest.TestCase):
    @patch("ui.main_window.OllamaClient")
    @patch("ui.main_window.DatabaseManager")
    def test_shortcuts_button_exists(self, MockDB, MockClient):
        config = AppConfig()
        state = AppState(config)
        client = MagicMock()
        client.check_connection.return_value = (True, "Connected")
        db = MagicMock()
        db.get_connection.return_value = MagicMock()
        main_win = MainWindow(state, client, db)

        self.assertIsNotNone(main_win.shortcuts_btn)
        self.assertIn("Shortcuts", main_win.shortcuts_btn.toolTip())

        # Test _open_shortcuts_dialog call
        with patch("ui.shortcuts_dialog.ShortcutsDialog.exec") as mock_exec:
            main_win._open_shortcuts_dialog()
            mock_exec.assert_called_once()


if __name__ == "__main__":
    unittest.main()
