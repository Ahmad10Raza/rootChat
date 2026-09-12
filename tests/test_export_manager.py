import json
import unittest
from core.export_manager import (
    sanitize_filename,
    export_to_markdown,
    export_to_txt,
    export_to_json
)

class TestExportManager(unittest.TestCase):
    def setUp(self):
        self.conversation = {
            "id": 42,
            "title": "Python Asyncio Guide",
            "model": "llama3.2:3b",
            "is_pinned": 1,
            "is_archived": 0,
            "created_at": "2026-09-12 12:00:00",
            "updated_at": "2026-09-12 12:30:00"
        }
        self.messages = [
            {"id": 1, "role": "user", "content": "Explain asyncio in Python.", "created_at": "2026-09-12 12:00:05"},
            {"id": 2, "role": "assistant", "content": "Asyncio is a library to write concurrent code.", "created_at": "2026-09-12 12:00:10"}
        ]

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("Valid Name"), "Valid_Name")
        self.assertEqual(sanitize_filename("Invalid: / * ? < > | Name"), "Invalid_Name")
        self.assertEqual(sanitize_filename("   "), "conversation")

    def test_export_to_markdown(self):
        md = export_to_markdown(self.conversation, self.messages)
        self.assertIn("# Python Asyncio Guide", md)
        self.assertIn("- **Model:** `llama3.2:3b`", md)
        self.assertIn("### 👤 User", md)
        self.assertIn("Explain asyncio in Python.", md)
        self.assertIn("### 🤖 Assistant", md)
        self.assertIn("Asyncio is a library to write concurrent code.", md)

    def test_export_to_txt(self):
        txt = export_to_txt(self.conversation, self.messages)
        self.assertIn("TITLE: Python Asyncio Guide", txt)
        self.assertIn("MODEL: llama3.2:3b", txt)
        self.assertIn("[USER]", txt)
        self.assertIn("Explain asyncio in Python.", txt)
        self.assertIn("[ASSISTANT]", txt)
        self.assertIn("Asyncio is a library to write concurrent code.", txt)

    def test_export_to_json(self):
        json_str = export_to_json(self.conversation, self.messages)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["conversation"]["id"], 42)
        self.assertEqual(parsed["conversation"]["title"], "Python Asyncio Guide")
        self.assertEqual(len(parsed["messages"]), 2)
        self.assertEqual(parsed["messages"][0]["role"], "user")
        self.assertEqual(parsed["messages"][1]["role"], "assistant")

if __name__ == "__main__":
    unittest.main()
