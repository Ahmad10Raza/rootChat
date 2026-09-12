import re
from core.app_state import AppState
from database.repositories.memory_repository import MemoryRepository

class MemoryManager:
    """Manages creation, deduplication, and retrieval of relevant local memories."""
    
    def __init__(self, app_state: AppState, repo: MemoryRepository):
        self.app_state = app_state
        self.repo = repo
        
    def create_memory(self, content: str, category: str = "preference") -> bool:
        # Check for duplicates before adding
        content = content.strip()
        memories = self.repo.list_memories()
        for m in memories:
            if m["content"].lower() == content.lower():
                return False  # Avoid duplicate
        
        self.repo.create_memory(content, category)
        return True
        
    def detect_and_save_explicit_memory(self, user_message: str) -> bool:
        """
        Detects if a user message is an explicit command to remember something.
        Returns True if a memory was extracted and saved.
        """
        pattern = re.compile(r"^(?:remember|save|keep)\s+(?:this|that\s+)?(.+)", re.IGNORECASE)
        match = pattern.search(user_message.strip())
        if match:
            memory_content = match.group(1).strip()
            # Basic perspective shift
            if memory_content.lower().startswith("i "):
                memory_content = "User " + memory_content[2:]
            elif memory_content.lower().startswith("my "):
                memory_content = "User's " + memory_content[3:]
                
            return self.create_memory(memory_content)
            
        return False
        
    def get_relevant_memories(self, query: str, limit: int = 5) -> list:
        """
        Retrieves the most relevant memories for a given query based on keyword overlap.
        """
        if not self.app_state.get("memory_enabled", True):
            return []
            
        memories = self.repo.list_memories(only_enabled=True)
        if not memories:
            return []
            
        # Extremely simple keyword overlap scoring
        query_words = set(re.findall(r'\w+', query.lower()))
        
        scored = []
        for mem in memories:
            mem_words = set(re.findall(r'\w+', mem["content"].lower()))
            overlap = len(query_words.intersection(mem_words))
            if overlap > 0:
                scored.append((overlap, mem))
                
        # Sort by score desc, then by date desc
        scored.sort(key=lambda x: (x[0], x[1]["updated_at"]), reverse=True)
        
        return [item[1] for item in scored[:limit]]
