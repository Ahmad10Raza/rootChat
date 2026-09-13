from core.app_state import AppState
from core.memory_manager import MemoryManager
from database.repositories.message_repository import MessageRepository
from retrieval.retriever import Retriever
from core.presets import get_preset
from utils.logger import logger

class ContextManager:
    """Responsible for building the structured context payload sent to Ollama."""
    
    def __init__(self, app_state: AppState, memory_manager: MemoryManager, msg_repo: MessageRepository, retriever: Retriever = None):
        self.app_state = app_state
        self.memory_manager = memory_manager
        self.msg_repo = msg_repo
        self.retriever = retriever
        
    def build_context(self, conversation_id: int, current_user_message: str) -> list:
        context_messages = []
        
        # 1. Base System Prompt from Persona / Preset
        preset_id = self.app_state.get("active_preset", "general")
        preset_info = get_preset(preset_id)
        sys_prompt = self.app_state.get("system_prompt") or preset_info.get("system_prompt")
        
        # 2. Inject Relevant Memories
        if self.app_state.get("memory_enabled", True):
            mem_limit = int(self.app_state.get("max_memories", 5))
            relevant_memories = self.memory_manager.get_relevant_memories(current_user_message, limit=mem_limit)
            if relevant_memories:
                memory_lines = [f"- [{m.get('category', 'general').capitalize()}] {m['content']}" for m in relevant_memories]
                memory_text = "\n".join(memory_lines)
                sys_prompt += (
                    f"\n\nUSER PERSONAL MEMORY & BACKGROUND\n---------------------------------\n"
                    f"The following facts are remembered about the user from past conversations:\n"
                    f"{memory_text}\n\n"
                    f"INSTRUCTIONS FOR RECALLED MEMORIES:\n"
                    f"1. Always treat these memories as established facts about the user (e.g. their background, programming languages, tools, skills, preferences, and project environment).\n"
                    f"2. Prioritize and directly align your recommendations, code examples, tech stack choices, and answers with these facts, especially when the user asks for advice 'based on my background' or preferences.\n"
                    f"3. Directly use these remembered skills and preferences to answer, rather than offering generic options across other unrelated tech stacks."
                )
                self.app_state.set("last_memories_used", len(relevant_memories))
                self.app_state.set("last_memories_data", relevant_memories)
            else:
                self.app_state.set("last_memories_used", 0)
                self.app_state.set("last_memories_data", [])
        else:
            self.app_state.set("last_memories_used", 0)
            self.app_state.set("last_memories_data", [])

        # 2.5 Inject Document RAG Context (Scoped per Conversation)
        knowledge_mode = self.app_state.get("active_knowledge_mode", "none")
        chunks = []
        
        if self.app_state.get("knowledge_enabled", True) and self.retriever and knowledge_mode != "none":
            top_k = int(self.app_state.get("top_k", 5))
            threshold = float(self.app_state.get("similarity_threshold", 0.2))
            
            if knowledge_mode == "all":
                chunks = self.retriever.retrieve(current_user_message, top_k=top_k, similarity_threshold=threshold, doc_ids=None)
            elif knowledge_mode == "specific":
                doc_ids = self.app_state.get("active_knowledge_doc_ids", [])
                if doc_ids:
                    chunks = self.retriever.retrieve(current_user_message, top_k=top_k, similarity_threshold=threshold, doc_ids=doc_ids)

        if chunks:
            doc_text = "Relevant local documents:\n\n"
            for chunk in chunks:
                doc_text += f"[Source: {chunk['filename']}, Page {chunk.get('page_number', '?')}]\n{chunk['content']}\n\n"
            sys_prompt += (
                f"\n\nDOCUMENT CONTEXT\n----------------\n"
                f"The following reference material has been retrieved from the user's attached documents:\n\n"
                f"{doc_text}\n"
                f"INSTRUCTIONS FOR ATTACHED DOCUMENTS:\n"
                f"1. Use the reference material above to answer the user's questions about these files, documents, parts, or data.\n"
                f"2. Cite the source filename when referencing information from them.\n"
                f"3. Never claim that you cannot view, access, or read these files, because their extracted contents are provided right above.\n"
            )
            
            self.app_state.set("last_sources_used", len(chunks))
            self.app_state.set("last_sources_data", chunks)
        else:
            if knowledge_mode != "none":
                logger.info("Knowledge mode is '%s', but no chunks matched query: '%s'", knowledge_mode, current_user_message)
            self.app_state.set("last_sources_used", 0)
            self.app_state.set("last_sources_data", [])
            
        context_messages.append({"role": "system", "content": sys_prompt})
        
        # 3. Recent Conversation History
        limit = int(self.app_state.get("context_message_limit", 30))
        messages = self.msg_repo.get_messages(conversation_id)
        
        # Exclude the very last message since it's the empty assistant placeholder we just created
        for msg in messages[-limit-1:-1]:
            context_messages.append({"role": msg["role"], "content": msg["content"]})
            
        return context_messages
