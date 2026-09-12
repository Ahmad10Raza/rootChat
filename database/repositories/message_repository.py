from database.database import DatabaseManager
from utils.logger import logger

class MessageRepository:
    """Handles database operations for messages."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create_message(self, conversation_id: int, role: str, content: str) -> int:
        query = "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)"
        msg_id = self.db.execute_query(query, (conversation_id, role, content), commit=True)
        # Update the associated conversation's updated_at timestamp
        self.db.execute_query("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,), commit=True)
        return msg_id

    def get_messages(self, conversation_id: int):
        query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC, id ASC"
        results = self.db.execute_query(query, (conversation_id,))
        return [dict(row) for row in results]

    def delete_messages_after(self, conversation_id: int, message_id: int):
        """Deletes this message and all subsequent messages in the conversation. Used for regenerating responses."""
        query = "DELETE FROM messages WHERE conversation_id = ? AND id >= ?"
        self.db.execute_query(query, (conversation_id, message_id), commit=True)
        logger.debug("Deleted messages from %d onwards in conversation %d", message_id, conversation_id)
        
    def update_message_content(self, message_id: int, content: str):
        query = "UPDATE messages SET content = ? WHERE id = ?"
        self.db.execute_query(query, (content, message_id), commit=True)

    def delete_message(self, message_id: int):
        """Deletes a single message by ID."""
        query = "DELETE FROM messages WHERE id = ?"
        self.db.execute_query(query, (message_id,), commit=True)
        logger.debug("Deleted message %d", message_id)
