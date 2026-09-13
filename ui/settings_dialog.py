"""Modern settings dialog for rootChat with responsive scrollable cards."""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QCheckBox, QPushButton, QLineEdit,
    QScrollArea, QWidget, QFrame, QSizePolicy, QApplication,
    QSpinBox, QDoubleSpinBox, QSlider, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot, QEvent
from PySide6.QtGui import QPixmap, QIcon
from core.app_state import AppState
from core.presets import list_presets
from database.database import DatabaseManager, DB_FILE
from ui.theme.theme_manager import ThemeManager
from utils.resource_path import get_resource_path
from utils.logger import logger
from version import __version__


def format_file_size(path: str) -> str:
    """Returns human-readable size of a file."""
    if os.path.exists(path):
        try:
            size_bytes = os.path.getsize(path)
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.2f} MB"
        except Exception:
            return "Unknown"
    return "0 B (Not created yet)"


class SettingsDialog(QDialog):
    """Modern card-based settings dialog with responsive scrolling."""
    
    theme_changed = Signal(str)
    endpoint_changed = Signal(str)
    manage_models_requested = Signal()
    manage_memories_requested = Signal()
    manage_knowledge_requested = Signal()
    clear_chats_requested = Signal()
    
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.db_path = DB_FILE
        self.setWindowTitle("Settings")
        self.resize(580, 720)
        self.setMinimumSize(540, 500)
        
        # Window icon
        icon_path = get_resource_path("resources/icons/rootChat.png")
        if not os.path.exists(icon_path):
            icon_path = get_resource_path("resources/icons/rootChat.svg")
        self.setWindowIcon(QIcon(icon_path))

        self.init_ui()
        self._apply_theme()
        self._update_connection_status()

    def init_ui(self):
        # Root layout with no outer margins so header and footer touch dialog edges
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ─── 1. FIXED TOP HEADER ───
        self.header_frame = QFrame()
        self.header_frame.setObjectName("SettingsHeader")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(24, 16, 24, 16)
        header_layout.setSpacing(12)

        header_icon_lbl = QLabel()
        header_icon_lbl.setObjectName("HeaderIcon")
        icon_path = get_resource_path("resources/icons/rootChat_32.png")
        if os.path.exists(icon_path):
            header_icon_lbl.setPixmap(QPixmap(icon_path).scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            header_icon_lbl.setText("⚙")
        header_layout.addWidget(header_icon_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        
        self.title_label = QLabel("Settings")
        self.title_label.setObjectName("SettingsTitle")
        title_col.addWidget(self.title_label)

        self.subtitle_label = QLabel("Configure models, inference service, and desktop integration")
        self.subtitle_label.setObjectName("SettingsSubtitle")
        self.subtitle_label.setWordWrap(True)
        title_col.addWidget(self.subtitle_label)

        header_layout.addLayout(title_col, 1)
        root_layout.addWidget(self.header_frame)

        # ─── 2. SCROLLABLE MIDDLE CONTENT ───
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("SettingsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.horizontalScrollBar().setEnabled(False)
        self.scroll_area.horizontalScrollBar().valueChanged.connect(lambda _: self.scroll_area.horizontalScrollBar().setValue(0))
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.viewport().installEventFilter(self)

        self.container = QWidget()
        self.container.setObjectName("SettingsScrollContainer")
        self.container.setMinimumWidth(0)
        self.container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(24, 18, 24, 20)
        self.content_layout.setSpacing(14)

        # ──── Card 1: Appearance ────
        card_app, app_layout = self._create_card("🎨  Appearance", "Customize interface theme and color accents")
        
        theme_row = QHBoxLayout()
        theme_row.setSpacing(12)
        theme_lbl = QLabel("Color Theme:")
        theme_lbl.setObjectName("FieldLabel")
        theme_row.addWidget(theme_lbl)

        theme_row.addStretch(1)

        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("ThemeCombo")
        self.theme_combo.setMinimumWidth(150)
        self.theme_combo.setFixedHeight(32)
        self.theme_combo.addItems(["Dark", "Light", "System"])
        current_theme = self.app_state.get("theme", "dark")
        idx_map = {"dark": 0, "light": 1, "system": 2}
        self.theme_combo.setCurrentIndex(idx_map.get(current_theme, 0))
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self.theme_combo)
        app_layout.addLayout(theme_row)

        accent_note = QLabel("Active accent: Safety Orange (#FF5F15)")
        accent_note.setObjectName("FieldHelper")
        accent_note.setWordWrap(True)
        app_layout.addWidget(accent_note)

        self.content_layout.addWidget(card_app)

        # ──── Card 2: Ollama Service ────
        card_ollama, ollama_layout = self._create_card("⚡  Ollama Service", "Local LLM inference endpoint & installed models")
        
        # Status header row
        status_row = QHBoxLayout()
        endpoint_lbl = QLabel("API Endpoint URL:")
        endpoint_lbl.setObjectName("FieldLabel")
        status_row.addWidget(endpoint_lbl)
        
        status_row.addStretch(1)
        
        self.status_badge = QLabel("● Checking...")
        self.status_badge.setObjectName("OllamaStatusBadge")
        status_row.addWidget(self.status_badge)
        ollama_layout.addLayout(status_row)

        self.endpoint_input = QLineEdit(self.app_state.get("ollama_endpoint", "http://localhost:11434"))
        self.endpoint_input.setObjectName("EndpointInput")
        self.endpoint_input.setPlaceholderText("http://localhost:11434")
        self.endpoint_input.setFixedHeight(34)
        ollama_layout.addWidget(self.endpoint_input)

        # Default Model row
        ollama_layout.addSpacing(6)
        model_row = QHBoxLayout()
        model_row.setSpacing(12)
        model_lbl = QLabel("Default Model:")
        model_lbl.setObjectName("FieldLabel")
        model_row.addWidget(model_lbl)
        model_row.addStretch(1)

        self.default_model_combo = QComboBox()
        self.default_model_combo.setObjectName("DefaultModelCombo")
        self.default_model_combo.setMinimumWidth(180)
        self.default_model_combo.setFixedHeight(32)
        self._populate_models_combo()
        self.default_model_combo.currentTextChanged.connect(self._on_default_model_changed)
        model_row.addWidget(self.default_model_combo)
        ollama_layout.addLayout(model_row)

        model_sub = QLabel("Model preselected when starting new conversations.")
        model_sub.setObjectName("FieldHelper")
        model_sub.setWordWrap(True)
        ollama_layout.addWidget(model_sub)

        ollama_layout.addSpacing(6)
        endpoint_btn_row = QHBoxLayout()
        endpoint_btn_row.setSpacing(10)

        self.manage_models_btn = QPushButton("⚙ Manage Models...")
        self.manage_models_btn.setObjectName("SecondaryBtn")
        self.manage_models_btn.setFixedHeight(32)
        self.manage_models_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_models_btn.clicked.connect(self.manage_models_requested.emit)
        endpoint_btn_row.addWidget(self.manage_models_btn)

        endpoint_btn_row.addStretch(1)

        self.save_endpoint_btn = QPushButton("↻ Save && Reconnect")
        self.save_endpoint_btn.setObjectName("PrimaryAccentBtn")
        self.save_endpoint_btn.setFixedHeight(32)
        self.save_endpoint_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_endpoint_btn.clicked.connect(self._on_save_endpoint)
        endpoint_btn_row.addWidget(self.save_endpoint_btn)
        
        ollama_layout.addLayout(endpoint_btn_row)
        self.content_layout.addWidget(card_ollama)

        # ──── Card 3: Chat & Interaction ────
        card_chat, chat_layout = self._create_card("💬  Chat & Interaction", "Composer shortcuts, assistant persona, and generation parameters")
        
        self.enter_send = QCheckBox("Enter to send message")
        self.enter_send.setObjectName("SettingCheckBox")
        self.enter_send.setChecked(self.app_state.get("enter_to_send", True))
        self.enter_send.toggled.connect(self._on_enter_send_toggled)
        chat_layout.addWidget(self.enter_send)

        chat_sub = QLabel("When enabled, pressing Enter sends prompt. Press Shift+Enter for new line.")
        chat_sub.setObjectName("FieldHelper")
        chat_sub.setWordWrap(True)
        chat_layout.addWidget(chat_sub)

        chat_layout.addSpacing(8)

        # Default Persona
        preset_row = QHBoxLayout()
        preset_row.setSpacing(12)
        preset_lbl = QLabel("Default Persona:")
        preset_lbl.setObjectName("FieldLabel")
        preset_row.addWidget(preset_lbl)
        preset_row.addStretch(1)

        self.default_preset_combo = QComboBox()
        self.default_preset_combo.setObjectName("DefaultPresetCombo")
        self.default_preset_combo.setMinimumWidth(180)
        self.default_preset_combo.setFixedHeight(32)
        for p in list_presets():
            self.default_preset_combo.addItem(f"{p['icon']} {p['name']}", userData=p["id"])
        
        cur_preset = self.app_state.get("default_preset", "general")
        idx = self.default_preset_combo.findData(cur_preset)
        if idx >= 0:
            self.default_preset_combo.setCurrentIndex(idx)
        self.default_preset_combo.currentIndexChanged.connect(self._on_default_preset_changed)
        preset_row.addWidget(self.default_preset_combo)
        chat_layout.addLayout(preset_row)

        preset_sub = QLabel("Default persona and system prompt applied when starting new chat sessions.")
        preset_sub.setObjectName("FieldHelper")
        preset_sub.setWordWrap(True)
        chat_layout.addWidget(preset_sub)

        chat_layout.addSpacing(8)

        # Temperature Slider
        temp_row = QHBoxLayout()
        temp_row.setSpacing(12)
        temp_lbl = QLabel("Generation Temperature:")
        temp_lbl.setObjectName("FieldLabel")
        temp_row.addWidget(temp_lbl)
        temp_row.addStretch(1)

        cur_temp = float(self.app_state.get("temperature", 0.70))
        self.temperature_val_lbl = QLabel(f"{cur_temp:.2f}")
        self.temperature_val_lbl.setObjectName("FieldBadge")
        temp_row.addWidget(self.temperature_val_lbl)
        chat_layout.addLayout(temp_row)

        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.temperature_slider.setObjectName("TemperatureSlider")
        self.temperature_slider.setRange(0, 100)
        self.temperature_slider.setValue(int(round(cur_temp * 100)))
        self.temperature_slider.valueChanged.connect(self._on_temperature_slider_changed)
        chat_layout.addWidget(self.temperature_slider)

        temp_sub = QLabel("0.0 is focused & deterministic; 0.7 is balanced; 1.0 is creative & diverse.")
        temp_sub.setObjectName("FieldHelper")
        temp_sub.setWordWrap(True)
        chat_layout.addWidget(temp_sub)

        chat_layout.addSpacing(8)

        # Context Message Limit
        ctx_row = QHBoxLayout()
        ctx_row.setSpacing(12)
        ctx_lbl = QLabel("Context History Limit:")
        ctx_lbl.setObjectName("FieldLabel")
        ctx_row.addWidget(ctx_lbl)
        ctx_row.addStretch(1)

        self.context_limit_spin = QSpinBox()
        self.context_limit_spin.setObjectName("ContextLimitSpin")
        self.context_limit_spin.setRange(4, 100)
        self.context_limit_spin.setSingleStep(2)
        self.context_limit_spin.setValue(int(self.app_state.get("context_message_limit", 30)))
        self.context_limit_spin.setSuffix(" messages")
        self.context_limit_spin.setMinimumWidth(130)
        self.context_limit_spin.setFixedHeight(30)
        self.context_limit_spin.valueChanged.connect(lambda v: self.app_state.set("context_message_limit", v))
        ctx_row.addWidget(self.context_limit_spin)
        chat_layout.addLayout(ctx_row)

        ctx_sub = QLabel("Maximum number of recent chat messages passed into model context window.")
        ctx_sub.setObjectName("FieldHelper")
        ctx_sub.setWordWrap(True)
        chat_layout.addWidget(ctx_sub)

        self.content_layout.addWidget(card_chat)

        # ──── Card 4: Memory Engine ────
        card_mem, mem_layout = self._create_card("🧠  Memory Engine", "Persistent recall of user facts and conversation context")
        
        self.memory_toggle = QCheckBox("Enable Memory Engine")
        self.memory_toggle.setObjectName("SettingCheckBox")
        self.memory_toggle.setChecked(self.app_state.get("memory_enabled", True))
        self.memory_toggle.toggled.connect(lambda v: self.app_state.set("memory_enabled", v))
        mem_layout.addWidget(self.memory_toggle)

        mem_sub = QLabel("Extracts and recalls key facts, preferences, and personal details across chats.")
        mem_sub.setObjectName("FieldHelper")
        mem_sub.setWordWrap(True)
        mem_layout.addWidget(mem_sub)

        mem_layout.addSpacing(8)

        # Max Recalled Memories
        max_mem_row = QHBoxLayout()
        max_mem_row.setSpacing(12)
        max_mem_lbl = QLabel("Max Recalled Memories:")
        max_mem_lbl.setObjectName("FieldLabel")
        max_mem_row.addWidget(max_mem_lbl)
        max_mem_row.addStretch(1)

        self.max_memories_spin = QSpinBox()
        self.max_memories_spin.setObjectName("MaxMemoriesSpin")
        self.max_memories_spin.setRange(1, 20)
        self.max_memories_spin.setValue(int(self.app_state.get("max_memories", 5)))
        self.max_memories_spin.setSuffix(" items")
        self.max_memories_spin.setMinimumWidth(110)
        self.max_memories_spin.setFixedHeight(30)
        self.max_memories_spin.valueChanged.connect(lambda v: self.app_state.set("max_memories", v))
        max_mem_row.addWidget(self.max_memories_spin)
        mem_layout.addLayout(max_mem_row)

        max_mem_sub = QLabel("Maximum number of relevant past facts injected into prompt context.")
        max_mem_sub.setObjectName("FieldHelper")
        max_mem_sub.setWordWrap(True)
        mem_layout.addWidget(max_mem_sub)

        mem_layout.addSpacing(6)
        mem_btn_row = QHBoxLayout()
        mem_btn_row.setSpacing(10)
        self.manage_memories_btn = QPushButton("🧠 Manage Memories...")
        self.manage_memories_btn.setObjectName("SecondaryBtn")
        self.manage_memories_btn.setFixedHeight(32)
        self.manage_memories_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_memories_btn.clicked.connect(self.manage_memories_requested.emit)
        mem_btn_row.addWidget(self.manage_memories_btn)
        mem_btn_row.addStretch(1)
        mem_layout.addLayout(mem_btn_row)

        self.content_layout.addWidget(card_mem)

        # ──── Card 5: Knowledge Base (RAG) ────
        card_rag, rag_layout = self._create_card("📚  Knowledge Base (RAG)", "Local document indexing and context-augmented queries")
        
        self.knowledge_toggle = QCheckBox("Enable RAG (Document Context)")
        self.knowledge_toggle.setObjectName("SettingCheckBox")
        self.knowledge_toggle.setChecked(self.app_state.get("knowledge_enabled", True))
        self.knowledge_toggle.toggled.connect(lambda v: self.app_state.set("knowledge_enabled", v))
        rag_layout.addWidget(self.knowledge_toggle)

        rag_sub = QLabel("Injects semantic search matches from ingested PDFs, code, and text into prompts.")
        rag_sub.setObjectName("FieldHelper")
        rag_sub.setWordWrap(True)
        rag_layout.addWidget(rag_sub)

        rag_layout.addSpacing(8)

        k_default_row = QHBoxLayout()
        k_default_lbl = QLabel("Default Context:")
        k_default_lbl.setObjectName("FieldLabel")
        k_default_row.addWidget(k_default_lbl)
        k_default_row.addStretch(1)

        self.default_knowledge_combo = QComboBox()
        self.default_knowledge_combo.setObjectName("DefaultKnowledgeCombo")
        self.default_knowledge_combo.setMinimumWidth(180)
        self.default_knowledge_combo.setFixedHeight(32)
        self.default_knowledge_combo.addItem("Off (Pure Chat — Fast)", "none")
        self.default_knowledge_combo.addItem("All Documents (Library RAG)", "all")

        cur_k_mode = self.app_state.get("default_knowledge_mode", "none")
        idx = self.default_knowledge_combo.findData(cur_k_mode)
        if idx >= 0:
            self.default_knowledge_combo.setCurrentIndex(idx)
        self.default_knowledge_combo.currentIndexChanged.connect(self._on_default_knowledge_changed)
        k_default_row.addWidget(self.default_knowledge_combo)
        rag_layout.addLayout(k_default_row)

        k_default_sub = QLabel("New chats start with this knowledge scope. You can change scope anytime via the top bar or composer.")
        k_default_sub.setObjectName("FieldHelper")
        k_default_sub.setWordWrap(True)
        rag_layout.addWidget(k_default_sub)

        rag_layout.addSpacing(8)

        # Retrieved Chunks (Top-K)
        top_k_row = QHBoxLayout()
        top_k_row.setSpacing(12)
        top_k_lbl = QLabel("Retrieved Chunks (Top-K):")
        top_k_lbl.setObjectName("FieldLabel")
        top_k_row.addWidget(top_k_lbl)
        top_k_row.addStretch(1)

        self.top_k_spin = QSpinBox()
        self.top_k_spin.setObjectName("TopKSpin")
        self.top_k_spin.setRange(1, 15)
        self.top_k_spin.setValue(int(self.app_state.get("top_k", 5)))
        self.top_k_spin.setSuffix(" chunks")
        self.top_k_spin.setMinimumWidth(110)
        self.top_k_spin.setFixedHeight(30)
        self.top_k_spin.valueChanged.connect(lambda v: self.app_state.set("top_k", v))
        top_k_row.addWidget(self.top_k_spin)
        rag_layout.addLayout(top_k_row)

        top_k_sub = QLabel("Number of relevant text passages retrieved from indexed documents per query.")
        top_k_sub.setObjectName("FieldHelper")
        top_k_sub.setWordWrap(True)
        rag_layout.addWidget(top_k_sub)

        rag_layout.addSpacing(8)

        # Similarity Threshold
        sim_row = QHBoxLayout()
        sim_row.setSpacing(12)
        sim_lbl = QLabel("Similarity Threshold:")
        sim_lbl.setObjectName("FieldLabel")
        sim_row.addWidget(sim_lbl)
        sim_row.addStretch(1)

        self.similarity_spin = QDoubleSpinBox()
        self.similarity_spin.setObjectName("SimilaritySpin")
        self.similarity_spin.setRange(0.0, 1.0)
        self.similarity_spin.setSingleStep(0.05)
        self.similarity_spin.setDecimals(2)
        self.similarity_spin.setValue(float(self.app_state.get("similarity_threshold", 0.20)))
        self.similarity_spin.setMinimumWidth(110)
        self.similarity_spin.setFixedHeight(30)
        self.similarity_spin.valueChanged.connect(lambda v: self.app_state.set("similarity_threshold", round(v, 2)))
        sim_row.addWidget(self.similarity_spin)
        rag_layout.addLayout(sim_row)

        sim_sub = QLabel("Cosine similarity cutoff for including retrieved document passages.")
        sim_sub.setObjectName("FieldHelper")
        sim_sub.setWordWrap(True)
        rag_layout.addWidget(sim_sub)

        rag_layout.addSpacing(6)
        k_btn_row = QHBoxLayout()
        k_btn_row.setSpacing(10)
        self.manage_knowledge_btn = QPushButton("📚 Manage Knowledge Library...")
        self.manage_knowledge_btn.setObjectName("SecondaryBtn")
        self.manage_knowledge_btn.setFixedHeight(32)
        self.manage_knowledge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_knowledge_btn.clicked.connect(self.manage_knowledge_requested.emit)
        k_btn_row.addWidget(self.manage_knowledge_btn)
        k_btn_row.addStretch(1)
        rag_layout.addLayout(k_btn_row)

        self.content_layout.addWidget(card_rag)

        # ──── Card 6: Data & Storage ────
        card_storage, storage_layout = self._create_card("💾  Data & Storage", "Local database file, storage usage, and maintenance")

        db_path_row = QHBoxLayout()
        db_path_lbl = QLabel("Database Location:")
        db_path_lbl.setObjectName("FieldLabel")
        db_path_row.addWidget(db_path_lbl)
        db_path_row.addStretch(1)

        self.db_path_val = QLabel(self.db_path)
        self.db_path_val.setObjectName("TechStackLabel")
        self.db_path_val.setToolTip(self.db_path)
        db_path_row.addWidget(self.db_path_val)
        storage_layout.addLayout(db_path_row)

        db_size_row = QHBoxLayout()
        db_size_lbl = QLabel("Database Size:")
        db_size_lbl.setObjectName("FieldLabel")
        db_size_row.addWidget(db_size_lbl)
        db_size_row.addStretch(1)

        self.db_size_val = QLabel(format_file_size(self.db_path))
        self.db_size_val.setObjectName("FieldBadge")
        db_size_row.addWidget(self.db_size_val)
        storage_layout.addLayout(db_size_row)

        storage_layout.addSpacing(6)
        storage_btn_row = QHBoxLayout()
        storage_btn_row.setSpacing(10)

        self.vacuum_btn = QPushButton("🧹 Optimize Database")
        self.vacuum_btn.setObjectName("SecondaryBtn")
        self.vacuum_btn.setFixedHeight(32)
        self.vacuum_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vacuum_btn.clicked.connect(self._on_vacuum_db)
        storage_btn_row.addWidget(self.vacuum_btn)

        self.clear_chats_btn = QPushButton("🗑️ Clear All Chats")
        self.clear_chats_btn.setObjectName("DangerBtn")
        self.clear_chats_btn.setFixedHeight(32)
        self.clear_chats_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_chats_btn.clicked.connect(self._on_clear_chats)
        storage_btn_row.addWidget(self.clear_chats_btn)

        storage_btn_row.addStretch(1)
        storage_layout.addLayout(storage_btn_row)

        self.storage_status_lbl = QLabel("")
        self.storage_status_lbl.setObjectName("FieldHelper")
        self.storage_status_lbl.setWordWrap(True)
        storage_layout.addWidget(self.storage_status_lbl)

        self.content_layout.addWidget(card_storage)

        # ──── Card 6: Desktop Integration ────
        card_desktop, desktop_layout = self._create_card("🖥️  Desktop Integration", "System tray, background alerts, and window close behavior")
        
        self.tray_toggle = QCheckBox("Show System Tray Icon")
        self.tray_toggle.setObjectName("SettingCheckBox")
        self.tray_toggle.setChecked(self.app_state.get("tray_icon_enabled", True))
        self.tray_toggle.toggled.connect(self._on_tray_toggle)
        desktop_layout.addWidget(self.tray_toggle)

        tray_sub = QLabel("Keeps rootChat running in the background with quick access from the tray menu.")
        tray_sub.setObjectName("FieldHelper")
        tray_sub.setWordWrap(True)
        desktop_layout.addWidget(tray_sub)

        desktop_layout.addSpacing(6)

        self.notif_toggle = QCheckBox("Desktop Notifications")
        self.notif_toggle.setObjectName("SettingCheckBox")
        self.notif_toggle.setChecked(self.app_state.get("notifications_enabled", True))
        self.notif_toggle.toggled.connect(self._on_notif_toggle)
        desktop_layout.addWidget(self.notif_toggle)

        notif_sub = QLabel("Sends OS notification when background LLM generation finishes.")
        notif_sub.setObjectName("FieldHelper")
        notif_sub.setWordWrap(True)
        desktop_layout.addWidget(notif_sub)

        desktop_layout.addSpacing(6)

        self.minimize_to_tray_toggle = QCheckBox("Minimize to System Tray on Window Close")
        self.minimize_to_tray_toggle.setObjectName("SettingCheckBox")
        self.minimize_to_tray_toggle.setChecked(self.app_state.get("minimize_to_tray", False))
        self.minimize_to_tray_toggle.toggled.connect(self._on_minimize_to_tray_toggle)
        desktop_layout.addWidget(self.minimize_to_tray_toggle)

        min_sub = QLabel("Clicking the window close button hides the app to tray instead of quitting.")
        min_sub.setObjectName("FieldHelper")
        min_sub.setWordWrap(True)
        desktop_layout.addWidget(min_sub)

        self.content_layout.addWidget(card_desktop)

        # ──── Card 7: About rootChat ────
        card_about = QFrame()
        card_about.setObjectName("SettingsCard")
        about_main_layout = QVBoxLayout(card_about)
        about_main_layout.setContentsMargins(16, 16, 16, 16)
        about_main_layout.setSpacing(12)

        about_header_row = QHBoxLayout()
        about_header_row.setSpacing(14)

        # Robot Logo Avatar
        logo_lbl = QLabel()
        logo_lbl.setObjectName("AboutLogo")
        logo_path = get_resource_path("resources/icons/rootChat_128.png")
        if not os.path.exists(logo_path):
            logo_path = get_resource_path("resources/icons/rootChat.png")
        if os.path.exists(logo_path):
            logo_lbl.setPixmap(QPixmap(logo_path).scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo_lbl.setText("🤖")
            logo_lbl.setStyleSheet("font-size: 36px;")
        logo_lbl.setFixedSize(56, 56)
        about_header_row.addWidget(logo_lbl, 0, Qt.AlignmentFlag.AlignTop)

        about_details = QVBoxLayout()
        about_details.setSpacing(3)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        app_name_lbl = QLabel("rootChat")
        app_name_lbl.setObjectName("AboutAppName")
        title_row.addWidget(app_name_lbl)

        version_pill = QLabel(f"v{__version__}")
        version_pill.setObjectName("VersionPill")
        title_row.addWidget(version_pill)
        title_row.addStretch(1)
        about_details.addLayout(title_row)

        app_desc_lbl = QLabel("Private, offline AI desktop assistant powered by Ollama models")
        app_desc_lbl.setObjectName("AboutAppDesc")
        app_desc_lbl.setWordWrap(True)
        about_details.addWidget(app_desc_lbl)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(6)
        b1 = QLabel("🔒 100% Local")
        b1.setObjectName("FeatureBadge")
        b2 = QLabel("🛡️ Zero Telemetry")
        b2.setObjectName("FeatureBadge")
        b3 = QLabel("⚡ GPU Accelerated")
        b3.setObjectName("FeatureBadge")
        badges_row.addWidget(b1)
        badges_row.addWidget(b2)
        badges_row.addWidget(b3)
        badges_row.addStretch(1)
        about_details.addLayout(badges_row)

        about_header_row.addLayout(about_details, 1)
        about_main_layout.addLayout(about_header_row)

        divider = QFrame()
        divider.setObjectName("CardDivider")
        divider.setFixedHeight(1)
        about_main_layout.addWidget(divider)

        tech_row = QHBoxLayout()
        tech_lbl = QLabel("Engine: PySide6 (Qt6) • Ollama • SQLite • ChromaDB")
        tech_lbl.setObjectName("TechStackLabel")
        tech_lbl.setWordWrap(True)
        tech_row.addWidget(tech_lbl)
        about_main_layout.addLayout(tech_row)

        self.content_layout.addWidget(card_about)
        
        self.scroll_area.setWidget(self.container)
        root_layout.addWidget(self.scroll_area, 1)

        # ─── 3. FIXED BOTTOM FOOTER ───
        self.footer_frame = QFrame()
        self.footer_frame.setObjectName("SettingsFooter")
        footer_layout = QHBoxLayout(self.footer_frame)
        footer_layout.setContentsMargins(24, 12, 24, 12)
        footer_layout.setSpacing(12)

        config_path_lbl = QLabel("Config: ~/.config/rootChat/config.json")
        config_path_lbl.setObjectName("ConfigPathLabel")
        config_path_lbl.setWordWrap(True)
        footer_layout.addWidget(config_path_lbl, 1)

        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("SettingsCloseBtn")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFixedHeight(34)
        self.close_btn.setMinimumWidth(90)
        self.close_btn.clicked.connect(self.close)
        footer_layout.addWidget(self.close_btn, 0)

        root_layout.addWidget(self.footer_frame)

    def eventFilter(self, obj, event):
        """Filter out horizontal wheel scrolling events to strictly lock X-axis."""
        if hasattr(self, "scroll_area") and obj == self.scroll_area.viewport():
            if event.type() == QEvent.Type.Wheel:
                if event.angleDelta().y() == 0:
                    return True
        return super().eventFilter(obj, event)

    def _create_card(self, title: str, subtitle: str) -> tuple[QFrame, QVBoxLayout]:
        """Creates a standardized modern card container."""
        card = QFrame()
        card.setObjectName("SettingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        card_title = QLabel(title)
        card_title.setObjectName("CardTitle")
        card_title.setWordWrap(True)
        layout.addWidget(card_title)

        card_sub = QLabel(subtitle)
        card_sub.setObjectName("CardSubtitle")
        card_sub.setWordWrap(True)
        layout.addWidget(card_sub)

        layout.addSpacing(4)
        return card, layout

    def _populate_models_combo(self):
        """Populate default model selector with available models."""
        self.default_model_combo.clear()
        models = self.app_state.get("available_models", [])
        if models:
            for m in models:
                name = m.get("name") if isinstance(m, dict) else str(m)
                self.default_model_combo.addItem(name)
            current_selected = self.app_state.get("selected_model")
            idx = self.default_model_combo.findText(current_selected)
            if idx >= 0:
                self.default_model_combo.setCurrentIndex(idx)
        else:
            current_selected = self.app_state.get("selected_model")
            if current_selected:
                self.default_model_combo.addItem(current_selected)
            else:
                self.default_model_combo.addItem("(No models detected)")

    def _apply_theme(self):
        """Apply comprehensive styling using centralized ThemeManager tokens."""
        tm = ThemeManager.instance()
        c = tm.colors
        ff = tm.font_family
        mf = tm.mono_family

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c.BG_PRIMARY};
                color: {c.TEXT_PRIMARY};
                font-family: '{ff}';
            }}
            
            /* Header */
            #SettingsHeader {{
                background-color: {c.BG_SIDEBAR};
                border-bottom: 1px solid {c.BORDER_SUBTLE};
            }}
            #SettingsTitle {{
                color: {c.TEXT_PRIMARY};
                font-size: 18px;
                font-weight: 700;
            }}
            #SettingsSubtitle {{
                color: {c.TEXT_MUTED};
                font-size: 12px;
            }}
            
            /* Scroll Area & Container */
            #SettingsScrollArea {{
                background: transparent;
                border: none;
            }}
            #SettingsScrollContainer {{
                background: transparent;
            }}
            
            /* Cards */
            #SettingsCard {{
                background-color: {c.BG_CARD};
                border: 1px solid {c.BORDER};
                border-radius: 10px;
            }}
            #CardTitle {{
                color: {c.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 700;
            }}
            #CardSubtitle {{
                color: {c.TEXT_MUTED};
                font-size: 11px;
                margin-bottom: 2px;
            }}
            #CardDivider {{
                background-color: {c.BORDER_SUBTLE};
                border: none;
            }}
            
            /* Form Fields & Labels */
            #FieldLabel {{
                color: {c.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 600;
            }}
            #FieldBadge {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_ACCENT};
                border: 1px solid {c.BORDER};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 12px;
                font-weight: 700;
                font-family: '{mf}';
            }}
            #FieldHelper {{
                color: {c.TEXT_MUTED};
                font-size: 11px;
                margin-left: 28px;
                margin-top: -2px;
            }}
            QLineEdit#EndpointInput {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-family: '{mf}';
            }}
            QLineEdit#EndpointInput:focus {{
                border: 1px solid {c.ACCENT};
            }}
            
            /* Dropdowns */
            QComboBox {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 500;
            }}
            QComboBox:hover {{
                border-color: {c.BORDER_FOCUS};
                background-color: {c.BG_HOVER};
            }}
            QComboBox:focus {{
                border-color: {c.ACCENT};
            }}
            QComboBox QAbstractItemView {{
                background-color: {c.BG_CARD};
                color: {c.TEXT_PRIMARY};
                selection-background-color: {c.BG_SELECTED};
                selection-color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 26px;
                padding: 4px 8px;
                border-radius: 4px;
                color: {c.TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {c.BG_HOVER};
                color: {c.TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {c.BG_SELECTED};
                color: {c.TEXT_ACCENT};
            }}
            
            /* Spinboxes */
            QSpinBox, QDoubleSpinBox {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: 500;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {c.ACCENT};
            }}
            
            /* Sliders */
            QSlider::groove:horizontal {{
                height: 6px;
                background: {c.BG_INPUT};
                border: 1px solid {c.BORDER};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {c.ACCENT};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {c.TEXT_PRIMARY};
                border: 2px solid {c.ACCENT};
                width: 16px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {c.ACCENT_HOVER};
            }}
            
            /* Checkboxes */
            QCheckBox#SettingCheckBox {{
                color: {c.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 500;
                spacing: 10px;
            }}
            QCheckBox#SettingCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid {c.BORDER};
                background-color: {c.BG_INPUT};
            }}
            QCheckBox#SettingCheckBox::indicator:hover {{
                border-color: {c.BORDER_FOCUS};
            }}
            QCheckBox#SettingCheckBox::indicator:checked {{
                background-color: {c.ACCENT};
                border-color: {c.ACCENT};
                image: url("{get_resource_path('resources/icons/check.svg')}");
            }}
            
            /* Action Buttons */
            QPushButton#SecondaryBtn {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton#SecondaryBtn:hover {{
                background-color: {c.BG_HOVER};
                border-color: {c.BORDER_FOCUS};
            }}
            QPushButton#PrimaryAccentBtn {{
                background-color: {c.ACCENT};
                color: #FFFFFF;
                border: 1px solid {c.ACCENT};
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#PrimaryAccentBtn:hover {{
                background-color: {c.ACCENT_HOVER};
                border-color: {c.ACCENT_HOVER};
            }}
            QPushButton#PrimaryAccentBtn:pressed {{
                background-color: {c.ACCENT_PRESSED};
            }}
            QPushButton#DangerBtn {{
                background-color: rgba(255, 85, 85, 0.12);
                color: #FF5555;
                border: 1px solid rgba(255, 85, 85, 0.35);
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton#DangerBtn:hover {{
                background-color: rgba(255, 85, 85, 0.22);
                border-color: #FF5555;
            }}
            
            /* Status Badges */
            #OllamaStatusBadge {{
                font-size: 11px;
                font-weight: 600;
                padding: 3px 8px;
                border-radius: 10px;
            }}
            #VersionPill {{
                background-color: {c.BG_SELECTED};
                color: {c.TEXT_ACCENT};
                font-size: 11px;
                font-weight: 700;
                padding: 2px 8px;
                border-radius: 10px;
            }}
            #FeatureBadge {{
                background-color: rgba(255, 255, 255, 0.04);
                color: {c.TEXT_SECONDARY};
                font-size: 10px;
                font-weight: 600;
                padding: 2px 7px;
                border: 1px solid {c.BORDER_SUBTLE};
                border-radius: 4px;
            }}
            #AboutAppName {{
                color: {c.TEXT_PRIMARY};
                font-size: 16px;
                font-weight: 700;
            }}
            #AboutAppDesc {{
                color: {c.TEXT_SECONDARY};
                font-size: 12px;
            }}
            #TechStackLabel {{
                color: {c.TEXT_MUTED};
                font-size: 11px;
            }}
            
            /* Footer */
            #SettingsFooter {{
                background-color: {c.BG_SIDEBAR};
                border-top: 1px solid {c.BORDER_SUBTLE};
            }}
            #ConfigPathLabel {{
                color: {c.TEXT_MUTED};
                font-size: 11px;
            }}
            QPushButton#SettingsCloseBtn {{
                background-color: {c.BG_CARD};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#SettingsCloseBtn:hover {{
                background-color: {c.BG_HOVER};
                border-color: {c.ACCENT};
                color: #FFFFFF;
            }}
        """)

    def _update_connection_status(self):
        """Update live connection status badge."""
        status = self.app_state.get("ollama_status", "Offline")
        if status == "Connected":
            self.status_badge.setText("● Connected")
            self.status_badge.setStyleSheet("color: #35C759; background-color: rgba(53, 199, 89, 0.12); border: 1px solid rgba(53, 199, 89, 0.3);")
        else:
            self.status_badge.setText("● Offline")
            self.status_badge.setStyleSheet("color: #FF5555; background-color: rgba(255, 85, 85, 0.12); border: 1px solid rgba(255, 85, 85, 0.3);")

    def _on_theme_changed(self, text: str):
        mode = text.lower()
        self.app_state.set("theme", mode)
        self.theme_changed.emit(mode)
        self._apply_theme()

    def _on_default_model_changed(self, model_name: str):
        if model_name and model_name != "(No models detected)":
            self.app_state.set("selected_model", model_name)
            logger.info("Settings updated default model: %s", model_name)

    def _on_default_preset_changed(self, index: int):
        preset_id = self.default_preset_combo.itemData(index)
        if preset_id:
            self.app_state.set("default_preset", preset_id)
            logger.info("Settings updated default preset: %s", preset_id)

    def _on_temperature_slider_changed(self, val: int):
        temp = round(val / 100.0, 2)
        self.temperature_val_lbl.setText(f"{temp:.2f}")
        self.app_state.set("temperature", temp)

    def _on_enter_send_toggled(self, checked: bool):
        self.app_state.set("enter_to_send", checked)

    def _on_save_endpoint(self):
        new_endpoint = self.endpoint_input.text().strip()
        if new_endpoint:
            self.app_state.set("ollama_endpoint", new_endpoint)
            self.status_badge.setText("● Connecting...")
            self.status_badge.setStyleSheet("color: #FFB545; background-color: rgba(255, 181, 69, 0.12); border: 1px solid rgba(255, 181, 69, 0.3);")
            self.endpoint_changed.emit(new_endpoint)
            logger.info("Saved new Ollama endpoint: %s", new_endpoint)

    def _on_tray_toggle(self, checked: bool):
        self.app_state.set("tray_icon_enabled", checked)

    def _on_notif_toggle(self, checked: bool):
        self.app_state.set("notifications_enabled", checked)

    def _on_minimize_to_tray_toggle(self, checked: bool):
        self.app_state.set("minimize_to_tray", checked)

    def _on_default_knowledge_changed(self, index: int):
        val = self.default_knowledge_combo.currentData()
        self.app_state.set("default_knowledge_mode", val)
        logger.info("Saved default knowledge mode: %s", val)

    def _on_vacuum_db(self):
        """Run SQLite vacuum on the application database."""
        try:
            db = DatabaseManager(self.db_path)
            db.vacuum()
            self.db_size_val.setText(format_file_size(self.db_path))
            self.storage_status_lbl.setText("✓ Database optimized successfully!")
            self.storage_status_lbl.setStyleSheet("color: #35C759; font-size: 11px; margin-left: 28px;")
        except Exception as e:
            logger.error("Error optimizing database: %s", e)
            self.storage_status_lbl.setText(f"Error optimizing: {e}")
            self.storage_status_lbl.setStyleSheet("color: #FF5555; font-size: 11px; margin-left: 28px;")

    def _on_clear_chats(self):
        """Prompt user confirmation and delete all conversations."""
        ans = QMessageBox.question(
            self,
            "Clear All Chat History",
            "Are you sure you want to permanently delete all conversation history?\n\nThis will remove all past chats and messages. This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            try:
                from database.repositories.conversation_repository import ConversationRepository
                repo = ConversationRepository(DatabaseManager(self.db_path))
                repo.delete_all_conversations()
                self.app_state.set("active_conversation_id", None)
                self.app_state.set("current_messages", [])
                
                db = DatabaseManager(self.db_path)
                db.vacuum()
                self.db_size_val.setText(format_file_size(self.db_path))
                self.storage_status_lbl.setText("✓ All chat conversations deleted and storage optimized.")
                self.storage_status_lbl.setStyleSheet("color: #35C759; font-size: 11px; margin-left: 28px;")
                self.clear_chats_requested.emit()
            except Exception as e:
                logger.error("Error clearing chats: %s", e)
                QMessageBox.critical(self, "Error", f"Failed to clear chat history: {e}")

