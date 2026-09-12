import math
from .vector_store import VectorStore
from database.repositories.document_repository import DocumentRepository

def cosine_similarity(v1: list, v2: list) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)

class LocalVectorStore(VectorStore):
    """A lightweight, zero-dependency local vector store built on SQLite and pure Python math."""
    
    def __init__(self, doc_repo: DocumentRepository):
        self.doc_repo = doc_repo

    def search(self, query_embedding: list, top_k: int = 5, similarity_threshold: float = 0.5) -> list:
        chunks = self.doc_repo.get_all_chunks()
        results = []
        
        for chunk in chunks:
            sim = cosine_similarity(query_embedding, chunk["embedding"])
            if sim >= similarity_threshold:
                chunk["similarity"] = sim
                results.append(chunk)
                
        # Sort by highest similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
