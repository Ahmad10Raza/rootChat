import re
import math
from PySide6.QtCore import QObject, Signal
from core.app_state import AppState
from database.repositories.memory_repository import MemoryRepository
from utils.logger import logger


# Common English stopwords to prevent false-positive keyword overlaps
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "tell", "show", "give", "please", "can", "just"
}


def cosine_similarity(v1: list, v2: list) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


# ─────────────────────────────────────────────────────────
# 1. Grammar Normalization & Category Classification
# ─────────────────────────────────────────────────────────

def normalize_grammar(text: str) -> str:
    """Transforms first-person statements into clean third-person persona memories."""
    text = text.strip().lstrip(":- ").strip()
    
    # Leading perspective shifts
    replacements = [
        (r"^i\s+am\s+", "User is "),
        (r"^i'm\s+", "User is "),
        (r"^i\s+have\s+", "User has "),
        (r"^i've\s+", "User has "),
        (r"^i\s+work\s+", "User works "),
        (r"^i\s+live\s+", "User lives "),
        (r"^i\s+prefer\s+", "User prefers "),
        (r"^i\s+like\s+", "User likes "),
        (r"^i\s+love\s+", "User loves "),
        (r"^i\s+need\s+", "User needs "),
        (r"^i\s+use\s+", "User uses "),
        (r"^my\s+", "User's "),
    ]
    
    lower_text = text.lower()
    for pattern, repl in replacements:
        if re.search(pattern, lower_text):
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
            break
            
    # Clean trailing punctuation
    text = text.rstrip(".!?;")
    return text


def classify_category(content: str) -> str:
    """Classifies a memory into one of four standard categories."""
    content_lower = content.lower()
    
    # 1. Preferences
    pref_keywords = [
        "prefer", "prefers", "preference", "favorite", "like", "likes", "love", "loves", 
        "dislike", "dislikes", "hate", "format", "style", "concise", "brief", "detailed", 
        "tone", "python 3", "dark mode", "light mode", "enjoy", "enjoys"
    ]
    if any(kw in content_lower for kw in pref_keywords):
        return "preference"
        
    # 2. Work & Technical Skills
    work_keywords = ["work", "job", "company", "developer", "engineer", "software", "coder", "tech", "stack", "project", "code", "programming", "devops", "linux", "backend", "frontend"]
    if any(kw in content_lower for kw in work_keywords):
        return "work"
        
    # 3. Personal & Biography
    personal_keywords = ["live", "located", "city", "country", "name is", "dog", "cat", "pet", "family", "born", "age", "timezone", "fluent", "speak"]
    if any(kw in content_lower for kw in personal_keywords):
        return "personal"
        
    return "general"


def stem_word(w: str) -> str:
    """Lightweight suffix trimmer for resilient non-stopword lexical matching."""
    w = w.lower().strip()
    if len(w) > 4:
        if w.endswith("ies") and len(w) > 5:
            return w[:-3] + "y"
        # Only strip 'es' when preceded by sibilants (boxes -> box, watches -> watch, dishes -> dish)
        if (w.endswith("shes") or w.endswith("ches") or w.endswith("xes") or w.endswith("zes") or w.endswith("sses")) and len(w) > 4:
            return w[:-2]
        if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            return w[:-1]
        if w.endswith("ing") and len(w) > 5:
            return w[:-3]
        if w.endswith("ed") and len(w) > 4:
            return w[:-2]
    return w


