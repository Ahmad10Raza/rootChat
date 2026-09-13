import os
import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from core.app_config import AppConfig
from core.app_state import AppState
from core.chat_manager import ChatManager
from core.context_manager import ContextManager
from core.memory_manager import MemoryManager
from database.database import DatabaseManager
from database.repositories.conversation_repository import ConversationRepository
from database.repositories.document_repository import DocumentRepository
from database.repositories.memory_repository import MemoryRepository
from database.repositories.message_repository import MessageRepository
from retrieval.local_vector_store import LocalVectorStore
from retrieval.retriever import Retriever
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"
_qapp = QApplication.instance() or QApplication([])


class TestKnowledgePerChat(unittest.TestCase):
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

        self.conv_repo = ConversationRepository(self.db_manager)
        self.doc_repo = DocumentRepository(self.db_manager)
        self.msg_repo = MessageRepository(self.db_manager)
        self.mem_repo = MemoryRepository(self.db_manager)
        self.memory_manager = MemoryManager(self.app_state, self.mem_repo)

        self.retriever_mock = MagicMock()
        self.context_manager = ContextManager(
            self.app_state, self.memory_manager, self.msg_repo, retriever=self.retriever_mock
        )
        self.chat_manager = ChatManager(
            self.app_state, self.client_mock, self.db_manager, self.memory_manager, self.context_manager
        )

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    # 1. Repository CRUD Tests
    def test_conversation_repository_knowledge_fields(self):
        # Create with default 'none'
        conv1_id = self.conv_repo.create_conversation("Chat 1", "test_model")
        conv1 = self.conv_repo.get_conversation(conv1_id)
        self.assertEqual(conv1["knowledge_mode"], "none")
        self.assertEqual(conv1["knowledge_doc_ids"], "[]")

        # Create with 'specific' and doc ids
        conv2_id = self.conv_repo.create_conversation(
            "Chat 2", "test_model", knowledge_mode="specific", knowledge_doc_ids="[10, 20]"
        )
        conv2 = self.conv_repo.get_conversation(conv2_id)
        self.assertEqual(conv2["knowledge_mode"], "specific")
        self.assertEqual(conv2["knowledge_doc_ids"], "[10, 20]")

        # Update conversation knowledge settings
        self.conv_repo.update_conversation(conv1_id, knowledge_mode="all", knowledge_doc_ids="[]")
        updated_conv1 = self.conv_repo.get_conversation(conv1_id)
        self.assertEqual(updated_conv1["knowledge_mode"], "all")
        self.assertEqual(updated_conv1["knowledge_doc_ids"], "[]")

    # 2. Document Repository Scoped Chunks Query
    def test_get_chunks_for_documents(self):
        doc1_id = self.doc_repo.create_document("doc1.txt", "/tmp/doc1.txt", ".txt", 100, "hash1")
        doc2_id = self.doc_repo.create_document("doc2.txt", "/tmp/doc2.txt", ".txt", 200, "hash2")

        chunks_doc1 = [
            {"chunk_index": 0, "content": "Doc 1 Chunk 0", "embedding": [1.0, 0.0], "page_number": 1},
            {"chunk_index": 1, "content": "Doc 1 Chunk 1", "embedding": [0.8, 0.2], "page_number": 1},
        ]
        chunks_doc2 = [
            {"chunk_index": 0, "content": "Doc 2 Chunk 0", "embedding": [0.0, 1.0], "page_number": 1},
        ]

        self.doc_repo.save_chunks(doc1_id, chunks_doc1)
        self.doc_repo.save_chunks(doc2_id, chunks_doc2)

        # Retrieve only doc1
        res1 = self.doc_repo.get_chunks_for_documents([doc1_id])
        self.assertEqual(len(res1), 2)
        for c in res1:
            self.assertEqual(c["document_id"], doc1_id)
            self.assertEqual(c["filename"], "doc1.txt")

        # Retrieve only doc2
        res2 = self.doc_repo.get_chunks_for_documents([doc2_id])
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0]["document_id"], doc2_id)

        # Retrieve both
        res_both = self.doc_repo.get_chunks_for_documents([doc1_id, doc2_id])
        self.assertEqual(len(res_both), 3)

        # Retrieve with empty list
        res_empty = self.doc_repo.get_chunks_for_documents([])
        self.assertEqual(res_empty, [])

    # 3. LocalVectorStore Scoped Filtering
    def test_local_vector_store_filtering(self):
        vector_store = LocalVectorStore(self.doc_repo)
        doc1_id = self.doc_repo.create_document("taxes.pdf", "/tmp/taxes.pdf", ".pdf", 100, "h1")
        doc2_id = self.doc_repo.create_document("linux.txt", "/tmp/linux.txt", ".txt", 100, "h2")

        self.doc_repo.save_chunks(doc1_id, [{"chunk_index": 0, "content": "Tax chunk", "embedding": [1.0, 0.0]}])
        self.doc_repo.save_chunks(doc2_id, [{"chunk_index": 0, "content": "Linux chunk", "embedding": [1.0, 0.0]}])

        # Search with doc_ids=[doc1_id] -> only tax chunk
        res_scoped = vector_store.search(query_embedding=[1.0, 0.0], doc_ids=[doc1_id])
        self.assertEqual(len(res_scoped), 1)
        self.assertEqual(res_scoped[0]["document_id"], doc1_id)
        self.assertEqual(res_scoped[0]["content"], "Tax chunk")

        # Search with doc_ids=[] -> returns [] immediately
        res_empty = vector_store.search(query_embedding=[1.0, 0.0], doc_ids=[])
        self.assertEqual(res_empty, [])

        # Search with doc_ids=None -> returns all
        res_all = vector_store.search(query_embedding=[1.0, 0.0], doc_ids=None)
        self.assertEqual(len(res_all), 2)

    # 4. ContextManager Scoping Behavior
    def test_context_manager_scoping(self):
        conv_id = self.conv_repo.create_conversation("RAG Test", "test_model")
        self.msg_repo.create_message(conv_id, "user", "What is my tax rate?")
        self.msg_repo.create_message(conv_id, "assistant", "")  # placeholder

        # Mode: 'none' -> retriever must NOT be called
        self.app_state.set("active_knowledge_mode", "none")
        self.app_state.set("active_knowledge_doc_ids", [])
        self.context_manager.build_context(conv_id, "What is my tax rate?")
        self.retriever_mock.retrieve.assert_not_called()
        self.assertEqual(self.app_state.get("last_sources_used"), 0)

        # Mode: 'all' -> retriever called with doc_ids=None
        self.retriever_mock.reset_mock()
        self.retriever_mock.retrieve.return_value = [
            {"filename": "all_doc.txt", "page_number": 1, "content": "Tax is 20%"}
        ]
        self.app_state.set("active_knowledge_mode", "all")
        ctx = self.context_manager.build_context(conv_id, "What is my tax rate?")
        self.retriever_mock.retrieve.assert_called_once()
        _, kwargs = self.retriever_mock.retrieve.call_args
        self.assertIsNone(kwargs["doc_ids"])
        self.assertEqual(self.app_state.get("last_sources_used"), 1)
        self.assertIn("DOCUMENT CONTEXT", ctx[0]["content"])
        self.assertIn("Tax is 20%", ctx[0]["content"])

        # Mode: 'specific' -> retriever called with specific doc_ids
        self.retriever_mock.reset_mock()
        self.retriever_mock.retrieve.return_value = [
            {"filename": "scoped_tax.txt", "page_number": 2, "content": "Scoped tax is 15%"}
        ]
        self.app_state.set("active_knowledge_mode", "specific")
        self.app_state.set("active_knowledge_doc_ids", [42, 99])
        ctx = self.context_manager.build_context(conv_id, "What is my tax rate?")
        self.retriever_mock.retrieve.assert_called_once()
        _, kwargs = self.retriever_mock.retrieve.call_args
        self.assertEqual(kwargs["doc_ids"], [42, 99])
        self.assertEqual(self.app_state.get("last_sources_used"), 1)
        self.assertIn("Scoped tax is 15%", ctx[0]["content"])

    # 5. ChatManager State & Signals
    def test_chat_manager_knowledge_signals_and_switching(self):
        emitted_modes = []

        def on_knowledge_changed(mode, doc_ids):
            emitted_modes.append((mode, doc_ids))

        self.chat_manager.knowledge_mode_changed.connect(on_knowledge_changed)

        # Start new conversation -> resets to default ('none')
        self.chat_manager.start_new_conversation()
        self.assertEqual(emitted_modes[-1], ("none", []))
        self.assertEqual(self.app_state.get("active_knowledge_mode"), "none")

        # Create Chat A with specific knowledge
        conv_a_id = self.conv_repo.create_conversation(
            "Chat A", "test_model", knowledge_mode="specific", knowledge_doc_ids="[1, 5]"
        )

        # Create Chat B with no knowledge
        conv_b_id = self.conv_repo.create_conversation(
            "Chat B", "test_model", knowledge_mode="none", knowledge_doc_ids="[]"
        )

        # Load Chat A -> switches state and emits
        self.chat_manager.load_conversation(conv_a_id)
        self.assertEqual(self.app_state.get("active_knowledge_mode"), "specific")
        self.assertEqual(self.app_state.get("active_knowledge_doc_ids"), [1, 5])
        self.assertEqual(emitted_modes[-1], ("specific", [1, 5]))

        # Load Chat B -> switches back to none
        self.chat_manager.load_conversation(conv_b_id)
        self.assertEqual(self.app_state.get("active_knowledge_mode"), "none")
        self.assertEqual(self.app_state.get("active_knowledge_doc_ids"), [])
        self.assertEqual(emitted_modes[-1], ("none", []))

        # Dynamically set knowledge on Chat B
        self.chat_manager.set_conversation_knowledge(conv_b_id, "all", [])
        self.assertEqual(self.app_state.get("active_knowledge_mode"), "all")
        conv_b_db = self.conv_repo.get_conversation(conv_b_id)
        self.assertEqual(conv_b_db["knowledge_mode"], "all")
        self.assertEqual(emitted_modes[-1], ("all", []))

    # 6. UI Pill & Selector Tests
    def test_message_input_pill_behavior(self):
        from ui.message_input import MessageInput
        widget = MessageInput(self.app_state)
        widget.show()

        # Initially hidden
        self.assertTrue(widget.pill_container.isHidden())

        # Set to 'all'
        widget.set_knowledge_context("all", [])
        self.assertFalse(widget.pill_container.isHidden())
        self.assertIn("All Documents", widget.pill_btn.text())

        # Set to 'specific' with 2 docs
        widget.set_knowledge_context("specific", [1, 2])
        self.assertFalse(widget.pill_container.isHidden())
        self.assertIn("2 Documents", widget.pill_btn.text())

        # Set to 'none'
        widget.set_knowledge_context("none", [])
        self.assertTrue(widget.pill_container.isHidden())

        # Test signals
        cleared = []
        scoped = []
        widget.knowledge_clear_requested.connect(lambda: cleared.append(True))
        widget.knowledge_scope_requested.connect(lambda: scoped.append(True))

        widget.pill_clear_btn.click()
        self.assertEqual(len(cleared), 1)

        widget.pill_btn.click()
        self.assertEqual(len(scoped), 1)

    def test_knowledge_selector_pill(self):
        from ui.knowledge_selector import KnowledgeSelector
        selector = KnowledgeSelector()

        selector.set_knowledge("none", [])
        self.assertIn("Off", selector.pill_btn.text())

        selector.set_knowledge("all", [])
        self.assertIn("All", selector.pill_btn.text())

        selector.set_knowledge("specific", [10, 20, 30])
        self.assertIn("3 Files", selector.pill_btn.text())

    def test_knowledge_scope_dialog_tiles(self):
        from ui.knowledge_selector import KnowledgeScopeDialog
        doc_mgr = MagicMock()
        doc_mgr.repo.list_documents.return_value = [
            {"id": 1, "filename": "test.pdf", "status": "Indexed", "real_chunk_count": 5},
            {"id": 2, "filename": "notes.txt", "status": "Indexed", "real_chunk_count": 3},
        ]
        
        dlg = KnowledgeScopeDialog(doc_manager=doc_mgr, current_mode="none")
        self.assertTrue(dlg.tile_none.is_selected)
        self.assertFalse(dlg.tile_all.is_selected)
        self.assertFalse(dlg.tile_specific.is_selected)
        self.assertTrue(dlg.specific_container.isHidden())

        # Select specific mode
        dlg.tile_specific.clicked.emit("specific")
        self.assertFalse(dlg.tile_none.is_selected)
        self.assertTrue(dlg.tile_specific.is_selected)
        self.assertFalse(dlg.specific_container.isHidden())

        # Select All items
        dlg._select_all()
        self.assertIn("2 of 2", dlg.sel_count_lbl.text())

        # Clear items
        dlg._clear_all()
        self.assertIn("0 of 2", dlg.sel_count_lbl.text())

    def test_knowledge_dialog_and_cards(self):
        from ui.knowledge_panel import KnowledgeDialog, DocumentCardWidget
        doc_mgr = MagicMock()
        doc_mgr.app_state.get.return_value = True
        doc_mgr.repo.list_documents.return_value = [
            {"id": 1, "filename": "report.pdf", "file_size": 204800, "status": "Indexed", "real_chunk_count": 10},
        ]
        doc_mgr.document_added = MagicMock()
        doc_mgr.indexing_progress = MagicMock()
        doc_mgr.indexing_finished = MagicMock()

        dlg = KnowledgeDialog(doc_manager=doc_mgr)
        self.assertEqual(dlg.list_widget.count(), 1)
        self.assertIn("1 Document", dlg.stats_badge.text())
        self.assertIn("10 Chunks", dlg.stats_badge.text())

    def test_pdf_loader_ocr_fallback(self):
        from documents.loaders.pdf_loader import PDFLoader
        loader = PDFLoader()
        self.assertTrue(loader.can_load("test.pdf"))
        self.assertFalse(loader.can_load("test.txt"))

        # Test on Offer_Letter.pdf if present on machine
        offer_path = "/home/ahmad10raza/Downloads/Resume/Offer_Letter.pdf"
        if os.path.exists(offer_path):
            progress_calls = []
            pages = loader.load(offer_path, progress_callback=lambda msg, pct: progress_calls.append((msg, pct)))
            self.assertEqual(len(pages), 9)
            # Verify OCR extracted text
            self.assertTrue(any("AHMAD RAZA" in p["content"] for p in pages))
            self.assertTrue(len(progress_calls) > 0)


if __name__ == "__main__":
    unittest.main()

