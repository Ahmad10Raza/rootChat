from database.database import DatabaseManager
from utils.logger import logger

class MemoryRepository:
    """Handles database operations for memories."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create_memory(self, content: str, category: str = "general", source: str = "user") -> int:
        query = "INSERT INTO memories (content, category, source) VALUES (?, ?, ?)"
        mem_id = self.db.execute_query(query, (content, category, source), commit=True)
        logger.debug("Created new memory with ID %d", mem_id)
        return mem_id

    def get_memory(self, memory_id: int):
        query = "SELECT * FROM memories WHERE id = ?"
        result = self.db.execute_query(query, (memory_id,))
        return dict(result[0]) if result else None

    def list_memories(self, only_enabled=False):
        query = "SELECT * FROM memories"
        if only_enabled:
            query += " WHERE is_enabled = 1"
        query += " ORDER BY updated_at DESC"
        results = self.db.execute_query(query)
        return [dict(row) for row in results]

    def update_memory(self, memory_id: int, content: str = None, category: str = None, is_enabled: bool = None):
        updates = []
        params = []
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if is_enabled is not None:
            updates.append("is_enabled = ?")
            params.append(1 if is_enabled else 0)
            
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"
            params.append(memory_id)
            self.db.execute_query(query, tuple(params), commit=True)
            logger.debug("Updated memory %d", memory_id)

    def delete_memory(self, memory_id: int):
        query = "DELETE FROM memories WHERE id = ?"
        self.db.execute_query(query, (memory_id,), commit=True)
        logger.info("Deleted memory %d", memory_id)
        
    def clear_all_memories(self):
        self.db.execute_query("DELETE FROM memories", commit=True)
        logger.info("Cleared all memories")