class MemoryManager(QObject):
    """
    Production-ready memory engine for rootChat.
    Handles natural language intent parsing, grammar normalization,
    vector embedding generation, and hybrid semantic + stopword-filtered retrieval.
    """
    memory_added = Signal(dict)
    memory_updated = Signal(dict)
    memory_deleted = Signal(int)
    memories_cleared = Signal()

    def __init__(self, app_state: AppState, repo: MemoryRepository, embedding_provider=None):
        super().__init__()
        self.app_state = app_state
        self.repo = repo
        self.embedding_provider = embedding_provider
        self.backfill_missing_embeddings()

    def set_embedding_provider(self, provider):
        """Sets or updates the embedding provider (e.g. OllamaEmbeddings)."""
        self.embedding_provider = provider
        self.backfill_missing_embeddings()

    def _get_embedding(self, text: str) -> list | None:
        """Safely generates embedding using whichever method the provider exposes."""
        if not self.embedding_provider or not text:
            return None
        try:
            if hasattr(self.embedding_provider, "embed_query"):
                return self.embedding_provider.embed_query(text)
            elif hasattr(self.embedding_provider, "embed_text"):
                return self.embedding_provider.embed_text(text)
        except Exception as e:
            logger.warning("Could not generate embedding for text '%s...': %s", text[:30], e)
        return None

    def backfill_missing_embeddings(self):
        """Scans active memories in SQLite and generates embeddings for any that have NULL embedding."""
        if not self.embedding_provider:
            return
        try:
            memories = self.repo.list_memories(only_enabled=True, include_embedding=True)
            backfilled_count = 0
            for m in memories:
                if m.get("embedding") is None and m.get("content"):
                    emb = self._get_embedding(m["content"])
                    if emb:
                        self.repo.update_memory(m["id"], embedding=emb)
                        backfilled_count += 1
            if backfilled_count > 0:
                logger.info("Successfully backfilled vector embeddings for %d memories", backfilled_count)
        except Exception as e:
            logger.warning("Error during memory embeddings backfill: %s", e)

    normalize_grammar = staticmethod(normalize_grammar)
    classify_category = staticmethod(classify_category)

    # ─────────────────────────────────────────────────────────
    # 2. Natural Language Intent Recognition
    # ─────────────────────────────────────────────────────────

    def parse_memory_intent(self, user_message: str) -> tuple[str, str, str, str]:
        """
        Parses user messages for memory commands.
        Returns: (intent_type, memory_content, category, remaining_query)
        intent_type is one of: 'remember', 'forget', or None.
        """
        msg = user_message.strip()
        
        # 1. Check for Forget / Delete Commands
        forget_patterns = [
            r"^(?:please\s+)?(?:forget|delete\s+memory(?:\s+about)?|remove\s+memory(?:\s+about)?)[\s:]+(?:that\s+)?(.+)$",
            r"^(?:can\s+you\s+)?forget\s+(?:that\s+)?(.+)$",
        ]
        for pat in forget_patterns:
            m = re.match(pat, msg, re.IGNORECASE)
            if m:
                target = m.group(1).strip()
                return ("forget", target, "general", "")
                
        # 2. Check for Remember / Save Commands
        remember_patterns = [
            r"^(?:please\s+)?(?:remember|keep\s+in\s+mind|don't\s+forget|note\s+that|save\s+to\s+memory)[\s:]+(?:that\s+)?(.+)$",
            r"^(?:can\s+you\s+)?remember\s+(?:that\s+)?(.+)$",
            r"^(?:save|keep)\s+(?:this|that)[\s:]+(.+)$",
        ]
        
        for pat in remember_patterns:
            m = re.match(pat, msg, re.IGNORECASE)
            if m:
                raw_payload = m.group(1).strip()
                
                # Check for hybrid multi-intent prompts (e.g. "Remember that I use Linux, and show me...")
                hybrid_split = re.split(
                    r"(?:[,;]\s+(?:and\s+)?(?=(?:show|tell|explain|what|how|where|when|why|give|write|generate|recommend|can\s+you|please)\b)|\.\s+)",
                    raw_payload,
                    flags=re.IGNORECASE
                )
                
                if len(hybrid_split) > 1 and len(hybrid_split[1].strip()) > 3:
                    fact_part = hybrid_split[0].strip()
                    remaining_query = hybrid_split[1].strip()
                else:
                    fact_part = raw_payload
                    remaining_query = ""
                    
                normalized = self.normalize_grammar(fact_part)
                category = self.classify_category(normalized)
                return ("remember", normalized, category, remaining_query)
                
        return (None, "", "general", "")

    def detect_and_save_explicit_memory(self, user_message: str) -> bool:
        """Backward-compatible helper for Phase 3 tests and legacy callers."""
        intent, fact, cat, _ = self.parse_memory_intent(user_message)
        if intent == "remember" and fact:
            return self.create_memory(fact, category=cat, source="explicit")
        return False

    # ─────────────────────────────────────────────────────────
    # 3. Memory CRUD Operations & Embeddings
    # ─────────────────────────────────────────────────────────

    def create_memory(self, content: str, category: str = "general", source: str = "user") -> bool:
        """Creates a memory, prevents duplicates, and computes vector embeddings if available."""
        content = content.strip()
        if not content:
            return False
            
        # Deduplication check
        existing_memories = self.repo.list_memories()
        for m in existing_memories:
            if m["content"].lower() == content.lower():
                # Already exists, ensure it is enabled
                if not m["is_enabled"]:
                    self.repo.update_memory(m["id"], is_enabled=True)
                return False
                
        # Generate embedding if provider available
        embedding = self._get_embedding(content)
                
        mem_id = self.repo.create_memory(content, category=category, source=source, embedding=embedding)
        new_mem = self.repo.get_memory(mem_id)
        if new_mem:
            self.memory_added.emit(new_mem)
        return True

    def forget_memory(self, query: str) -> str:
        """Searches for a memory matching the query and deletes it. Returns deleted text or empty string."""
        query = query.strip()
        if not query:
            return ""
            
        memories = self.repo.list_memories()
        if not memories:
            return ""
            
        # 1. Exact match
        for m in memories:
            if query.lower() in m["content"].lower():
                self.repo.delete_memory(m["id"])
                self.memory_deleted.emit(m["id"])
                return m["content"]
                
        # 2. Keyword match
        query_words = set(re.findall(r'\w+', query.lower())) - STOP_WORDS
        best_match = None
        best_score = 0
        for m in memories:
            m_words = set(re.findall(r'\w+', m["content"].lower())) - STOP_WORDS
            overlap = len(query_words.intersection(m_words))
            if overlap > best_score:
                best_score = overlap
                best_match = m
                
        if best_match and best_score > 0:
            self.repo.delete_memory(best_match["id"])
            self.memory_deleted.emit(best_match["id"])
            return best_match["content"]
            
        return ""

    def update_memory(self, memory_id: int, content: str = None, category: str = None, is_enabled: bool = None) -> bool:
        """Updates a memory's text, category, or status. Re-embeds content if changed and provider available."""
        embedding = None
        if content:
            embedding = self._get_embedding(content)
        return self.repo.update_memory(
            memory_id,
            content=content,
            category=category,
            is_enabled=is_enabled,
            embedding=embedding
        )

    # ─────────────────────────────────────────────────────────
    # 4. Hybrid Retrieval Engine (Semantic + Stopword-Filtered)
    # ─────────────────────────────────────────────────────────

    def get_relevant_memories(self, query: str, limit: int = 5) -> list:
        """
        Retrieves relevant active memories using hybrid semantic vector search
        combined with stopword-filtered lexical scoring and stemming.
        """
        if not self.app_state.get("memory_enabled", True):
            return []
            
        memories = self.repo.get_active_memories_with_embeddings()
        if not memories:
            return []
            
        query_words = set(re.findall(r'\w+', query.lower())) - STOP_WORDS
        query_stems = {stem_word(w) for w in query_words}
        
        # Try computing query embedding
        query_embedding = self._get_embedding(query)
                
        scored = []
        for mem in memories:
            mem_content = mem["content"]
            mem_words = set(re.findall(r'\w+', mem_content.lower())) - STOP_WORDS
            mem_stems = {stem_word(w) for w in mem_words}
            
            # Semantic score (cosine similarity)
            sim = 0.0
            if query_embedding and mem.get("embedding"):
                sim = cosine_similarity(query_embedding, mem["embedding"])
                
            # Lexical score (stopword-filtered exact + stemmed overlap)
            exact_overlap = len(query_words.intersection(mem_words))
            stemmed_overlap = len(query_stems.intersection(mem_stems))
            overlap = max(exact_overlap, stemmed_overlap)
            lex_score = overlap / max(1, len(mem_words)) if overlap > 0 else 0.0
            
            # Decision threshold:
            # Must meet either semantic threshold >= 0.40 OR have >= 1 significant non-stopword match
            if sim >= 0.40 or overlap >= 1:
                combined_score = (sim * 0.7) + (lex_score * 0.3)
                # Boost if both semantic and lexical agree
                if sim >= 0.40 and overlap >= 1:
                    combined_score += 0.20
                scored.append((combined_score, mem))
                
        scored.sort(key=lambda x: (x[0], x[1].get("updated_at", "")), reverse=True)
        return [item[1] for item in scored[:limit]]

