"""Memory Selector Widget & Scoping Dialog for rootChat.
Allows top-bar inspection and toggling of personalized memory recall (On/Off)
with 1-click access to the full Memory management dialog.
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, 
    QDialog, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot
from ui.theme.theme_manager import ThemeManager
from ui.knowledge_selector import ScopeOptionTile
from utils.logger import logger


class MemoryScopeDialog(QDialog):
    """Modal dialog allowing users to choose whether memory recall is active for chat."""
    
    memory_applied = Signal(bool)
    manage_memories_requested = Signal()
    
    def __init__(self, memory_manager=None, current_enabled: bool = True, parent=None):
        super().__init__(parent)
        self.memory_manager = memory_manager
        self.current_enabled = bool(current_enabled)
        
        self.setWindowTitle("Conversation Memory Scope")
        self.setFixedWidth(520)
        self.setObjectName("KnowledgeScopeDialog")  # Reuses styling
        
        self.init_ui()
        self._apply_theme()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        
        # ============ 1. HEADER ============
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        header_icon = QLabel("🧠")
        header_icon.setObjectName("HeaderIconBadge")
        header_icon.setFixedSize(38, 38)
        header_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(header_icon)

        header_titles = QVBoxLayout()
        header_titles.setSpacing(2)
        header_titles.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Conversation Memory Scope")
        title.setObjectName("DialogHeaderTitle")
        header_titles.addWidget(title)
        
        subtitle = QLabel("Choose whether rootChat recalls and updates your personal memory in chat:")
        subtitle.setObjectName("DialogHeaderSubtitle")
        subtitle.setWordWrap(True)
        header_titles.addWidget(subtitle)

        header_layout.addLayout(header_titles, 1)
        layout.addLayout(header_layout)
        
        # ============ 2. INTERACTIVE TILES ============
        tiles_container = QVBoxLayout()
        tiles_container.setSpacing(8)

        # Tile 1: Memory Active (On)
        mem_count = 0
        if self.memory_manager and hasattr(self.memory_manager, "repo"):
            stats = self.memory_manager.repo.get_stats()
            mem_count = stats.get("total", 0)
        badge_text = f"{mem_count} Facts" if mem_count > 0 else "Enabled"

        self.tile_on = ScopeOptionTile(
            mode_id="on",
            icon="⚡",
            title="Memory Active",
            desc="Recalls relevant background, skills, and preferences from past chats.",
            badge_text=badge_text
        )
        self.tile_on.clicked.connect(lambda _: self._select_mode(True))
        tiles_container.addWidget(self.tile_on)

        # Tile 2: Memory Off
        self.tile_off = ScopeOptionTile(
            mode_id="off",
            icon="⏸️",
            title="Memory Off",
            desc="Fast standard chat. Does not recall past facts or save new memories.",
            badge_text="Pure Chat"
        )
        self.tile_off.clicked.connect(lambda _: self._select_mode(False))
        tiles_container.addWidget(self.tile_off)

        layout.addLayout(tiles_container)
        
        # Initial selection
        self._select_mode(self.current_enabled)
        
        # ============ 3. BOTTOM ACTIONS ============
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        bottom_row.setContentsMargins(0, 8, 0, 0)
        
        self.manage_btn = QPushButton("⚙ Manage Memories...")
        self.manage_btn.setObjectName("DrawerManageBtn")
        self.manage_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_btn.clicked.connect(self._on_manage_memories)
        bottom_row.addWidget(self.manage_btn)
        
        bottom_row.addStretch(1)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("ActionSecondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(32)
        cancel_btn.clicked.connect(self.reject)
        bottom_row.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply to Chat")
        apply_btn.setObjectName("ActionPrimaryBtn")
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.setFixedHeight(32)
        apply_btn.clicked.connect(self._apply)
        bottom_row.addWidget(apply_btn)
        
        layout.addLayout(bottom_row)

    def _apply_theme(self):
        c = ThemeManager.instance().colors
        ff = ThemeManager.instance().font_family
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c.BG_PRIMARY};
                color: {c.TEXT_PRIMARY};
                font-family: '{ff}';
            }}
            #HeaderIconBadge {{
                background-color: {c.ACCENT_MUTED};
                border: 1px solid rgba(255, 95, 21, 0.35);
                border-radius: 8px;
                font-size: 18px;
            }}
            #DialogHeaderTitle {{
                font-size: 16px;
                font-weight: 700;
                color: {c.TEXT_PRIMARY};
            }}
            #DialogHeaderSubtitle {{
                font-size: 12px;
                color: {c.TEXT_SECONDARY};
            }}
            #DrawerManageBtn {{
                color: {c.TEXT_MUTED};
                background: transparent;
                border: none;
                font-size: 12px;
            }}
            #DrawerManageBtn:hover {{
                color: {c.ACCENT};
            }}
            #ActionPrimaryBtn {{
                background-color: {c.ACCENT};
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                border-radius: 6px;
                padding: 4px 16px;
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
                padding: 4px 14px;
                font-size: 12px;
            }}
            #ActionSecondaryBtn:hover {{
                background-color: {c.BG_HOVER};
            }}
        """)

    def _select_mode(self, enabled: bool):
        self.current_enabled = enabled
        self.tile_on.set_selected(enabled)
        self.tile_off.set_selected(not enabled)

    def _on_manage_memories(self):
        self.accept()
        self.manage_memories_requested.emit()

    def _apply(self):
        self.memory_applied.emit(self.current_enabled)
        self.accept()


