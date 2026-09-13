from abc import ABC, abstractmethod

class BaseLoader(ABC):
    @abstractmethod
    def can_load(self, file_path: str) -> bool:
        pass
        
    @abstractmethod
    def load(self, file_path: str, progress_callback=None) -> list:
        """Returns a list of dicts: [{'page_number': 1, 'content': '...'}, ...]"""
        pass

