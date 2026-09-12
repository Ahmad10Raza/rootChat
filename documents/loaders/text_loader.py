import os
from .base_loader import BaseLoader

class TextLoader(BaseLoader):
    def can_load(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in ['.txt', '.md', '.csv', '.json', '.log']
        
    def load(self, file_path: str) -> list:
        content = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='iso-8859-1') as f:
                content = f.read()
        return [{"page_number": 1, "content": content}]
