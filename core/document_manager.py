import os
from PySide6.QtCore import QObject, Signal
from database.repositories.document_repository import DocumentRepository
from documents.loaders import DocumentParser
from documents.chunking.text_chunker import TextChunker
from documents.embeddings.embedding_provider import EmbeddingProvider
from workers.document_worker import DocumentIndexingWorker, get_file_hash
from core.app_state import AppState
from utils.logger import logger

class DocumentManager(QObject):
    document_added = Signal(int)
    indexing_progress = Signal(int, str, int)  # doc_id, msg, pct
    indexing_finished = Signal(int, bool, str)  # doc_id, success, msg
    
    def __init__(self, app_state: AppState, repo: DocumentRepository, embedding_provider: EmbeddingProvider):
        super().__init__()
        self.app_state = app_state
        self.repo = repo
        self.embedding_provider = embedding_provider
        self.parser = DocumentParser()
        self.chunker = TextChunker(
            chunk_size=int(self.app_state.get("chunk_size", 1000)),
            chunk_overlap=int(self.app_state.get("chunk_overlap", 150))
        )
        self.active_workers = {}

    def add_document(self, file_path: str):
        if not os.path.exists(file_path):
            return None, "File does not exist."
            
        file_hash = get_file_hash(file_path)
        existing = self.repo.get_document_by_hash(file_hash)
        if existing:
            # If document exists but has 0 chunks or failed, auto re-index
            real_chunks = existing.get("real_chunk_count", 0)
            if real_chunks == 0 or existing.get("status") != "Indexed":
                logger.info("Document %d exists but has %d chunks (status=%s). Re-indexing...", existing["id"], real_chunks, existing.get("status"))
                query = "UPDATE documents SET file_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                self.repo.db.execute_query(query, (file_path, existing["id"]), commit=True)
                self.reindex_document(existing["id"], file_path)
                return existing["id"], "Re-indexing started."
            return existing["id"], "Document already exists."
            
        filename = os.path.basename(file_path)
        file_type = os.path.splitext(filename)[1].lower()
        file_size = os.path.getsize(file_path)
        
        doc_id = self.repo.create_document(filename, file_path, file_type, file_size, file_hash)
        self.document_added.emit(doc_id)
        
        self.reindex_document(doc_id, file_path)
        return doc_id, "Indexing started."
        
    def reindex_document(self, doc_id: int, file_path: str):
        self.repo.update_document_status(doc_id, "Indexing")
        
        worker = DocumentIndexingWorker(
            file_path, doc_id, self.parser, self.chunker, self.embedding_provider, self.repo
        )
        worker.progress.connect(lambda msg, pct, d=doc_id: self.indexing_progress.emit(d, msg, pct))
        worker.finished.connect(self._on_indexing_finished)
        self.active_workers[doc_id] = worker
        worker.start()
        
    def _on_indexing_finished(self, doc_id: int, success: bool, msg: str):
        if doc_id in self.active_workers:
            del self.active_workers[doc_id]
        self.indexing_finished.emit(doc_id, success, msg)
        
    def delete_document(self, doc_id: int):
        self.repo.delete_document(doc_id)
