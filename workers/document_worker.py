import os
import hashlib
from PySide6.QtCore import QThread, Signal
from documents.loaders import DocumentParser
from documents.chunking.text_chunker import TextChunker
from documents.embeddings.embedding_provider import EmbeddingProvider
from database.repositories.document_repository import DocumentRepository
from utils.logger import logger

def get_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

class DocumentIndexingWorker(QThread):
    progress = Signal(str, int)  # status_message, percentage
    finished = Signal(int, bool, str)  # doc_id, success, message
    
    def __init__(self, file_path: str, doc_id: int, 
                 parser: DocumentParser, chunker: TextChunker, 
                 embedding_provider: EmbeddingProvider, repo: DocumentRepository):
        super().__init__()
        self.file_path = file_path
        self.doc_id = doc_id
        self.parser = parser
        self.chunker = chunker
        self.embedding_provider = embedding_provider
        self.repo = repo
        
    def run(self):
        try:
            self.progress.emit("Extracting text...", 10)
            
            # 1. Parse
            pages = self.parser.parse(self.file_path)
            if not pages or all(not p.get("content", "").strip() for p in pages):
                self.repo.update_document_status(self.doc_id, "Failed")
                self.finished.emit(self.doc_id, False, "No readable text found.")
                return
                
            self.progress.emit("Chunking text...", 30)
            
            # 2. Chunk
            chunks = self.chunker.chunk_document(pages)
            if not chunks:
                self.repo.update_document_status(self.doc_id, "Failed")
                self.finished.emit(self.doc_id, False, "Failed to create chunks.")
                return
                
            # 3. Embed
            total = len(chunks)
            for i, chunk in enumerate(chunks):
                pct = 30 + int(60 * (i / total))
                self.progress.emit(f"Embedding chunk {i+1}/{total}...", pct)
                chunk["embedding"] = self.embedding_provider.embed_text(chunk["content"])
                
            self.progress.emit("Saving to database...", 95)
            
            # 4. Save
            self.repo.save_chunks(self.doc_id, chunks)
            self.repo.update_document_status(self.doc_id, "Indexed", len(chunks))
            
            self.progress.emit("Complete!", 100)
            self.finished.emit(self.doc_id, True, "Successfully indexed.")
            
        except Exception as e:
            logger.error("Document indexing failed: %s", e)
            self.repo.update_document_status(self.doc_id, "Failed")
            self.finished.emit(self.doc_id, False, str(e))
