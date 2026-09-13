from documents.embeddings.embedding_provider import EmbeddingProvider
from .vector_store import VectorStore
from utils.logger import logger

class Retriever:
    def __init__(self, embedding_provider: EmbeddingProvider, vector_store: VectorStore):
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        
    def retrieve(self, query: str, top_k: int = 5, similarity_threshold: float = 0.5, doc_ids: list[int] = None) -> list:
        try:
            query_embedding = self.embedding_provider.embed_text(query)
            if not query_embedding:
                logger.warning("Empty embedding returned for query.")
                return []
                
            results = self.vector_store.search(query_embedding, top_k=top_k, similarity_threshold=similarity_threshold, doc_ids=doc_ids)
            return results
        except Exception as e:
            logger.error("Retrieval failed: %s", e)
            return []
