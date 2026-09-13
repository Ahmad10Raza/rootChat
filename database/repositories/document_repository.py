import json
from database.database import DatabaseManager
from utils.logger import logger

class DocumentRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create_document(self, filename: str, file_path: str, file_type: str, file_size: int, file_hash: str) -> int:
        query = """
            INSERT INTO documents (filename, file_path, file_type, file_size, file_hash, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
        """
        doc_id = self.db.execute_query(query, (filename, file_path, file_type, file_size, file_hash), commit=True)
        logger.debug("Created document record %d for %s", doc_id, filename)
        return doc_id

    def get_document(self, doc_id: int):
        query = """
            SELECT d.*, 
                   COALESCE(c.real_chunk_count, 0) as real_chunk_count
            FROM documents d
            LEFT JOIN (
                SELECT document_id, COUNT(*) as real_chunk_count 
                FROM document_chunks 
                GROUP BY document_id
            ) c ON d.id = c.document_id
            WHERE d.id = ?
        """
        res = self.db.execute_query(query, (doc_id,))
        return dict(res[0]) if res else None

    def get_document_by_hash(self, file_hash: str):
        query = """
            SELECT d.*, 
                   COALESCE(c.real_chunk_count, 0) as real_chunk_count
            FROM documents d
            LEFT JOIN (
                SELECT document_id, COUNT(*) as real_chunk_count 
                FROM document_chunks 
                GROUP BY document_id
            ) c ON d.id = c.document_id
            WHERE d.file_hash = ?
        """
        res = self.db.execute_query(query, (file_hash,))
        return dict(res[0]) if res else None

    def list_documents(self):
        query = """
            SELECT d.*, 
                   COALESCE(c.real_chunk_count, 0) as real_chunk_count
            FROM documents d
            LEFT JOIN (
                SELECT document_id, COUNT(*) as real_chunk_count 
                FROM document_chunks 
                GROUP BY document_id
            ) c ON d.id = c.document_id
            ORDER BY d.created_at DESC
        """
        return [dict(row) for row in self.db.execute_query(query)]

    def update_document_status(self, doc_id: int, status: str, chunk_count: int = None):
        if chunk_count is not None:
            query = "UPDATE documents SET status = ?, chunk_count = ?, indexed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            self.db.execute_query(query, (status, chunk_count, doc_id), commit=True)
        else:
            query = "UPDATE documents SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            self.db.execute_query(query, (status, doc_id), commit=True)

    def delete_document(self, doc_id: int):
        # ON DELETE CASCADE handles chunks
        query = "DELETE FROM documents WHERE id = ?"
        self.db.execute_query(query, (doc_id,), commit=True)
        logger.info("Deleted document %d", doc_id)

    def save_chunks(self, document_id: int, chunks: list):
        """
        Chunks format: [{"chunk_index": i, "content": text, "page_number": p, "embedding": list_of_floats}]
        """
        insert_query = """
            INSERT INTO document_chunks (document_id, chunk_index, content, page_number, embedding)
            VALUES (?, ?, ?, ?, ?)
        """
        operations = [
            ("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
        ]
        for chunk in chunks:
            # We serialize the embedding list to JSON string, then encode to utf-8 BLOB
            emb_blob = json.dumps(chunk["embedding"]).encode('utf-8') if chunk.get("embedding") else None
            operations.append((insert_query, (
                document_id,
                chunk["chunk_index"],
                chunk["content"],
                chunk.get("page_number", 1),
                emb_blob
            )))
            
        self.db.execute_transaction(operations)
        logger.info("Saved %d chunks for document %d", len(chunks), document_id)

    def get_all_chunks(self):
        """
        Fetches all chunks for vector search.
        In a real production app with 1M chunks, we would batch this.
        For a local app with a few thousand chunks, it easily fits in memory.
        """
        query = """
            SELECT dc.*, d.filename 
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.embedding IS NOT NULL
        """
        rows = self.db.execute_query(query)
        chunks = []
        for row in rows:
            c = dict(row)
            # Deserialize embedding
            c["embedding"] = json.loads(c["embedding"].decode('utf-8'))
            chunks.append(c)
        return chunks

    def get_chunks_for_documents(self, doc_ids: list[int]):
        """
        Fetches chunks only for the specified document IDs.
        """
        if not doc_ids:
            return []
        placeholders = ",".join("?" * len(doc_ids))
        query = f"""
            SELECT dc.*, d.filename 
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.embedding IS NOT NULL AND dc.document_id IN ({placeholders})
        """
        rows = self.db.execute_query(query, tuple(doc_ids))
        chunks = []
        for row in rows:
            c = dict(row)
            c["embedding"] = json.loads(c["embedding"].decode('utf-8'))
            chunks.append(c)
        return chunks
