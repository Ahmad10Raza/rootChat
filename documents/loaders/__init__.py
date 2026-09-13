from .base_loader import BaseLoader
from .text_loader import TextLoader
from .pdf_loader import PDFLoader
from .docx_loader import DocxLoader

class DocumentParser:
    def __init__(self):
        self.loaders = [
            PDFLoader(),
            DocxLoader(),
            TextLoader() # Catch-all for text-like files
        ]
        
    def parse(self, file_path: str, progress_callback=None) -> list:
        for loader in self.loaders:
            if loader.can_load(file_path):
                try:
                    return loader.load(file_path, progress_callback=progress_callback)
                except TypeError:
                    return loader.load(file_path)
        raise ValueError(f"No suitable loader found for file: {file_path}")

