"""
Modern, production-grade Memory Management Dialog for rootChat.
Features:
- Card-based UI matching rootChat Safety Orange (#FF5F15) design language
- Dynamic category filter chips (All, Preferences, Work, Personal, General)
- Real-time search by keyword
- Inline custom Memory Editor modal (no blocking QInputDialog)
- Active/Paused toggles per memory card
- Visual indicator for Vector Semantic vs Lexical indexing
- Dark/Light theme dynamic adaptation
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QCheckBox, QFrame, QWidget, QLineEdit, QStackedWidget,
    QTextEdit, QComboBox
)
from PySide6.QtCore import Qt, Signal, QSize
from core.memory_manager import MemoryManager
from ui.theme.theme_manager import ThemeManager
from utils.logger import logger


CATEGORY_CONFIG = {
    "preference": {
        "label": "🎨 Preference",
        "color": "#FF5F15",
        "bg": "rgba(255, 95, 21, 0.14)",
        "border": "rgba(255, 95, 21, 0.35)",
    },
    "work": {
        "label": "💼 Work & Skills",
        "color": "#5B9DF0",
        "bg": "rgba(91, 157, 240, 0.14)",
        "border": "rgba(91, 157, 240, 0.35)",
    },
    "personal": {
        "label": "👤 Personal",
        "color": "#A371F7",
        "bg": "rgba(163, 113, 247, 0.14)",
        "border": "rgba(163, 113, 247, 0.35)",
    },
    "general": {
        "label": "📌 General",
        "color": "#8B949E",
        "bg": "rgba(139, 148, 158, 0.14)",
        "border": "rgba(139, 148, 158, 0.35)",
    },
}


class MemoryEditorModal(QDialog):
    """Clean, dedicated modal for adding or editing an explicit memory."""

    def __init__(self, parent=None, memory: dict = None):
        super().__init__(parent)
        self.memory = memory
        self.is_edit = memory is not None
        self.setWindowTitle("Edit Memory" if self.is_edit else "Add New Memory")
        self.setFixedSize(480, 360)
        self.setModal(True)
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_lbl = QLabel("🧠")
        icon_lbl.setObjectName("ModalIcon")
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("Edit Memory" if self.is_edit else "Add New Memory")
        title_lbl.setObjectName("ModalTitle")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        title_col.addWidget(title_lbl)

        sub_lbl = QLabel("rootChat recalls this fact across conversations to customize responses.")
        sub_lbl.setObjectName("ModalSubtitle")
        sub_lbl.setStyleSheet("font-size: 11px;")
        sub_lbl.setWordWrap(True)
        title_col.addWidget(sub_lbl)
        header_layout.addLayout(title_col, 1)

        layout.addLayout(header_layout)

        # Content Input
        input_label = QLabel("Memory Content:")
        input_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        layout.addWidget(input_label)

        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("MemoryTextInput")
        self.text_edit.setPlaceholderText("e.g., I write backend services in Python and Go, and prefer concise code...")
        if self.is_edit and self.memory:
            self.text_edit.setPlainText(self.memory.get("content", ""))
        self.text_edit.setFixedHeight(110)
        layout.addWidget(self.text_edit)

        # Category Row
        cat_row = QHBoxLayout()
        cat_row.setSpacing(10)

        cat_lbl = QLabel("Category:")
        cat_lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        cat_row.addWidget(cat_lbl)

        self.cat_combo = QComboBox()
        self.cat_combo.setObjectName("MemoryCatCombo")
        self.cat_combo.addItem("🎨 Preference", "preference")
        self.cat_combo.addItem("💼 Work & Skills", "work")
        self.cat_combo.addItem("👤 Personal", "personal")
        self.cat_combo.addItem("📌 General", "general")

        if self.is_edit and self.memory:
            cur_cat = self.memory.get("category", "general")
            for idx in range(self.cat_combo.count()):
                if self.cat_combo.itemData(idx) == cur_cat:
                    self.cat_combo.setCurrentIndex(idx)
                    break
        cat_row.addWidget(self.cat_combo, 1)

        layout.addLayout(cat_row)

        # Active Checkbox
        self.active_check = QCheckBox("Active (recall this memory during chats)")
        self.active_check.setObjectName("MemoryActiveCheck")
        is_active = True
        if self.is_edit and self.memory:
            is_active = bool(self.memory.get("is_enabled", 1))
        self.active_check.setChecked(is_active)
        layout.addWidget(self.active_check)

        layout.addStretch(1)

        # Actions
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("ActionSecondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Memory")
        save_btn.setObjectName("ActionPrimaryBtn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _on_save(self):
        content = self.text_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Missing Content", "Please enter memory content before saving.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "content": self.text_edit.toPlainText().strip(),
            "category": self.cat_combo.currentData(),
            "is_enabled": self.active_check.isChecked()
        }

    def apply_theme(self):
        c = ThemeManager.instance().colors
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c.BG_PRIMARY};
                color: {c.TEXT_PRIMARY};
            }}
            #ModalIcon {{
                background-color: {c.ACCENT_MUTED};
                border: 1px solid {c.ACCENT};
                border-radius: 8px;
                font-size: 18px;
            }}
            #ModalTitle {{
                color: {c.TEXT_PRIMARY};
            }}
            #ModalSubtitle {{
                color: {c.TEXT_MUTED};
            }}
            #MemoryTextInput {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }}
            #MemoryTextInput:focus {{
                border-color: {c.ACCENT};
            }}
            #MemoryCatCombo {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            #MemoryCatCombo:focus {{
                border-color: {c.ACCENT};
            }}
            #MemoryActiveCheck {{
                font-size: 12px;
                color: {c.TEXT_PRIMARY};
                spacing: 8px;
            }}
            #ActionPrimaryBtn {{
                background-color: {c.ACCENT};
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                border-radius: 6px;
                padding: 7px 18px;
                border: none;
            }}
            #ActionPrimaryBtn:hover {{
                background-color: {c.ACCENT_HOVER};
            }}
            #ActionSecondaryBtn {{
                background-color: {c.BG_CARD};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            #ActionSecondaryBtn:hover {{
                background-color: {c.BG_HOVER};
                border-color: {c.TEXT_MUTED};
            }}
        """)


