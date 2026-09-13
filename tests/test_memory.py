import os
import tempfile
import unittest
from PySide6.QtWidgets import QApplication
from database.database import DatabaseManager
from database.repositories.memory_repository import MemoryRepository
from core.memory_manager import (
    MemoryManager,
    normalize_grammar,
    classify_category,
    cosine_similarity,
    STOP_WORDS
)
from core.app_state import AppState
from core.app_config import AppConfig
from ui.memory_dialog import MemoryDialog, MemoryCardWidget, MemoryEditorModal


# Create QApplication instance if not already existing
app = QApplication.instance()
if not app:
    app = QApplication([])


class MockEmbeddingProvider:
    """Mock embedding provider for deterministic vector similarity tests."""

    def __init__(self):
        # Map of keywords to 3D dummy vectors
        self.vectors = {
            "python": [1.0, 0.0, 0.0],
            "coding": [0.95, 0.1, 0.0],
            "berlin": [0.0, 1.0, 0.0],
            "germany": [0.0, 0.98, 0.1],
            "coffee": [0.0, 0.0, 1.0],
            "cafe": [0.0, 0.0, 0.99],
        }

    def embed_query(self, text: str) -> list[float]:
        text_lower = text.lower()
        for kw, vec in self.vectors.items():
            if kw in text_lower:
                return vec
        return [0.0, 0.0, 0.0]


class TestMemoryRepository(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.mktemp(suffix=".db")
        self.db = DatabaseManager(self.temp_db)
        self.repo = MemoryRepository(self.db)

    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)

    def test_create_and_get_memory(self):
        mem_id = self.repo.create_memory("User likes dark mode", category="preference", source="user")
        self.assertIsNotNone(mem_id)

        mem = self.repo.get_memory(mem_id)
        self.assertIsNotNone(mem)
        self.assertEqual(mem["content"], "User likes dark mode")
        self.assertEqual(mem["category"], "preference")
        self.assertEqual(mem["source"], "user")
        self.assertEqual(mem["is_enabled"], 1)

    def test_embedding_storage_and_retrieval(self):
        embedding_vec = [0.123, -0.456, 0.789]
        mem_id = self.repo.create_memory("Vector test", embedding=embedding_vec)

        active = self.repo.get_active_memories_with_embeddings()
        self.assertEqual(len(active), 1)
        self.assertIsNotNone(active[0]["embedding"])
        self.assertAlmostEqual(active[0]["embedding"][0], 0.123, places=3)
        self.assertAlmostEqual(active[0]["embedding"][1], -0.456, places=3)
        self.assertAlmostEqual(active[0]["embedding"][2], 0.789, places=3)

    def test_update_and_delete_memory(self):
        mem_id = self.repo.create_memory("Initial text", category="general")
        self.repo.update_memory(mem_id, content="Updated text", category="work", is_enabled=False)

        mem = self.repo.get_memory(mem_id)
        self.assertEqual(mem["content"], "Updated text")
        self.assertEqual(mem["category"], "work")
        self.assertEqual(mem["is_enabled"], 0)

        # Active list should now exclude it
        active = self.repo.get_active_memories_with_embeddings()
        self.assertEqual(len(active), 0)

        # Delete
        self.repo.delete_memory(mem_id)
        self.assertIsNone(self.repo.get_memory(mem_id))

    def test_list_with_category_and_search_filter(self):
        self.repo.create_memory("Prefers tabs over spaces", category="preference")
        self.repo.create_memory("Software engineer in Berlin", category="work")
        self.repo.create_memory("Has two cats", category="personal")

        # Category filter
        pref_list = self.repo.list_memories(category="preference")
        self.assertEqual(len(pref_list), 1)
        self.assertEqual(pref_list[0]["category"], "preference")

        # Search filter
        berlin_list = self.repo.list_memories(search="berlin")
        self.assertEqual(len(berlin_list), 1)
        self.assertIn("Berlin", berlin_list[0]["content"])

    def test_get_stats(self):
        self.repo.create_memory("Mem 1", category="preference")
        self.repo.create_memory("Mem 2", category="work")
        m3 = self.repo.create_memory("Mem 3", category="work")
        self.repo.update_memory(m3, is_enabled=False)

        stats = self.repo.get_stats()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["active"], 2)
        self.assertEqual(stats["by_category"].get("work"), 2)
        self.assertEqual(stats["by_category"].get("preference"), 1)


