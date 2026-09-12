import os
from .base_loader import BaseLoader
from utils.logger import logger

class DocxLoader(BaseLoader):
    def can_load(self, file_path: str) -> bool:
        return os.path.splitext(file_path)[1].lower() == '.docx'
        
    def load(self, file_path: str) -> list:
        try:
            import docx
        except ImportError:
            logger.warning("python-docx is not installed. DOCX loading is disabled.")
            return [{"page_number": 1, "content": "Error: python-docx is not installed."}]
            
        try:
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            return [{"page_number": 1, "content": text}]
        except Exception as e:
            logger.error(f"Failed to read DOCX {file_path}: {e}")
            return [{"page_number": 1, "content": f"Error reading DOCX: {e}"}]
