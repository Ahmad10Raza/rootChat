"""Modern settings dialog for rootChat with responsive scrollable cards."""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QCheckBox, QPushButton, QLineEdit,
    QScrollArea, QWidget, QFrame, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap, QIcon
from core.app_state import AppState
from ui.theme.theme_manager import ThemeManager
from utils.resource_path import get_resource_path
from utils.logger import logger
from version import __version__


class SettingsDialog(QDialog):
    """Modern card-based settings dialog with responsive scrolling."""
    
    theme_changed = Signal(str)
    endpoint_changed = Signal(str)
    manage_models_requested = Signal()
    
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.setWindowTitle("Settings")
        self.resize(580, 660)
        self.setMinimumSize(480, 420)
        
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
        title_col.addWidget(self.subtitle_label)

        header_layout.addLayout(title_col, 1)
        root_layout.addWidget(self.header_frame)

        # ─── 2. SCROLLABLE MIDDLE CONTENT ───
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("SettingsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.container = QWidget()
        self.container.setObjectName("SettingsScrollContainer")
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
        card_chat, chat_layout = self._create_card("💬  Chat & Interaction", "Composer input shortcuts and generation behavior")
        
        self.enter_send = QCheckBox("Enter to send message")
        self.enter_send.setObjectName("SettingCheckBox")
        self.enter_send.setChecked(self.app_state.get("enter_to_send", True))
        self.enter_send.toggled.connect(self._on_enter_send_toggled)
        chat_layout.addWidget(self.enter_send)

        chat_sub = QLabel("When enabled, pressing Enter sends prompt. Press Shift+Enter for new line.")
        chat_sub.setObjectName("FieldHelper")
        chat_layout.addWidget(chat_sub)

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
        mem_layout.addWidget(mem_sub)

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
        rag_layout.addWidget(rag_sub)

        self.content_layout.addWidget(card_rag)

        # ──── Card 6: Desktop Integration ────
        card_desktop, desktop_layout = self._create_card("🖥️  Desktop Integration", "System tray, background alerts, and window close behavior")
        
        self.tray_toggle = QCheckBox("Show System Tray Icon")
        self.tray_toggle.setObjectName("SettingCheckBox")
        self.tray_toggle.setChecked(self.app_state.get("tray_icon_enabled", True))
        self.tray_toggle.toggled.connect(self._on_tray_toggle)
        desktop_layout.addWidget(self.tray_toggle)

        tray_sub = QLabel("Keeps rootChat running in the background with quick access from the tray menu.")
        tray_sub.setObjectName("FieldHelper")
        desktop_layout.addWidget(tray_sub)

        desktop_layout.addSpacing(6)

        self.notif_toggle = QCheckBox("Desktop Notifications")
        self.notif_toggle.setObjectName("SettingCheckBox")
        self.notif_toggle.setChecked(self.app_state.get("notifications_enabled", True))
        self.notif_toggle.toggled.connect(self._on_notif_toggle)
        desktop_layout.addWidget(self.notif_toggle)

        notif_sub = QLabel("Sends OS notification when background LLM generation finishes.")
        notif_sub.setObjectName("FieldHelper")
        desktop_layout.addWidget(notif_sub)

        desktop_layout.addSpacing(6)

        self.minimize_to_tray_toggle = QCheckBox("Minimize to System Tray on Window Close")
        self.minimize_to_tray_toggle.setObjectName("SettingCheckBox")
        self.minimize_to_tray_toggle.setChecked(self.app_state.get("minimize_to_tray", False))
        self.minimize_to_tray_toggle.toggled.connect(self._on_minimize_to_tray_toggle)
        desktop_layout.addWidget(self.minimize_to_tray_toggle)

        min_sub = QLabel("Clicking the window close button hides the app to tray instead of quitting.")
        min_sub.setObjectName("FieldHelper")
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
        footer_layout.addWidget(config_path_lbl, 1)

        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("SettingsCloseBtn")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFixedHeight(34)
        self.close_btn.setMinimumWidth(90)
        self.close_btn.clicked.connect(self.close)
        footer_layout.addWidget(self.close_btn, 0)

        root_layout.addWidget(self.footer_frame)

    def _create_card(self, title: str, subtitle: str) -> tuple[QFrame, QVBoxLayout]:
        """Creates a standardized modern card container."""
        card = QFrame()
        card.setObjectName("SettingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        card_title = QLabel(title)
        card_title.setObjectName("CardTitle")
        layout.addWidget(card_title)

        card_sub = QLabel(subtitle)
        card_sub.setObjectName("CardSubtitle")
        layout.addWidget(card_sub)

        layout.addSpacing(4)
        return card, layout

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
            
            /* Dropdown */
            QComboBox#ThemeCombo {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 500;
            }}
            QComboBox#ThemeCombo:focus {{
                border-color: {c.ACCENT};
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
        self.app_state.config.set("theme", mode)
        self.theme_changed.emit(mode)
        self._apply_theme()

    def _on_enter_send_toggled(self, checked: bool):
        self.app_state.set("enter_to_send", checked)
        self.app_state.config.set("enter_to_send", checked)

    def _on_save_endpoint(self):
        new_endpoint = self.endpoint_input.text().strip()
        if new_endpoint:
            self.app_state.set("ollama_endpoint", new_endpoint)
            self.app_state.config.set("ollama_endpoint", new_endpoint)
            self.status_badge.setText("● Connecting...")
            self.status_badge.setStyleSheet("color: #FFB545; background-color: rgba(255, 181, 69, 0.12); border: 1px solid rgba(255, 181, 69, 0.3);")
            self.endpoint_changed.emit(new_endpoint)
            logger.info("Saved new Ollama endpoint: %s", new_endpoint)

    def _on_tray_toggle(self, checked: bool):
        self.app_state.set("tray_icon_enabled", checked)
        self.app_state.config.set("tray_icon_enabled", checked)

    def _on_notif_toggle(self, checked: bool):
        self.app_state.set("notifications_enabled", checked)
        self.app_state.config.set("notifications_enabled", checked)

    def _on_minimize_to_tray_toggle(self, checked: bool):
        self.app_state.set("minimize_to_tray", checked)
        self.app_state.config.set("minimize_to_tray", checked)
