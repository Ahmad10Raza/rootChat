import os
import json
import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication

from core.ollama_client import OllamaClient
from core.app_config import AppConfig
from core.app_state import AppState
from core.ollama_worker import OllamaPullWorker, OllamaDeleteWorker, OllamaShowWorker
from ui.model_manager_dialog import ModelManagerDialog, format_size

import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication([])


class TestModelManager(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.tmp_dir.name, "config.json")
        self.client = OllamaClient("http://localhost:11434")
        self.config = AppConfig(self.config_path)
        self.app_state = AppState(self.config)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_format_size(self):
        self.assertEqual(format_size(0), "Unknown")
        self.assertEqual(format_size(-10), "Unknown")
        self.assertEqual(format_size(500), "500.0 B")
        self.assertEqual(format_size(2048), "2.0 KB")
        self.assertEqual(format_size(10 * 1024 * 1024), "10.0 MB")
        self.assertEqual(format_size(3 * 1024 * 1024 * 1024), "3.0 GB")

    @patch("requests.post")
    def test_pull_model_stream(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"status": "pulling manifest"}',
            b'{"status": "downloading", "completed": 500, "total": 1000}',
            b'{"status": "success"}'
        ]
        mock_response.__enter__.return_value = mock_response
        mock_post.return_value = mock_response

        chunks = list(self.client.pull_model("llama3.2"))
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["status"], "pulling manifest")
        self.assertEqual(chunks[1]["completed"], 500)
        self.assertEqual(chunks[2]["status"], "success")

    @patch("requests.post")
    def test_pull_model_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"error": "model not found"}'
        ]
        mock_response.__enter__.return_value = mock_response
        mock_post.return_value = mock_response

        with self.assertRaises(Exception) as ctx:
            list(self.client.pull_model("invalid-model-xyz"))
        self.assertIn("model not found", str(ctx.exception))

    @patch("requests.delete")
    def test_delete_model_success(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response

        success, msg = self.client.delete_model("llama3.2")
        self.assertTrue(success)
        self.assertIn("deleted successfully", msg)

    @patch("requests.delete")
    def test_delete_model_failure(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "model 'nonexistent' not found"}
        mock_delete.return_value = mock_response

        success, msg = self.client.delete_model("nonexistent")
        self.assertFalse(success)
        self.assertIn("Failed to delete", msg)

    def test_ollama_pull_worker_progress_and_finish(self):
        worker = OllamaPullWorker(self.client, "test-model")
        
        # Mock client.pull_model
        mock_chunks = [
            {"status": "downloading", "completed": 50, "total": 100},
            {"status": "success"}
        ]
        self.client.pull_model = MagicMock(return_value=iter(mock_chunks))
        
        progress_events = []
        finished_events = []
        
        worker.progress.connect(lambda p: progress_events.append(p))
        worker.finished.connect(lambda m: finished_events.append(m))
        
        worker.run()
        
        self.assertEqual(len(progress_events), 2)
        self.assertEqual(progress_events[0]["percent"], 50.0)
        self.assertEqual(finished_events, ["test-model"])

    def test_ollama_delete_worker(self):
        worker = OllamaDeleteWorker(self.client, "test-model")
        self.client.delete_model = MagicMock(return_value=(True, "Deleted successfully"))
        
        results = []
        worker.finished.connect(lambda s, m: results.append((s, m)))
        worker.run()
        
        self.assertEqual(results, [(True, "Deleted successfully")])

    def test_ollama_show_worker(self):
        worker = OllamaShowWorker(self.client, "test-model")
        self.client.get_model_info = MagicMock(return_value={"details": {"family": "llama"}})
        
        results = []
        worker.finished.connect(lambda m, info: results.append((m, info)))
        worker.run()
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "test-model")
        self.assertEqual(results[0][1]["details"]["family"], "llama")

    def test_model_manager_dialog_ui(self):
        # Mock client list_models to return test data
        self.client.list_models = MagicMock(return_value=[
            {"name": "llama3.2:latest", "size": 2048 * 1024 * 1024, "family": "llama"},
            {"name": "qwen2.5:3b", "size": 1900 * 1024 * 1024, "family": "qwen2"}
        ])
        self.client.get_model_info = MagicMock(return_value={
            "details": {
                "parameter_size": "3.2B",
                "quantization_level": "Q4_K_M",
                "family": "llama"
            },
            "model_info": {
                "llama.context_length": 131072
            }
        })
        
        dialog = ModelManagerDialog(self.client, self.app_state)
        
        # Manually populate models
        dialog._on_models_fetched([
            {"name": "llama3.2:latest", "size": 2048 * 1024 * 1024, "family": "llama"},
            {"name": "qwen2.5:3b", "size": 1900 * 1024 * 1024, "family": "qwen2"}
        ])
        
        self.assertEqual(dialog.model_list.count(), 2)
        
        # Set active model
        dialog.model_list.setCurrentRow(1)
        dialog._on_use_active_clicked()
        self.assertEqual(self.app_state.get("selected_model"), "qwen2.5:3b")

    def test_model_manager_search_filter(self):
        dialog = ModelManagerDialog(self.client, self.app_state)
        dialog._on_models_fetched([
            {"name": "llama3.2:latest", "size": 2048 * 1024 * 1024, "family": "llama"},
            {"name": "deepseek-r1:7b", "size": 4683075440, "family": "qwen2"},
            {"name": "glm-4.7:cloud", "size": 327, "remote_model": "glm-4.7"}
        ])
        self.assertEqual(dialog.model_list.count(), 3)
        self.assertEqual(dialog.model_count_badge.text(), "3 Models")

        # Filter for deepseek
        dialog.search_input.setText("deepseek")
        self.assertEqual(dialog.model_list.count(), 1)
        self.assertIn("deepseek-r1:7b", dialog.model_list.item(0).text())

        # Clear filter
        dialog.search_input.setText("")
        self.assertEqual(dialog.model_list.count(), 3)

    def test_model_manager_cloud_model_specs(self):
        dialog = ModelManagerDialog(self.client, self.app_state)
        dialog._on_models_fetched([
            {"name": "glm-4.7:cloud", "size": 327, "remote_model": "glm-4.7", "remote_host": "https://ollama.com:443"}
        ])
        dialog.model_list.setCurrentRow(0)

        # Trigger model info fetched for cloud model
        cloud_info = {
            "remote_model": "glm-4.7",
            "remote_host": "https://ollama.com:443",
            "capabilities": ["completion", "tools", "thinking"],
            "details": {
                "parameter_size": "",
                "quantization_level": "",
                "family": ""
            },
            "model_info": {}
        }
        dialog._on_model_info_fetched("glm-4.7:cloud", cloud_info)

        self.assertEqual(dialog.details_name_lbl.text(), "glm-4.7:cloud")
        self.assertEqual(dialog.details_params_lbl.text(), "Parameters: Cloud Managed")
        self.assertEqual(dialog.details_quant_lbl.text(), "Quantization: Cloud API")
        self.assertEqual(dialog.details_family_lbl.text(), "Family: glm-4.7")
        self.assertIn("completion, tools, thinking", dialog.details_caps_lbl.text())
        self.assertEqual(dialog.details_host_lbl.text(), "Remote Host: https://ollama.com:443")
        self.assertFalse(dialog.details_type_badge.isHidden())
        self.assertEqual(dialog.details_type_badge.text(), "🌐 Cloud Proxy")


if __name__ == "__main__":
    unittest.main()
