from .embedding_provider import EmbeddingProvider
from core.ollama_client import OllamaClient
from utils.logger import logger

class OllamaEmbeddings(EmbeddingProvider):
    def __init__(self, client: OllamaClient, model_name: str = "nomic-embed-text"):
        self.client = client
        self.model_name = model_name

    def embed_text(self, text: str) -> list:
        return self.client.generate_embeddings(self.model_name, text)

    def embed_query(self, text: str) -> list:
        return self.embed_text(text)
        
    def embed_documents(self, chunks: list) -> list:
        for chunk in chunks:
            try:
                emb = self.embed_text(chunk["content"])
                chunk["embedding"] = emb
            except Exception as e:
                logger.error(f"Failed to embed chunk {chunk['chunk_index']}: {e}")
                chunk["embedding"] = None
        return chunks
