from PySide6.QtCore import QObject, Signal
from core.app_config import AppConfig
from utils.logger import logger

class AppState(QObject):
    """Central manager for application runtime state."""
    state_changed = Signal(str, object)
    
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self._state = {
            "selected_model": self.config.get("selected_model"),
            "ollama_status": "Checking",
            "available_models": [],
            "ollama_endpoint": self.config.get("ollama_endpoint", "http://localhost:11434"),
            "active_conversation_id": None,
            "active_preset": "general",
            "current_messages": [],
            "generation_state": "idle",
            "last_generation_stats": {},
            "last_memories_used": 0,
            "last_sources_used": 0,
            "default_knowledge_mode": self.config.get("default_knowledge_mode", "none"),
            "active_knowledge_mode": self.config.get("default_knowledge_mode", "none"),
            "active_knowledge_doc_ids": [],
            "memory_enabled": self.config.get("memory_enabled", True),
            "temperature": float(self.config.get("temperature", 0.7)),
            "default_preset": self.config.get("default_preset", "general"),
            "top_k": int(self.config.get("top_k", 5)),
            "similarity_threshold": float(self.config.get("similarity_threshold", 0.2)),
            "max_memories": int(self.config.get("max_memories", 5)),
            "context_message_limit": int(self.config.get("context_message_limit", 30))
        }

    def get(self, key, default=None):
        return self._state.get(key, default)
        
    def set(self, key, value):
        # We allow setting the same value for current_messages to force a UI refresh
        # but for simple scalar values, we skip identical updates.
        if key == "current_messages" or self._state.get(key) != value:
            self._state[key] = value
            self.state_changed.emit(key, value)
            if key in (
                "selected_model", "ollama_endpoint", "default_knowledge_mode", 
                "memory_enabled", "temperature", "default_preset", "top_k", 
                "similarity_threshold", "max_memories", "context_message_limit",
                "theme", "enter_to_send", "tray_icon_enabled", "notifications_enabled", "minimize_to_tray"
            ):
                self.config.set(key, value)
            logger.debug("AppState updated: %s", key)

    # Maintain properties for backward compatibility with Phase 1 components
    @property
    def selected_model(self):
        return self.get("selected_model")

    @selected_model.setter
    def selected_model(self, value):
        self.set("selected_model", value)

    @property
    def ollama_status(self):
        return self.get("ollama_status")

    @ollama_status.setter
    def ollama_status(self, value):
        self.set("ollama_status", value)

    @property
    def available_models(self):
        return self.get("available_models")

    @available_models.setter
    def available_models(self, value):
        self.set("available_models", value)

    @property
    def ollama_endpoint(self):
        return self.get("ollama_endpoint")

    @ollama_endpoint.setter
    def ollama_endpoint(self, value):
        self.set("ollama_endpoint", value)

    @property
    def active_preset(self):
        return self.get("active_preset", "general")

    @active_preset.setter
    def active_preset(self, value):
        self.set("active_preset", value)