class MemorySelector(QWidget):
    """Top bar control displaying active memory recall state with 1-click scoping popover."""
    
    memory_toggled = Signal(bool)
    manage_requested = Signal()
    
    def __init__(self, memory_manager=None, parent=None):
        super().__init__(parent)
        self.memory_manager = memory_manager
        self.is_enabled = True
        self.setObjectName("MemorySelector")
        
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.pill_btn = QPushButton("🧠 Memory: On ▾")
        self.pill_btn.setObjectName("TopBarMemoryBtn")
        self.pill_btn.setFixedHeight(28)
        self.pill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pill_btn.clicked.connect(self._open_scoping_dialog)
        layout.addWidget(self.pill_btn)
        
        self._update_button_appearance()

    def set_memory_manager(self, memory_manager):
        self.memory_manager = memory_manager
        self._update_button_appearance()

    def set_enabled_state(self, enabled: bool):
        """Sets active memory state without emitting change signal."""
        self.is_enabled = bool(enabled)
        self._update_button_appearance()

    def _update_button_appearance(self):
        if self.is_enabled:
            self.pill_btn.setText("🧠 Memory: On ▾")
            self.pill_btn.setToolTip("Active Memory: On (Recalls background and skills)")
            self.pill_btn.setProperty("active", "true")
            self.pill_btn.setStyleSheet("""
                QPushButton#TopBarMemoryBtn {
                    background-color: rgba(255, 95, 21, 0.15);
                    border: 1px solid rgba(255, 95, 21, 0.45);
                    color: #FF5F15;
                    border-radius: 6px;
                    padding: 2px 7px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton#TopBarMemoryBtn:hover {
                    background-color: rgba(255, 95, 21, 0.25);
                    border-color: #FF5F15;
                    color: #FF5F15;
                }
            """)
        else:
            self.pill_btn.setText("🧠 Memory: Off ▾")
            self.pill_btn.setToolTip("Active Memory: Off (Pure chat, no facts recalled or stored)")
            self.pill_btn.setProperty("active", "false")
            self.pill_btn.setStyleSheet("""
                QPushButton#TopBarMemoryBtn {
                    background-color: rgba(128, 134, 144, 0.12);
                    border: 1px solid rgba(128, 134, 144, 0.25);
                    color: #8B949E;
                    border-radius: 6px;
                    padding: 2px 7px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton#TopBarMemoryBtn:hover {
                    background-color: rgba(128, 134, 144, 0.20);
                    border-color: #FF5F15;
                    color: #FF5F15;
                }
            """)
            
        self.pill_btn.style().unpolish(self.pill_btn)
        self.pill_btn.style().polish(self.pill_btn)

    def _open_scoping_dialog(self):
        dialog = MemoryScopeDialog(
            memory_manager=self.memory_manager,
            current_enabled=self.is_enabled,
            parent=self.window()
        )
        dialog.memory_applied.connect(self._on_memory_applied)
        dialog.manage_memories_requested.connect(self.manage_requested.emit)
        dialog.exec()

    @Slot(bool)
    def _on_memory_applied(self, enabled: bool):
        self.is_enabled = enabled
        self._update_button_appearance()
        logger.info("MemorySelector applied enabled=%s", enabled)
        self.memory_toggled.emit(enabled)
