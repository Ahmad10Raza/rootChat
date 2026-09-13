import json
from database.database import DatabaseManager
from utils.logger import logger

class MemoryRepository:
    """Handles database operations for memories, including embeddings and category filtering."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create_memory(self, content: str, category: str = "general", source: str = "user", embedding: list = None) -> int:
        emb_blob = json.dumps(embedding).encode('utf-8') if embedding else None
        query = "INSERT INTO memories (content, category, source, embedding) VALUES (?, ?, ?, ?)"
        mem_id = self.db.execute_query(query, (content, category, source, emb_blob), commit=True)
        logger.debug("Created new memory with ID %d (category=%s)", mem_id, category)
        return mem_id

    def get_memory(self, memory_id: int, include_embedding: bool = False):
        query = "SELECT * FROM memories WHERE id = ?"
        result = self.db.execute_query(query, (memory_id,))
        if not result:
            return None
        mem = dict(result[0])
        if include_embedding and mem.get("embedding"):
            try:
                mem["embedding"] = json.loads(mem["embedding"].decode('utf-8'))
            except Exception:
                mem["embedding"] = None
        elif not include_embedding:
            mem.pop("embedding", None)
        return mem

    def list_memories(self, only_enabled: bool = False, category: str = None, search_text: str = None, search: str = None, include_embedding: bool = False):
        conditions = []
        params = []
        
        target_search = search_text or search
        if only_enabled:
            conditions.append("is_enabled = 1")
        if category and category != "all":
            conditions.append("category = ?")
            params.append(category)
        if target_search and target_search.strip():
            conditions.append("content LIKE ?")
            params.append(f"%{target_search.strip()}%")
            
        query = "SELECT * FROM memories"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY updated_at DESC"
        
        results = self.db.execute_query(query, tuple(params))
        memories = []
        for row in results:
            mem = dict(row)
            if include_embedding and mem.get("embedding"):
                try:
                    mem["embedding"] = json.loads(mem["embedding"].decode('utf-8'))
                except Exception:
                    mem["embedding"] = None
            elif not include_embedding:
                mem.pop("embedding", None)
            memories.append(mem)
        return memories

    def get_active_memories_with_embeddings(self) -> list:
        """Fetches all active memories for vector similarity matching."""
        return self.list_memories(only_enabled=True, include_embedding=True)

    def get_stats(self) -> dict:
        """Returns counts of total, active, and per-category memories."""
        total_res = self.db.execute_query("SELECT COUNT(*) as total, SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as active FROM memories")
        total = total_res[0]["total"] if total_res else 0
        active = total_res[0]["active"] if total_res and total_res[0]["active"] is not None else 0
        
        cat_res = self.db.execute_query("SELECT category, COUNT(*) as count FROM memories GROUP BY category")
        by_category = {row["category"]: row["count"] for row in cat_res} if cat_res else {}
        
        return {"total": total, "active": active, "by_category": by_category}

    def update_memory(self, memory_id: int, content: str = None, category: str = None, is_enabled: bool = None, embedding: list = None):
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
        if embedding is not None:
            updates.append("embedding = ?")
            params.append(json.dumps(embedding).encode('utf-8') if embedding else None)
            
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