class MemoryCardWidget(QFrame):
    """Rich interactive card displaying a stored memory with category pill, status switch, and actions."""

    edit_clicked = Signal(dict)
    toggle_clicked = Signal(dict)
    delete_clicked = Signal(dict)

    def __init__(self, memory: dict, parent=None):
        super().__init__(parent)
        self.memory = memory
        self.setObjectName("MemoryCard")
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # ─── Row 1: Category Badge, Status Pill, and Actions ───
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Category Badge
        cat = self.memory.get("category", "general").lower()
        cat_info = CATEGORY_CONFIG.get(cat, CATEGORY_CONFIG["general"])
        
        self.cat_badge = QLabel(cat_info["label"])
        self.cat_badge.setObjectName("CatBadge")
        self.cat_badge.setStyleSheet(f"""
            QLabel#CatBadge {{
                background-color: {cat_info['bg']};
                color: {cat_info['color']};
                border: 1px solid {cat_info['border']};
                border-radius: 10px;
                padding: 2px 9px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        top_row.addWidget(self.cat_badge)

        # Vector Index Dot
        has_embedding = self.memory.get("embedding") is not None
        self.embed_dot = QLabel("● Vector Indexed" if has_embedding else "○ Lexical")
        self.embed_dot.setObjectName("EmbedStatusDot")
        top_row.addWidget(self.embed_dot)

        top_row.addStretch(1)

        # Active Toggle Pill Button
        is_enabled = bool(self.memory.get("is_enabled", 1))
        self.toggle_btn = QPushButton("✓ Active" if is_enabled else "○ Paused")
        self.toggle_btn.setObjectName("CardActiveToggle")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(lambda: self.toggle_clicked.emit(self.memory))
        top_row.addWidget(self.toggle_btn)

        # Edit Action Button
        edit_btn = QPushButton("✏️ Edit")
        edit_btn.setObjectName("CardActionBtn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.memory))
        top_row.addWidget(edit_btn)

        # Delete Action Button
        del_btn = QPushButton("🗑 Delete")
        del_btn.setObjectName("CardDeleteBtn")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.memory))
        top_row.addWidget(del_btn)

        layout.addLayout(top_row)

        # ─── Row 2: Memory Content ───
        content_text = self.memory.get("content", "")
        self.content_lbl = QLabel(content_text)
        self.content_lbl.setObjectName("MemoryCardContent")
        self.content_lbl.setWordWrap(True)
        self.content_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.content_lbl)

        # ─── Row 3: Metadata Footer ───
        created_at = self.memory.get("created_at", "")
        if created_at and " " in created_at:
            created_at = created_at.split(" ")[0]
        meta_text = f"Added {created_at}" if created_at else "Explicit Memory"
        source = self.memory.get("source", "user")
        if source:
            meta_text += f" • Source: {source.capitalize()}"

        meta_lbl = QLabel(meta_text)
        meta_lbl.setObjectName("MemoryCardMeta")
        layout.addWidget(meta_lbl)

    def apply_theme(self):
        c = ThemeManager.instance().colors
        is_enabled = bool(self.memory.get("is_enabled", 1))
        has_embedding = self.memory.get("embedding") is not None

        embed_color = "#20C997" if has_embedding else c.TEXT_MUTED

        active_bg = "rgba(53, 199, 89, 0.12)" if is_enabled else "rgba(139, 148, 158, 0.12)"
        active_color = "#35C759" if is_enabled else c.TEXT_MUTED
        active_border = "rgba(53, 199, 89, 0.3)" if is_enabled else c.BORDER

        content_color = c.TEXT_PRIMARY if is_enabled else c.TEXT_SECONDARY

        self.setStyleSheet(f"""
            QFrame#MemoryCard {{
                background-color: {c.BG_CARD};
                border: 1px solid {c.BORDER};
                border-radius: 9px;
            }}
            QFrame#MemoryCard:hover {{
                border-color: {c.TEXT_MUTED};
            }}
            #EmbedStatusDot {{
                color: {embed_color};
                font-size: 11px;
                font-weight: 500;
            }}
            #MemoryCardContent {{
                color: {content_color};
                font-size: 13px;
                font-weight: 500;
                line-height: 1.4;
            }}
            #MemoryCardMeta {{
                color: {c.TEXT_MUTED};
                font-size: 11px;
            }}
            #CardActiveToggle {{
                background-color: {active_bg};
                color: {active_color};
                border: 1px solid {active_border};
                border-radius: 11px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            #CardActiveToggle:hover {{
                border-color: {active_color};
            }}
            #CardActionBtn {{
                background-color: transparent;
                color: {c.TEXT_SECONDARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11px;
            }}
            #CardActionBtn:hover {{
                background-color: {c.BG_HOVER};
                color: {c.TEXT_PRIMARY};
            }}
            #CardDeleteBtn {{
                background-color: transparent;
                color: {c.TEXT_MUTED};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11px;
            }}
            #CardDeleteBtn:hover {{
                background-color: rgba(255, 85, 85, 0.12);
                color: #FF5555;
                border-color: rgba(255, 85, 85, 0.35);
            }}
        """)


class MemoryDialog(QDialog):
    """Production-grade interface for viewing, filtering, and managing personalized memories."""

    def __init__(self, memory_manager: MemoryManager, parent=None):
        super().__init__(parent)
        self.memory_manager = memory_manager
        self.setWindowTitle("Memory Engine")
        self.resize(700, 620)
        self.setMinimumSize(580, 480)

        self._filter_text = ""
        self._selected_category = None  # None means 'All'

        self.init_ui()
        self.apply_theme()
        self.load_memories()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # ─── 1. HEADER ───
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_box = QLabel("🧠")
        icon_box.setObjectName("HeaderIconBadge")
        icon_box.setFixedSize(40, 40)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_box)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_lbl = QLabel("Memory Engine")
        title_lbl.setObjectName("HeaderTitle")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 700;")
        title_layout.addWidget(title_lbl)

        subtitle_lbl = QLabel("Personalized facts, preferences, and background recalled across chat sessions.")
        subtitle_lbl.setObjectName("HeaderSubtitle")
        subtitle_lbl.setStyleSheet("font-size: 12px;")
        title_layout.addWidget(subtitle_lbl)

        header_layout.addLayout(title_layout, 1)

        self.stats_badge = QLabel("0 Memories • 0 Active")
        self.stats_badge.setObjectName("StatsBadge")
        header_layout.addWidget(self.stats_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        main_layout.addLayout(header_layout)

        # ─── 2. GLOBAL TOGGLE & ENGINE CARD ───
        config_card = QFrame()
        config_card.setObjectName("ConfigCard")
        config_layout = QHBoxLayout(config_card)
        config_layout.setContentsMargins(14, 12, 14, 12)
        config_layout.setSpacing(12)

        toggle_col = QVBoxLayout()
        toggle_col.setSpacing(2)
        self.global_toggle = QCheckBox("Enable Memory Engine")
        self.global_toggle.setObjectName("GlobalToggle")
        self.global_toggle.setChecked(self.memory_manager.app_state.get("memory_enabled", True))
        self.global_toggle.toggled.connect(self._on_global_toggle)
        toggle_col.addWidget(self.global_toggle)

        toggle_desc = QLabel("When enabled, rootChat automatically recalls relevant memories to personalize its answers.")
        toggle_desc.setObjectName("ToggleDesc")
        toggle_desc.setWordWrap(True)
        toggle_col.addWidget(toggle_desc)

        config_layout.addLayout(toggle_col, 1)

        # Engine Badge
        has_embed = self.memory_manager.embedding_provider is not None
        badge_text = "⚡ Vector Semantic Recall" if has_embed else "⚡ Lexical Matching"
        self.engine_badge = QLabel(badge_text)
        self.engine_badge.setObjectName("EngineBadge")
        config_layout.addWidget(self.engine_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        main_layout.addWidget(config_card)

        # ─── 3. SEARCH & CATEGORY CHIPS ───
        search_chip_layout = QVBoxLayout()
        search_chip_layout.setSpacing(8)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setObjectName("MemorySearchInput")
        self.search_input.setPlaceholderText("🔍  Search memories by keyword...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedHeight(34)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_chip_layout.addWidget(self.search_input)

        # Category Filter Chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)

        self.chip_buttons = {}
        chip_defs = [
            ("all", "All"),
            ("preference", "🎨 Preferences"),
            ("work", "💼 Work & Skills"),
            ("personal", "👤 Personal"),
            ("general", "📌 General"),
        ]

        for cat_key, cat_label in chip_defs:
            btn = QPushButton(cat_label)
            btn.setObjectName("FilterChip")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if cat_key == "all":
                btn.setChecked(True)
            btn.clicked.connect(lambda _, k=cat_key: self._on_chip_clicked(k))
            self.chip_buttons[cat_key] = btn
            chips_layout.addWidget(btn)

        chips_layout.addStretch(1)
        search_chip_layout.addLayout(chips_layout)

        main_layout.addLayout(search_chip_layout)

        # ─── 4. MEMORY LIST & EMPTY STATE STACK ───
        self.content_stack = QStackedWidget()

        # Page 0: Cards List
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("MemoryListWidget")
        self.list_widget.setSpacing(8)
        self.content_stack.addWidget(self.list_widget)

        # Page 1: Empty State Card
        empty_card = QFrame()
        empty_card.setObjectName("EmptyStateCard")
        empty_layout = QVBoxLayout(empty_card)
        empty_layout.setContentsMargins(32, 40, 32, 40)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_icon = QLabel("🧠")
        empty_icon.setStyleSheet("font-size: 38px;")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)

        empty_title = QLabel("No Memories Stored Yet")
        empty_title.setObjectName("EmptyTitle")
        empty_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)

        empty_desc = QLabel(
            "Tell rootChat 'Remember that I use Python for backend' in any chat, "
            "or click below to add your personal preferences and project facts manually."
        )
        empty_desc.setObjectName("EmptyDesc")
        empty_desc.setStyleSheet("font-size: 12px;")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_desc.setWordWrap(True)
        empty_layout.addWidget(empty_desc)

        empty_add_btn = QPushButton("+ Add Your First Memory")
        empty_add_btn.setObjectName("EmptyAddBtn")
        empty_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        empty_add_btn.clicked.connect(self._add_memory)
        empty_layout.addWidget(empty_add_btn, 0, Qt.AlignmentFlag.AlignCenter)

        self.content_stack.addWidget(empty_card)
        main_layout.addWidget(self.content_stack, 1)

        # ─── 5. BOTTOM ACTION TOOLBAR ───
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        add_btn = QPushButton("+ Add Memory")
        add_btn.setObjectName("ActionPrimaryBtn")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setFixedHeight(34)
        add_btn.clicked.connect(self._add_memory)
        btn_layout.addWidget(add_btn)

        clear_btn = QPushButton("Clear All Memories")
        clear_btn.setObjectName("ActionDangerBtn")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setFixedHeight(34)
        clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch(1)

        done_btn = QPushButton("Done")
        done_btn.setObjectName("ActionSecondaryBtn")
        done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        done_btn.setFixedHeight(34)
        done_btn.clicked.connect(self.accept)
        btn_layout.addWidget(done_btn)

        main_layout.addLayout(btn_layout)

    def apply_theme(self):
        c = ThemeManager.instance().colors
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c.BG_PRIMARY};
                color: {c.TEXT_PRIMARY};
            }}
            #HeaderIconBadge {{
                background-color: {c.ACCENT_MUTED};
                border: 1px solid {c.ACCENT};
                border-radius: 8px;
                font-size: 20px;
            }}
            #HeaderTitle {{
                color: {c.TEXT_PRIMARY};
            }}
            #HeaderSubtitle {{
                color: {c.TEXT_MUTED};
            }}
            #StatsBadge {{
                background-color: {c.BG_INPUT};
                color: {c.ACCENT};
                border: 1px solid {c.BORDER};
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            #ConfigCard {{
                background-color: {c.BG_SECONDARY};
                border: 1px solid {c.BORDER};
                border-radius: 8px;
            }}
            #GlobalToggle {{
                font-size: 13px;
                font-weight: 600;
                color: {c.TEXT_PRIMARY};
                spacing: 8px;
            }}
            #ToggleDesc {{
                font-size: 11px;
                color: {c.TEXT_MUTED};
            }}
            #EngineBadge {{
                background-color: {c.ACCENT_MUTED};
                color: {c.TEXT_ACCENT};
                border: 1px solid rgba(255, 95, 21, 0.3);
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            #MemorySearchInput {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
            }}
            #MemorySearchInput:focus {{
                border-color: {c.ACCENT};
            }}
            QPushButton#FilterChip {{
                background-color: {c.BG_CARD};
                color: {c.TEXT_SECONDARY};
                border: 1px solid {c.BORDER};
                border-radius: 14px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#FilterChip:hover {{
                background-color: {c.BG_HOVER};
                color: {c.TEXT_PRIMARY};
            }}
            QPushButton#FilterChip:checked {{
                background-color: {c.ACCENT};
                color: #FFFFFF;
                border-color: {c.ACCENT};
            }}
            QListWidget#MemoryListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#MemoryListWidget::item {{
                background: transparent;
                border: none;
                padding: 0px;
            }}
            QListWidget#MemoryListWidget::item:selected {{
                background: transparent;
            }}
            #EmptyStateCard {{
                background-color: {c.BG_SECONDARY};
                border: 1px dashed {c.BORDER};
                border-radius: 10px;
            }}
            #EmptyTitle {{
                color: {c.TEXT_PRIMARY};
            }}
            #EmptyDesc {{
                color: {c.TEXT_MUTED};
            }}
            #EmptyAddBtn {{
                background-color: {c.ACCENT};
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                border-radius: 6px;
                padding: 8px 18px;
                border: none;
            }}
            #EmptyAddBtn:hover {{
                background-color: {c.ACCENT_HOVER};
            }}
            #ActionPrimaryBtn {{
                background-color: {c.ACCENT};
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                border-radius: 6px;
                padding: 6px 16px;
                border: none;
            }}
            #ActionPrimaryBtn:hover {{
                background-color: {c.ACCENT_HOVER};
            }}
            #ActionSecondaryBtn {{
                background-color: {c.BG_CARD};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            #ActionSecondaryBtn:hover {{
                background-color: {c.BG_HOVER};
                border-color: {c.TEXT_MUTED};
            }}
            #ActionDangerBtn {{
                background-color: {c.BG_CARD};
                color: {c.TEXT_SECONDARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            #ActionDangerBtn:hover {{
                background-color: rgba(255, 85, 85, 0.15);
                color: #FF5555;
                border-color: rgba(255, 85, 85, 0.4);
            }}
        """)

    def _on_theme_changed(self):
        self.apply_theme()
        # Re-render cards to pick up new colors
        self.load_memories()

    def load_memories(self):
        """Loads memories from repository, applies category & search filters, and populates UI."""
        self.list_widget.clear()
        
        all_memories = self.memory_manager.repo.list_memories()
        stats = self.memory_manager.repo.get_stats()
        
        total = stats.get("total", len(all_memories))
        active = stats.get("active", sum(1 for m in all_memories if m.get("is_enabled", 1)))
        
        mem_str = "1 Memory" if total == 1 else f"{total} Memories"
        self.stats_badge.setText(f"{mem_str} • {active} Active")

        # Update chip counts
        by_cat = stats.get("by_category", {})
        for cat_key, btn in self.chip_buttons.items():
            if cat_key == "all":
                btn.setText(f"All ({total})")
            else:
                cat_count = by_cat.get(cat_key, 0)
                label_base = {
                    "preference": "🎨 Preferences",
                    "work": "💼 Work",
                    "personal": "👤 Personal",
                    "general": "📌 General",
                }.get(cat_key, cat_key.capitalize())
                btn.setText(f"{label_base} ({cat_count})")

        if not all_memories:
            self.content_stack.setCurrentIndex(1)  # Empty state
            return

        self.content_stack.setCurrentIndex(0)  # List state

        q = self._filter_text.strip().lower()
        selected_cat = self._selected_category

        filtered = []
        for mem in all_memories:
            cat_match = (selected_cat is None) or (mem.get("category") == selected_cat)
            search_match = (not q) or (q in mem.get("content", "").lower()) or (q in mem.get("category", "").lower())
            if cat_match and search_match:
                filtered.append(mem)

        for mem in filtered:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, mem)

            card_widget = MemoryCardWidget(mem)
            card_widget.edit_clicked.connect(self._edit_memory_card)
            card_widget.toggle_clicked.connect(self._toggle_memory_card)
            card_widget.delete_clicked.connect(self._delete_memory_card)

            # Measure height dynamically
            layout_hint = card_widget.sizeHint()
            item.setSizeHint(QSize(0, max(85, layout_hint.height())))

            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card_widget)

    def _on_chip_clicked(self, category_key: str):
        for k, btn in self.chip_buttons.items():
            btn.setChecked(k == category_key)
            
        self._selected_category = None if category_key == "all" else category_key
        self.load_memories()

    def _on_search_changed(self, text: str):
        self._filter_text = text
        self.load_memories()

    def _on_global_toggle(self, checked: bool):
        self.memory_manager.app_state.set("memory_enabled", checked)
        logger.info("Memory Engine global toggle set to: %s", checked)

    def _add_memory(self):
        modal = MemoryEditorModal(parent=self)
        if modal.exec() == QDialog.DialogCode.Accepted:
            data = modal.get_data()
            success = self.memory_manager.create_memory(
                data["content"],
                category=data["category"],
                source="user"
            )
            if not success:
                QMessageBox.information(self, "Memory Exists", "This memory is already saved in your rootChat library.")
            self.load_memories()

    def _edit_memory_card(self, mem: dict):
        modal = MemoryEditorModal(parent=self, memory=mem)
        if modal.exec() == QDialog.DialogCode.Accepted:
            data = modal.get_data()
            self.memory_manager.update_memory(
                mem["id"],
                content=data["content"],
                category=data["category"],
                is_enabled=data["is_enabled"]
            )
            self.load_memories()

    def _toggle_memory_card(self, mem: dict):
        new_state = not bool(mem.get("is_enabled", 1))
        self.memory_manager.update_memory(mem["id"], is_enabled=new_state)
        self.load_memories()

    def _delete_memory_card(self, mem: dict):
        confirm = QMessageBox.question(
            self,
            "Delete Memory",
            f"Are you sure you want to delete this memory?\n\n\"{mem.get('content')}\"",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.memory_manager.repo.delete_memory(mem["id"])
            self.load_memories()

    def _clear_all(self):
        confirm = QMessageBox.question(
            self,
            "Clear All Memories",
            "Are you sure you want to clear all stored memories? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.memory_manager.repo.clear_all_memories()
            self.load_memories()
