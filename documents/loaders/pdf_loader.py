import os
from .base_loader import BaseLoader
from utils.logger import logger

class PDFLoader(BaseLoader):
    def can_load(self, file_path: str) -> bool:
        return os.path.splitext(file_path)[1].lower() == '.pdf'
        
    def load(self, file_path: str) -> list:
        try:
            import fitz
        except ImportError:
            logger.warning("PyMuPDF (fitz) is not installed. PDF loading is disabled.")
            return [{"page_number": 1, "content": "Error: PyMuPDF is not installed."}]
            
        pages = []
        try:
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                pages.append({
                    "page_number": i + 1,
                    "content": page.get_text()
                })
            return pages
        except Exception as e:
            logger.error(f"Failed to read PDF {file_path}: {e}")
            return [{"page_number": 1, "content": f"Error reading PDF: {e}"}]
