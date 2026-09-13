from abc import ABC, abstractmethod

class VectorStore(ABC):
    @abstractmethod
    def search(self, query_embedding: list, top_k: int = 5, similarity_threshold: float = 0.5, doc_ids: list[int] = None) -> list:
        pass

