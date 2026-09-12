from abc import ABC, abstractmethod

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list:
        pass
        
    @abstractmethod
    def embed_documents(self, chunks: list) -> list:
        pass
