from database.database import DatabaseManager
from utils.logger import logger

class ConversationRepository:
    """Handles database operations for conversations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create_conversation(self, title: str, model: str, preset: str = "general", knowledge_mode: str = "none", knowledge_doc_ids: str = "[]") -> int:
        query = "INSERT INTO conversations (title, model, preset, knowledge_mode, knowledge_doc_ids) VALUES (?, ?, ?, ?, ?)"
        conv_id = self.db.execute_query(query, (title, model, preset, knowledge_mode, knowledge_doc_ids), commit=True)
        logger.debug("Created new conversation with ID %d (preset: %s, knowledge_mode: %s)", conv_id, preset, knowledge_mode)
        return conv_id

    def get_conversation(self, conversation_id: int):
        query = "SELECT * FROM conversations WHERE id = ?"
        result = self.db.execute_query(query, (conversation_id,))
        return dict(result[0]) if result else None

    def list_conversations(self, include_archived=False):
        query = "SELECT * FROM conversations"
        if not include_archived:
            query += " WHERE is_archived = 0"
        query += " ORDER BY is_pinned DESC, updated_at DESC"
        results = self.db.execute_query(query)
        return [dict(row) for row in results]

    def search_conversations(self, term: str, include_archived=False):
        term_like = f"%{term}%"
        query = """
            SELECT DISTINCT c.* 
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE (c.title LIKE ? OR m.content LIKE ?)
        """
        if not include_archived:
            query += " AND c.is_archived = 0"
        query += " ORDER BY c.is_pinned DESC, c.updated_at DESC"
        results = self.db.execute_query(query, (term_like, term_like))
        return [dict(row) for row in results]

    def update_conversation(self, conversation_id: int, title: str = None, model: str = None, is_pinned: bool = None, is_archived: bool = None, preset: str = None, knowledge_mode: str = None, knowledge_doc_ids: str = None):
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if model is not None:
            updates.append("model = ?")
            params.append(model)
        if preset is not None:
            updates.append("preset = ?")
            params.append(preset)
        if knowledge_mode is not None:
            updates.append("knowledge_mode = ?")
            params.append(knowledge_mode)
        if knowledge_doc_ids is not None:
            updates.append("knowledge_doc_ids = ?")
            params.append(knowledge_doc_ids)
        if is_pinned is not None:
            updates.append("is_pinned = ?")
            params.append(1 if is_pinned else 0)
        if is_archived is not None:
            updates.append("is_archived = ?")
            params.append(1 if is_archived else 0)
            
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?"
            params.append(conversation_id)
            self.db.execute_query(query, tuple(params), commit=True)
            logger.debug("Updated conversation %d", conversation_id)

    def delete_conversation(self, conversation_id: int):
        # ON DELETE CASCADE ensures messages are deleted automatically
        query = "DELETE FROM conversations WHERE id = ?"
        self.db.execute_query(query, (conversation_id,), commit=True)
        logger.info("Deleted conversation %d", conversation_id)

    def delete_all_conversations(self):
        """Deletes all conversations and cascaded messages."""
        self.db.execute_query("DELETE FROM conversations", commit=True)
        logger.info("Deleted all conversations")

