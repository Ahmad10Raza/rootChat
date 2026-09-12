from abc import ABC, abstractmethod

class BaseLoader(ABC):
    @abstractmethod
    def can_load(self, file_path: str) -> bool:
        pass
        
    @abstractmethod
    def load(self, file_path: str) -> list:
        """Returns a list of dicts: [{'page_number': 1, 'content': '...'}, ...]"""
        pass
