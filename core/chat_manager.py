from PySide6.QtCore import QObject, Signal
from core.app_state import AppState
from core.ollama_client import OllamaClient
from core.stream_worker import StreamWorker
from database.database import DatabaseManager
from database.repositories.conversation_repository import ConversationRepository
from database.repositories.message_repository import MessageRepository
from utils.logger import logger

class ChatManager(QObject):
    # Signals for UI updates
    message_added = Signal(dict)
    message_removed = Signal(int)
    chunk_received = Signal(str)
    stats_received = Signal(dict)
    generation_started = Signal()
    generation_finished = Signal(str)
    generation_error = Signal(str)
    generation_stopped = Signal()
    conversation_created = Signal(int)
    
    def __init__(self, app_state: AppState, client: OllamaClient, db_manager: DatabaseManager, memory_manager, context_manager):
        super().__init__()
        self.app_state = app_state
        self.client = client
        self.conv_repo = ConversationRepository(db_manager)
        self.msg_repo = MessageRepository(db_manager)
        self.memory_manager = memory_manager
        self.context_manager = context_manager
        self.worker = None
        self.current_assistant_msg_id = None
        
    def start_new_conversation(self):
        """Prepares state for a new chat (not saved to DB until first message)."""
        self.app_state.set("active_conversation_id", None)
        self.app_state.set("current_messages", [])
        self.app_state.set("last_memories_used", 0)
        self.app_state.set("last_sources_used", 0)
        self.app_state.set("last_sources_data", [])
        self.app_state.set("last_generation_stats", {})
        
    def load_conversation(self, conversation_id: int):
        """Loads conversation context and sets it active."""
        conv = self.conv_repo.get_conversation(conversation_id)
        if conv:
            self.app_state.set("active_conversation_id", conversation_id)
            if conv.get("model"):
                self.app_state.set("selected_model", conv["model"])
            if conv.get("preset"):
                self.app_state.set("active_preset", conv["preset"])
            else:
                self.app_state.set("active_preset", "general")
            messages = self.msg_repo.get_messages(conversation_id)
            self.app_state.set("current_messages", messages)
            return messages
        return []
        
    def _ensure_conversation_exists(self, initial_message: str):
        """Creates a conversation record if one does not exist for the current view."""
        conv_id = self.app_state.get("active_conversation_id")
        if not conv_id:
            model = self.app_state.get("selected_model") or "default"
            preset = self.app_state.get("active_preset", "general")
            # Create a placeholder to grab an ID first
            conv_id = self.conv_repo.create_conversation("New Chat...", model, preset=preset)
            
            # Now build a distinct, short title
            words = initial_message.split()
            short = " ".join(words[:2])
            if len(words) > 2:
                short += "..."
                
            final_title = f"Chat #{conv_id}: {short}"
            self.conv_repo.update_conversation(conv_id, title=final_title)
            
            self.app_state.set("active_conversation_id", conv_id)
            self.conversation_created.emit(conv_id)
        return conv_id
        
    def send_message(self, content: str):
        """Handles user sending a message."""
        content = content.strip()
        if not content:
            return
            
        conv_id = self._ensure_conversation_exists(content)
        
        # Save user message
        user_msg_id = self.msg_repo.create_message(conv_id, "user", content)
        user_msg = {"id": user_msg_id, "role": "user", "content": content}
        self.message_added.emit(user_msg)
        
        # Phase 3: Detect explicit memory commands
        is_memory_command = self.memory_manager.detect_and_save_explicit_memory(content)
        if is_memory_command:
            # Short-circuit Ollama, just reply with a local confirmation
            self._handle_local_memory_confirmation(conv_id)
        else:
            self._start_generation(conv_id)
            
    def _handle_local_memory_confirmation(self, conv_id: int):
        ast_msg_id = self.msg_repo.create_message(conv_id, "assistant", "✓ Saved to memory")
        ast_msg = {"id": ast_msg_id, "role": "assistant", "content": "✓ Saved to memory"}
        self.message_added.emit(ast_msg)
        # Finish immediately without invoking StreamWorker
        self.generation_finished.emit("✓ Saved to memory")
        
    def _start_generation(self, conv_id: int):
        """Internal method to start background stream generation."""
        # Save empty assistant message placeholder
        ast_msg_id = self.msg_repo.create_message(conv_id, "assistant", "")
        self.current_assistant_msg_id = ast_msg_id
        ast_msg = {"id": ast_msg_id, "role": "assistant", "content": ""}
        self.message_added.emit(ast_msg)
        
        self.app_state.set("generation_state", "generating")
        self.generation_started.emit()
        
        # Build context using Phase 3 ContextManager
        messages = self.msg_repo.get_messages(conv_id)
        if len(messages) >= 2:
            current_user_message = messages[-2]["content"]
        else:
            current_user_message = ""
            
        context_messages = self.context_manager.build_context(conv_id, current_user_message)
            
        model = self.app_state.get("selected_model")
        options = {"temperature": 0.7}
        
        self.worker = StreamWorker(self.client, model, context_messages, options)
        self.worker.chunk_received.connect(self.chunk_received.emit)
        self.worker.stats_received.connect(self._on_stats_received)
        self.worker.generation_finished.connect(self._on_generation_finished)
        self.worker.generation_error.connect(self._on_generation_error)
        self.worker.start()
        
    def stop_generation(self):
        """Stops an active generation stream but keeps partial response."""
        if self.worker and self.app_state.get("generation_state") == "generating":
            self.worker.stop()
            self.app_state.set("generation_state", "idle")
            self.generation_stopped.emit()
            
    def regenerate_response(self):
        """Regenerates the last assistant response."""
        conv_id = self.app_state.get("active_conversation_id")
        if not conv_id:
            return
            
        messages = self.msg_repo.get_messages(conv_id)
        if not messages:
            return
            
        # Delete the last assistant message and start generation
        last_msg = messages[-1]
        if last_msg["role"] == "assistant":
            self.msg_repo.delete_messages_after(conv_id, last_msg["id"])
            self.message_removed.emit(last_msg["id"])
            self._start_generation(conv_id)

    def delete_message(self, message_id: int):
        """Deletes a single message and emits message_removed."""
        self.msg_repo.delete_message(message_id)
        self.message_removed.emit(message_id)

    def _on_generation_finished(self, full_response: str):
        # Phase 4: Append sources if used
        sources = self.app_state.get("last_sources_data", [])
        if sources:
            source_text = "\n\n---\n**Sources:**\n"
            added_sources = set()
            for s in sources:
                src_key = f"{s['filename']} — Page {s.get('page_number', '?')}"
                if src_key not in added_sources:
                    source_text += f"- {src_key}\n"
                    added_sources.add(src_key)
            full_response += source_text
            # Emit chunk so it appears in UI immediately
            self.chunk_received.emit(source_text)
            
        if self.current_assistant_msg_id:
            self.msg_repo.update_message_content(self.current_assistant_msg_id, full_response)
        self.app_state.set("generation_state", "idle")
        self.generation_finished.emit(full_response)
        
    def _on_stats_received(self, stats: dict):
        self.app_state.set("last_generation_stats", stats)
        self.stats_received.emit(stats)

    def _on_generation_error(self, error_msg: str):
        self.app_state.set("generation_state", "error")
        self.generation_error.emit(error_msg)
