import os
import unittest
import tempfile
import json
import sqlite3
from unittest.mock import patch, MagicMock
import requests

# Set environment before imports to ensure logging doesn't fail
from core.ollama_client import OllamaClient
from core.app_config import AppConfig
from database.database import DatabaseManager
from config.default_config import DEFAULT_CONFIG

class TestOllamaClient(unittest.TestCase):
    """Tests the OllamaClient using mocked HTTP responses."""

    def setUp(self):
        self.client = OllamaClient("http://localhost:11434")

    @patch("requests.get")
    def test_connection_success(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Act
        is_connected, msg = self.client.check_connection()

        # Assert
        self.assertTrue(is_connected)
        self.assertEqual(msg, "Connected")
        mock_get.assert_called_once_with("http://localhost:11434", timeout=3.0)

    @patch("requests.get")
    def test_connection_offline(self, mock_get):
        # Arrange
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        # Act
        is_connected, msg = self.client.check_connection()

        # Assert
        self.assertFalse(is_connected)
        self.assertEqual(msg, "Offline")

    @patch("requests.get")
    def test_connection_timeout(self, mock_get):
        # Arrange
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        # Act
        is_connected, msg = self.client.check_connection()

        # Assert
        self.assertFalse(is_connected)
        self.assertEqual(msg, "Connection Timeout")

    @patch("requests.get")
    def test_list_models_success(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "llama3.2:3b",
                    "model": "llama3.2:3b",
                    "size": 2013919,
                    "modified_at": "2026-08-16T12:00:00Z",
                    "details": {"family": "llama"}
                },
                {
                    "name": "gemma:7b",
                    "model": "gemma:7b",
                    "size": 4800000,
                    "modified_at": "2026-08-16T12:05:00Z",
                    "details": {"family": "gemma"}
                }
            ]
        }
        mock_get.return_value = mock_response

        # Act
        models = self.client.list_models()

        # Assert
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]["name"], "llama3.2:3b")
        self.assertEqual(models[0]["family"], "llama")
        self.assertEqual(models[1]["name"], "gemma:7b")
        self.assertEqual(models[1]["family"], "gemma")

    @patch("requests.get")
    def test_list_models_error(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Act
        models = self.client.list_models()

        # Assert
        self.assertEqual(models, [])


class TestAppConfig(unittest.TestCase):
    """Tests the AppConfig class with configuration load and save properties."""

    def setUp(self):
        # Use a temporary file for config to isolate test runs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_config_path = os.path.join(self.temp_dir.name, "config.json")
        
        # Patch CONFIG_FILE in core.app_config to use our temporary file path
        self.patcher = patch("core.app_config.CONFIG_FILE", self.temp_config_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_default_configuration(self):
        config = AppConfig()
        self.assertEqual(config.get("ollama_endpoint"), DEFAULT_CONFIG["ollama_endpoint"])
        self.assertEqual(config.get("selected_model"), DEFAULT_CONFIG["selected_model"])
        self.assertEqual(config.get("theme"), DEFAULT_CONFIG["theme"])

    def test_save_load_configuration(self):
        config = AppConfig()
        config.set("selected_model", "llama3.2:3b")
        config.set("theme", "dark")
        
        # Instantiate a new config instance and verify it loads the saved values
        new_config = AppConfig()
        self.assertEqual(new_config.get("selected_model"), "llama3.2:3b")
        self.assertEqual(new_config.get("theme"), "dark")

    def test_load_corrupted_config_falls_back_to_defaults(self):
        # Write corrupted JSON to the file path
        with open(self.temp_config_path, "w") as f:
            f.write("invalid json content")
            
        config = AppConfig()
        self.assertEqual(config.get("ollama_endpoint"), DEFAULT_CONFIG["ollama_endpoint"])


class TestDatabaseManager(unittest.TestCase):
    """Tests the SQLite DatabaseManager tables initialization."""

    def setUp(self):
        # Use a temporary directory and file for the database to ensure isolation
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_rootChat.db")
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_initialization(self):
        # Get list of created tables
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        conn.close()

        # Assert all required tables exist
        self.assertIn("conversations", tables)
        self.assertIn("messages", tables)
        self.assertIn("memories", tables)
        self.assertIn("settings", tables)

    def test_foreign_key_enforcement(self):
        # Verify that foreign key constraint prevents adding message with invalid conversation ID
        conn = self.db.get_connection()
        cursor = conn.cursor()
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (999, 'user', 'hello');"
            )
        conn.close()

if __name__ == "__main__":
    unittest.main()
