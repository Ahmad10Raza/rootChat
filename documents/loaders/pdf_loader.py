import os
from .base_loader import BaseLoader
from utils.logger import logger

class PDFLoader(BaseLoader):
    def can_load(self, file_path: str) -> bool:
        return os.path.splitext(file_path)[1].lower() == '.pdf'
        
    def load(self, file_path: str, progress_callback=None) -> list:
        try:
            import fitz
        except ImportError:
            logger.warning("PyMuPDF (fitz) is not installed. PDF loading is disabled.")
            return [{"page_number": 1, "content": "Error: PyMuPDF is not installed."}]
            
        pages = []
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            
            for i, page in enumerate(doc):
                text = page.get_text()
                
                # If page has no extractable text or very sparse characters, check if it's a scanned/image page
                if not text.strip() or len(text.strip()) < 15:
                    images = page.get_images()
                    if images or not text.strip():
                        if progress_callback:
                            pct = 10 + int(20 * ((i + 1) / max(total_pages, 1)))
                            progress_callback(f"Scanning page {i+1}/{total_pages} (OCR)...", pct)
                        try:
                            ocr_tp = page.get_textpage_ocr(language="eng", dpi=150)
                            ocr_text = page.get_text(textpage=ocr_tp)
                            if ocr_text.strip():
                                text = ocr_text
                        except Exception as ocr_err:
                            logger.warning(
                                "OCR fallback skipped or failed on page %d of %s: %s",
                                i + 1, file_path, ocr_err
                            )
                elif progress_callback:
                    pct = 10 + int(20 * ((i + 1) / max(total_pages, 1)))
                    progress_callback(f"Reading page {i+1}/{total_pages}...", pct)
                    
                pages.append({
                    "page_number": i + 1,
                    "content": text
                })
            return pages
        except Exception as e:
            logger.error(f"Failed to read PDF {file_path}: {e}")
            return [{"page_number": 1, "content": f"Error reading PDF: {e}"}]

