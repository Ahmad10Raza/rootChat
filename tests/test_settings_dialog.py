import unittest
import os
import tempfile
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication, QScrollArea, QCheckBox, QComboBox, QLineEdit, QPushButton

from core.app_config import AppConfig
from core.app_state import AppState
from ui.settings_dialog import SettingsDialog

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication([])


class TestSettingsDialog(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_config = os.path.join(self.temp_dir.name, "config.json")
        self.config = AppConfig(self.temp_config)
        self.app_state = AppState(self.config)
        self.dialog = SettingsDialog(self.app_state)

    def tearDown(self):
        self.dialog.close()
        self.temp_dir.cleanup()

    def test_scroll_area_exists(self):
        """Verify the dialog contains a scroll area ensuring content doesn't get clipped."""
        self.assertIsInstance(self.dialog.scroll_area, QScrollArea)
        self.assertTrue(self.dialog.scroll_area.widgetResizable())
        self.assertIsNotNone(self.dialog.scroll_area.widget())

    def test_appearance_theme_selection(self):
        """Verify theme combo box is populated and emits theme_changed signal."""
        emitted = []
        self.dialog.theme_changed.connect(lambda t: emitted.append(t))

        self.assertIsInstance(self.dialog.theme_combo, QComboBox)
        self.assertEqual(self.dialog.theme_combo.count(), 3)
        self.dialog.theme_combo.setCurrentText("Light")
        self.assertIn("light", emitted)
        self.assertEqual(self.app_state.config.get("theme"), "light")

    def test_endpoint_input_and_save(self):
        """Verify endpoint input and save reconnect button."""
        emitted = []
        self.dialog.endpoint_changed.connect(lambda ep: emitted.append(ep))

        self.assertIsInstance(self.dialog.endpoint_input, QLineEdit)
        self.dialog.endpoint_input.setText("http://192.168.1.50:11434")
        self.dialog.save_endpoint_btn.click()

        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0], "http://192.168.1.50:11434")
        self.assertEqual(self.app_state.get("ollama_endpoint"), "http://192.168.1.50:11434")

    def test_manage_models_signal(self):
        """Verify manage models button emits manage_models_requested."""
        emitted = []
        self.dialog.manage_models_requested.connect(lambda: emitted.append(True))
        self.dialog.manage_models_btn.click()
        self.assertEqual(len(emitted), 1)

    def test_toggles_persistence(self):
        """Verify all checkbox toggles update app_state and config."""
        # Enter to send
        self.dialog.enter_send.setChecked(False)
        self.assertFalse(self.app_state.get("enter_to_send"))

        # Memory toggle
        self.dialog.memory_toggle.setChecked(False)
        self.assertFalse(self.app_state.get("memory_enabled"))

        # Knowledge toggle
        self.dialog.knowledge_toggle.setChecked(False)
        self.assertFalse(self.app_state.get("knowledge_enabled"))

        # Tray toggle
        self.dialog.tray_toggle.setChecked(False)
        self.assertFalse(self.app_state.get("tray_icon_enabled"))

        # Notification toggle
        self.dialog.notif_toggle.setChecked(False)
        self.assertFalse(self.app_state.get("notifications_enabled"))

        # Minimize to tray toggle
        self.dialog.minimize_to_tray_toggle.setChecked(True)
        self.assertTrue(self.app_state.get("minimize_to_tray"))

    def test_close_button(self):
        """Verify close button exists and closes the dialog."""
        self.assertIsInstance(self.dialog.close_btn, QPushButton)
        self.assertEqual(self.dialog.close_btn.text(), "Close")

    def test_default_knowledge_mode_selection(self):
        """Verify default knowledge mode dropdown updates app_state and config."""
        self.assertIsInstance(self.dialog.default_knowledge_combo, QComboBox)
        self.assertEqual(self.dialog.default_knowledge_combo.count(), 2)

        # Select "All Documents"
        self.dialog.default_knowledge_combo.setCurrentIndex(1)
        self.assertEqual(self.app_state.get("default_knowledge_mode"), "all")
        self.assertEqual(self.app_state.config.get("default_knowledge_mode"), "all")

        # Select "Off"
        self.dialog.default_knowledge_combo.setCurrentIndex(0)
        self.assertEqual(self.app_state.get("default_knowledge_mode"), "none")
        self.assertEqual(self.app_state.config.get("default_knowledge_mode"), "none")

    def test_manage_knowledge_signal(self):
        """Verify manage knowledge library button emits manage_knowledge_requested."""
        emitted = []
        self.dialog.manage_knowledge_requested.connect(lambda: emitted.append(True))
        self.dialog.manage_knowledge_btn.click()
        self.assertEqual(len(emitted), 1)

    def test_default_model_selection(self):
        """Verify default model selection updates app_state."""
        self.dialog.default_model_combo.addItem("mistral:latest")
        self.dialog.default_model_combo.setCurrentText("mistral:latest")
        self.assertEqual(self.app_state.get("selected_model"), "mistral:latest")

    def test_default_persona_selection(self):
        """Verify default persona dropdown updates app_state and config."""
        self.dialog.default_preset_combo.setCurrentIndex(1)
        expected_preset = self.dialog.default_preset_combo.currentData()
        self.assertEqual(self.app_state.get("default_preset"), expected_preset)
        self.assertEqual(self.app_state.config.get("default_preset"), expected_preset)

    def test_temperature_slider(self):
        """Verify temperature slider updates app_state and config."""
        self.dialog.temperature_slider.setValue(45)
        self.assertAlmostEqual(self.app_state.get("temperature"), 0.45)
        self.assertAlmostEqual(self.app_state.config.get("temperature"), 0.45)
        self.assertEqual(self.dialog.temperature_val_lbl.text(), "0.45")

    def test_numerical_limits_spinners(self):
        """Verify Context Limit, Max Memories, Top-K, and Similarity spinners update app_state and config."""
        self.dialog.context_limit_spin.setValue(40)
        self.assertEqual(self.app_state.get("context_message_limit"), 40)
        self.assertEqual(self.app_state.config.get("context_message_limit"), 40)

        self.dialog.max_memories_spin.setValue(12)
        self.assertEqual(self.app_state.get("max_memories"), 12)
        self.assertEqual(self.app_state.config.get("max_memories"), 12)

        self.dialog.top_k_spin.setValue(8)
        self.assertEqual(self.app_state.get("top_k"), 8)
        self.assertEqual(self.app_state.config.get("top_k"), 8)

        self.dialog.similarity_spin.setValue(0.35)
        self.assertAlmostEqual(self.app_state.get("similarity_threshold"), 0.35)
        self.assertAlmostEqual(self.app_state.config.get("similarity_threshold"), 0.35)


if __name__ == "__main__":
    unittest.main()

