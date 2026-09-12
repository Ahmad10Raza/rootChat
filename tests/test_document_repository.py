import os
import tempfile
import unittest
from database.database import DatabaseManager
from database.repositories.document_repository import DocumentRepository

class TestDocumentRepository(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_docs.db")
        self.db = DatabaseManager(db_path=self.db_path)
        self.repo = DocumentRepository(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_retrieve_chunks(self):
        doc_id = self.repo.create_document("sample.txt", "/path/sample.txt", ".txt", 1024, "hash_abc_123")
        self.assertIsNotNone(doc_id)

        chunks_data = [
            {"chunk_index": 0, "content": "First chunk content", "page_number": 1, "embedding": [0.1, 0.2, 0.3]},
            {"chunk_index": 1, "content": "Second chunk content", "page_number": 1, "embedding": [0.4, 0.5, 0.6]},
        ]

        self.repo.save_chunks(doc_id, chunks_data)
        self.repo.update_document_status(doc_id, "Indexed", len(chunks_data))

        all_chunks = self.repo.get_all_chunks()
        self.assertEqual(len(all_chunks), 2)
        self.assertEqual(all_chunks[0]["content"], "First chunk content")
        self.assertEqual(all_chunks[0]["embedding"], [0.1, 0.2, 0.3])
        self.assertEqual(all_chunks[0]["filename"], "sample.txt")

        # Overwrite chunks (re-indexing)
        new_chunks = [
            {"chunk_index": 0, "content": "Updated chunk", "page_number": 1, "embedding": [0.9, 0.8, 0.7]}
        ]
        self.repo.save_chunks(doc_id, new_chunks)
        all_chunks = self.repo.get_all_chunks()
        self.assertEqual(len(all_chunks), 1)
        self.assertEqual(all_chunks[0]["content"], "Updated chunk")

    def test_delete_document_cascades_chunks(self):
        doc_id = self.repo.create_document("delete_me.pdf", "/path/delete_me.pdf", ".pdf", 2048, "hash_del_456")
        chunks_data = [
            {"chunk_index": 0, "content": "Chunk to delete", "page_number": 1, "embedding": [0.1, 0.2]}
        ]
        self.repo.save_chunks(doc_id, chunks_data)
        self.assertEqual(len(self.repo.get_all_chunks()), 1)

        self.repo.delete_document(doc_id)
        self.assertEqual(len(self.repo.get_all_chunks()), 0)
        self.assertIsNone(self.repo.get_document(doc_id))

if __name__ == "__main__":
    unittest.main()
