class TextChunker:
    def __init__(self, chunk_size=1000, chunk_overlap=150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, pages: list) -> list:
        """
        Receives a list of dicts: [{'page_number': int, 'content': str}]
        Returns a list of chunks: [{'chunk_index': int, 'page_number': int, 'content': str}]
        """
        chunks = []
        chunk_idx = 0
        
        for page in pages:
            text = page["content"].strip()
            if not text:
                continue
                
            start = 0
            while start < len(text):
                end = start + self.chunk_size
                
                if end < len(text):
                    # Look backwards for a newline within the last 100 characters
                    nl_pos = text.rfind('\n', max(start, end - 100), end)
                    if nl_pos != -1:
                        end = nl_pos + 1
                    else:
                        # Otherwise look for a space
                        sp_pos = text.rfind(' ', max(start, end - 50), end)
                        if sp_pos != -1:
                            end = sp_pos + 1
                
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "page_number": page["page_number"],
                        "content": chunk_text
                    })
                    chunk_idx += 1
                
                start = end - self.chunk_overlap
                if start < 0 or end >= len(text):
                    break
                    
        return chunks