class TestMemoryManagerCore(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.mktemp(suffix=".db")
        self.temp_cfg = tempfile.mktemp(suffix=".json")
        self.db = DatabaseManager(self.temp_db)
        self.repo = MemoryRepository(self.db)
        self.config = AppConfig(self.temp_cfg)
        self.app_state = AppState(self.config)
        self.embedding_provider = MockEmbeddingProvider()
        self.manager = MemoryManager(self.app_state, self.repo, embedding_provider=self.embedding_provider)

    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
        if os.path.exists(self.temp_cfg):
            os.remove(self.temp_cfg)

    def test_grammar_normalization(self):
        self.assertEqual(normalize_grammar("I am a software architect"), "User is a software architect")
        self.assertEqual(normalize_grammar("my favorite language is Python"), "User's favorite language is Python")
        self.assertEqual(normalize_grammar("I like dark mode"), "User likes dark mode")

    def test_category_classification(self):
        self.assertEqual(classify_category("I prefer dark mode"), "preference")
        self.assertEqual(classify_category("I work as a Python engineer"), "work")
        self.assertEqual(classify_category("I live in Berlin with my dog"), "personal")
        self.assertEqual(classify_category("Water boils at 100 degrees Celsius"), "general")

    def test_intent_parsing(self):
        # Pure remember
        intent, content, cat, rem = self.manager.parse_memory_intent("Please remember that I love Python")
        self.assertEqual(intent, "remember")
        self.assertIn("Python", content)
        self.assertEqual(cat, "preference")
        self.assertEqual(rem, "")

        # Hybrid remember + question
        intent, content, cat, rem = self.manager.parse_memory_intent("Remember that I live in Munich. What is the weather like?")
        self.assertEqual(intent, "remember")
        self.assertIn("Munich", content)
        self.assertEqual(cat, "personal")
        self.assertEqual(rem, "What is the weather like?")

        # Forget
        intent, content, cat, rem = self.manager.parse_memory_intent("Please forget that I live in Munich")
        self.assertEqual(intent, "forget")
        self.assertIn("Munich", content)

    def test_stopword_filtering_prevents_false_positives(self):
        # Insert memories with common words
        self.manager.create_memory("User prefers Python for scripting", category="preference")
        self.manager.create_memory("User is based in Munich", category="personal")

        # Query with common stopwords: "Where is the best cafe in Berlin?"
        # None of the content words (cafe, berlin) match the stored memories.
        # Stopwords 'where', 'is', 'the', 'in' MUST NOT trigger a false retrieval.
        results = self.manager.get_relevant_memories("Where is the best cafe in Berlin?")
        self.assertEqual(len(results), 0)

    def test_semantic_vector_retrieval(self):
        # Stored memory contains 'berlin'
        self.manager.create_memory("User is living in Berlin", category="personal")
        # Stored memory contains 'coding'
        self.manager.create_memory("User loves coding systems", category="work")

        # Query asking about 'Germany' should retrieve 'Berlin' via vector cosine similarity
        results = self.manager.get_relevant_memories("What city do I live in in Germany?")
        self.assertTrue(len(results) > 0)
        self.assertIn("Berlin", results[0]["content"])

    def test_global_toggle_disables_retrieval(self):
        self.manager.create_memory("User loves Python", category="preference")
        self.app_state.set("memory_enabled", False)

        results = self.manager.get_relevant_memories("What is my favorite language?")
        self.assertEqual(len(results), 0)

    def test_forget_memory_deletes_record(self):
        self.manager.create_memory("User lives in Tokyo", category="personal")
        self.assertEqual(len(self.repo.list_memories()), 1)

        deleted = self.manager.forget_memory("Tokyo")
        self.assertIn("Tokyo", deleted)
        self.assertEqual(len(self.repo.list_memories()), 0)

    def test_stemmed_lexical_retrieval(self):
        # Create memory with plural word "microservices"
        self.manager.create_memory("User develops backend microservices in Go and Docker", category="work")
        # Query with singular word "microservice"
        results = self.manager.get_relevant_memories("How should I deploy my microservice?")
        self.assertEqual(len(results), 1)
        self.assertIn("Go and Docker", results[0]["content"])

    def test_backfill_missing_embeddings(self):
        # Insert raw memory without embedding
        mem_id = self.repo.create_memory("User writes python scripts", category="work")
        mem_before = self.repo.get_memory(mem_id)
        self.assertIsNone(mem_before.get("embedding"))

        # Run backfill
        self.manager.backfill_missing_embeddings()
        mem_after = self.repo.get_active_memories_with_embeddings()
        matching = [m for m in mem_after if m["id"] == mem_id]
        self.assertEqual(len(matching), 1)
        self.assertIsNotNone(matching[0]["embedding"])


class TestMemoryUIComponents(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.mktemp(suffix=".db")
        self.temp_cfg = tempfile.mktemp(suffix=".json")
        self.db = DatabaseManager(self.temp_db)
        self.repo = MemoryRepository(self.db)
        self.config = AppConfig(self.temp_cfg)
        self.app_state = AppState(self.config)
        self.manager = MemoryManager(self.app_state, self.repo)

    def tearDown(self):
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)
        if os.path.exists(self.temp_cfg):
            os.remove(self.temp_cfg)

    def test_memory_editor_modal_init(self):
        modal = MemoryEditorModal()
        self.assertFalse(modal.is_edit)
        self.assertEqual(modal.windowTitle(), "Add New Memory")
        self.assertEqual(modal.text_edit.toPlainText(), "")

        # Edit mode
        sample_mem = {"id": 1, "content": "Existing memory", "category": "work", "is_enabled": 1}
        edit_modal = MemoryEditorModal(memory=sample_mem)
        self.assertTrue(edit_modal.is_edit)
        self.assertEqual(edit_modal.windowTitle(), "Edit Memory")
        self.assertEqual(edit_modal.text_edit.toPlainText(), "Existing memory")
        self.assertEqual(edit_modal.cat_combo.currentData(), "work")

    def test_memory_card_widget(self):
        mem = {
            "id": 10,
            "content": "Prefers dark mode",
            "category": "preference",
            "is_enabled": 1,
            "created_at": "2026-09-13 14:00:00",
            "embedding": [0.1, 0.2]
        }
        card = MemoryCardWidget(mem)
        self.assertIn("Preference", card.cat_badge.text())
        self.assertEqual(card.toggle_btn.text(), "✓ Active")
        self.assertEqual(card.content_lbl.text(), "Prefers dark mode")
        self.assertEqual(card.embed_dot.text(), "● Vector Indexed")

    def test_memory_dialog_loading_and_filtering(self):
        self.manager.create_memory("Prefers PySide6", category="preference")
        self.manager.create_memory("Backend engineer at TechCorp", category="work")

        dialog = MemoryDialog(self.manager)
        self.assertEqual(dialog.content_stack.currentIndex(), 0)  # List state
        self.assertEqual(dialog.list_widget.count(), 2)

        # Search filter
        dialog._on_search_changed("PySide6")
        self.assertEqual(dialog.list_widget.count(), 1)

        # Clear search
        dialog._on_search_changed("")
        self.assertEqual(dialog.list_widget.count(), 2)

        # Category filter chip
        dialog._on_chip_clicked("work")
        self.assertEqual(dialog.list_widget.count(), 1)


class TestMemorySelectorAndSidebarControls(unittest.TestCase):
    def setUp(self):
        self.temp_cfg = tempfile.mktemp(suffix=".json")
        self.temp_db = tempfile.mktemp(suffix=".db")
        self.db = DatabaseManager(self.temp_db)
        self.config = AppConfig(self.temp_cfg)
        self.app_state = AppState(self.config)
        self.repo = MemoryRepository(self.db)
        self.manager = MemoryManager(self.app_state, self.repo)

    def tearDown(self):
        if os.path.exists(self.temp_cfg):
            os.remove(self.temp_cfg)
        if os.path.exists(self.temp_db):
            os.remove(self.temp_db)

    def test_memory_selector_appearance_and_toggling(self):
        from ui.memory_selector import MemorySelector
        selector = MemorySelector(self.manager)
        
        # Initial state (On)
        self.assertEqual(selector.pill_btn.text(), "🧠 Memory: On ▾")
        self.assertEqual(selector.pill_btn.property("active"), "true")
        
        # Toggle to Off
        selector.set_enabled_state(False)
        self.assertEqual(selector.pill_btn.text(), "🧠 Memory: Off ▾")
        self.assertEqual(selector.pill_btn.property("active"), "false")
        
        # Toggle back to On
        selector.set_enabled_state(True)
        self.assertEqual(selector.pill_btn.text(), "🧠 Memory: On ▾")
        self.assertEqual(selector.pill_btn.property("active"), "true")

    def test_sidebar_feature_row_toggle(self):
        from ui.sidebar import SidebarFeatureRow
        toggled = []
        managed = []
        row = SidebarFeatureRow(
            icon="🧠",
            title="Memory",
            on_toggle=lambda: toggled.append(True),
            on_manage=lambda: managed.append(True),
            initial_active=True
        )
        self.assertEqual(row.toggle_btn.text(), "ON")
        self.assertEqual(row.toggle_btn.property("active"), "true")
        
        # Toggle to False
        row.set_active(False)
        self.assertEqual(row.toggle_btn.text(), "OFF")
        self.assertEqual(row.toggle_btn.property("active"), "false")
        
        # Test toggle button click
        row.toggle_btn.click()
        self.assertEqual(len(toggled), 1)
        
        # Test collapsed mode
        row.set_collapsed(True)
        self.assertEqual(row.text(), "🧠")
        self.assertTrue(row.title_lbl.isHidden())
        self.assertTrue(row.toggle_btn.isHidden())
        
        row.set_collapsed(False)
        self.assertIn("Memory", row.text())
        self.assertFalse(row.title_lbl.isHidden())
        self.assertFalse(row.toggle_btn.isHidden())


if __name__ == "__main__":
    unittest.main()
