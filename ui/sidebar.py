import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                               QListWidget, QListWidgetItem, QMenu, QInputDialog, QMessageBox, QLineEdit, QSizePolicy, QFrame)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QPixmap
from datetime import datetime, timedelta
from core.chat_manager import ChatManager
from ui.memory_dialog import MemoryDialog
from utils.resource_path import get_resource_path


class SidebarFeatureRow(QFrame):
    """
    Modern sidebar feature row with:
    - An icon label (e.g. 🧠, 📚, 📦)
    - A title label (triggers on_manage callback if present)
    - An inline ON/OFF toggle pill button (triggers on_toggle callback)
    - Seamless support for expanded and collapsed sidebar modes
    """
    def __init__(self, icon: str, title: str, on_toggle=None, on_manage=None, initial_active=False, parent=None):
        super().__init__(parent)
        self.setObjectName("ArchiveRow")  # Reuses theme styling
        self.on_toggle = on_toggle
        self.on_manage = on_manage
        self._active = bool(initial_active)
        self._icon_char = icon
        self._title_str = title
        self._is_collapsed = False
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(8)

        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setObjectName("ArchiveIcon")
        self.layout.addWidget(self.icon_lbl)

        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("ArchiveTitle")
        self.layout.addWidget(self.title_lbl)

        self.layout.addStretch()

        self.toggle_btn = QPushButton("ON" if self._active else "OFF")
        self.toggle_btn.setObjectName("ArchiveToggleBtn")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setFixedSize(46, 22)
        self.toggle_btn.clicked.connect(self._handle_toggle_clicked)
        self.layout.addWidget(self.toggle_btn)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_active(self._active)

    def _handle_toggle_clicked(self):
        if self.on_toggle:
            self.on_toggle()

    def mousePressEvent(self, event):
        # Click on row body
        if self.on_manage:
            self.on_manage()
        elif self.on_toggle:
            self.on_toggle()

    def set_active(self, active: bool):
        self._active = bool(active)
        self.toggle_btn.setText("ON" if self._active else "OFF")
        self.toggle_btn.setProperty("active", "true" if self._active else "false")
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)

    def is_active(self) -> bool:
        return self._active

    def set_collapsed(self, collapsed: bool):
        self._is_collapsed = collapsed
        if collapsed:
            self.title_lbl.hide()
            self.toggle_btn.hide()
            self.layout.setContentsMargins(0, 0, 0, 0)
            self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.icon_lbl.setStyleSheet("font-size: 18px;")
            self.setFixedHeight(36)
            self.setToolTip(f"{self._title_str} ({'ON' if self._active else 'OFF'})")
        else:
            self.title_lbl.show()
            self.toggle_btn.show()
            self.layout.setContentsMargins(8, 4, 8, 4)
            self.layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.icon_lbl.setStyleSheet("")
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.setToolTip("")

    def setText(self, text: str):
        # Backward compatibility if setText is called directly
        if "ON" in text:
            self.set_active(True)
        elif "OFF" in text:
            self.set_active(False)

    def text(self) -> str:
        if self._is_collapsed:
            return self._icon_char
        return self._title_str


# Backward compatibility alias
ArchiveRowWidget = SidebarFeatureRow


class Sidebar(QWidget):
    settings_requested = Signal()
    sidebar_toggled = Signal(bool)
    
    def __init__(self, chat_manager: ChatManager, document_manager=None):
        super().__init__()
        self.chat_manager = chat_manager
        self.document_manager = document_manager
        self.setObjectName("Sidebar")
        self.setFixedWidth(260)
        self.is_collapsed = False
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 14, 12, 14)
        self.main_layout.setSpacing(8)

        # Header Row (Title + Collapse/Expand Toggle)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        self.brand_icon = QLabel()
        logo_path = get_resource_path("resources/icons/rootChat_32.png")
        if not os.path.exists(logo_path):
            logo_path = get_resource_path("resources/icons/rootChat.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.brand_icon.setPixmap(pix)
            self.brand_icon.setFixedSize(22, 22)
            header_row.addWidget(self.brand_icon, 0, Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel("rootChat")
        self.title_label.setStyleSheet("font-weight: 700; font-size: 17px; padding: 2px 2px;")
        header_row.addWidget(self.title_label, 1, Qt.AlignmentFlag.AlignVCenter)

        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setObjectName("SidebarToggleBtn")
        self.toggle_btn.setToolTip("Collapse sidebar (Ctrl+B)")
        self.toggle_btn.setFixedSize(32, 32)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet(
            "QPushButton#SidebarToggleBtn { "
            "  background: transparent; "
            "  border: none; "
            "  border-radius: 6px; "
            "  font-size: 16px; "
            "  color: #888888; "
            "} "
            "QPushButton#SidebarToggleBtn:hover { "
            "  background-color: rgba(255, 255, 255, 0.08); "
            "  color: #FFFFFF; "
            "}"
        )
        self.toggle_btn.clicked.connect(self.toggle_collapse)
        header_row.addWidget(self.toggle_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addLayout(header_row)

        # New Chat Button
        self.new_chat_btn = QPushButton("＋  New Chat")
        self.new_chat_btn.setObjectName("NewChatBtn")
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_btn.clicked.connect(self._on_new_chat)
        self.main_layout.addWidget(self.new_chat_btn)

        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("SearchInput")
        self.search_bar.setPlaceholderText("Search chats...")
        self.search_bar.textChanged.connect(self.load_conversations)
        self.main_layout.addWidget(self.search_bar)

        # Conversations List
        self.chat_list = QListWidget()
        self.chat_list.setObjectName("ChatList")
        self.chat_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_list.itemClicked.connect(self._on_chat_selected)
        
        # Context menu for rename/delete/pin/archive
        self.chat_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chat_list.customContextMenuRequested.connect(self._show_context_menu)
        
        self.main_layout.addWidget(self.chat_list, 1)

        # Middle Spacer (active in collapsed mode to anchor top and bottom sections)
        self.middle_spacer = QWidget()
        self.middle_spacer.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.middle_spacer.setVisible(False)
        self.main_layout.addWidget(self.middle_spacer)

        # Bottom Actions
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(0, 4, 0, 0)
        bottom_layout.setSpacing(4)

        # 1. Memory Row with inline ON/OFF toggle
        mem_enabled = True
        if hasattr(self.chat_manager, "app_state") and self.chat_manager.app_state:
            mem_enabled = self.chat_manager.app_state.get("memory_enabled", True)
        self.memory_row = SidebarFeatureRow(
            icon="🧠",
            title="Memory",
            on_toggle=self._toggle_memory,
            on_manage=self._open_memory_dialog,
            initial_active=mem_enabled
        )
        self.memory_btn = self.memory_row
        bottom_layout.addWidget(self.memory_row)
        
        # 2. Knowledge Base Row with inline ON/OFF toggle
        k_active = False
        if hasattr(self.chat_manager, "app_state") and self.chat_manager.app_state:
            k_active = (self.chat_manager.app_state.get("active_knowledge_mode", "none") != "none")
        self.knowledge_row = SidebarFeatureRow(
            icon="📚",
            title="Knowledge Base",
            on_toggle=self._toggle_knowledge,
            on_manage=self._open_knowledge_dialog,
            initial_active=k_active
        )
        self.knowledge_btn = self.knowledge_row
        bottom_layout.addWidget(self.knowledge_row)

        # 3. Archive View Row with inline ON/OFF toggle (Moved up!)
        self.showing_archived = False
        self.archive_row = SidebarFeatureRow(
            icon="📦",
            title="Archive View",
            on_toggle=self._toggle_archived_view,
            on_manage=None,
            initial_active=False
        )
        self.archive_btn = self.archive_row
        bottom_layout.addWidget(self.archive_row)

        # 4. Settings Button (Placed LAST at the bottom)
        self.settings_btn = QPushButton("⚙  Settings")
        self.settings_btn.setObjectName("SidebarActionBtn")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        bottom_layout.addWidget(self.settings_btn)

        self.main_layout.addLayout(bottom_layout)

        # Connect live state listeners
        if hasattr(self.chat_manager, "app_state") and self.chat_manager.app_state:
            self.chat_manager.app_state.state_changed.connect(self._on_app_state_changed)
        self.chat_manager.knowledge_mode_changed.connect(self._on_knowledge_mode_changed)

        self.chat_manager.conversation_created.connect(self.load_conversations)
        self.load_conversations()

    def toggle_collapse(self):
        """Toggles sidebar between expanded (260px) and collapsed (56px) modes."""
        self.set_collapsed(not self.is_collapsed)

    def set_collapsed(self, collapsed: bool):
        """Sets the sidebar collapsed state."""
        self.is_collapsed = collapsed
        
        if self.is_collapsed:
            self.setFixedWidth(56)
            self.main_layout.setContentsMargins(6, 14, 6, 14)
            self.title_label.hide()
            if hasattr(self, "brand_icon"):
                self.brand_icon.hide()
            self.toggle_btn.setToolTip("Expand sidebar (Ctrl+B)")
            self.toggle_btn.setStyleSheet(
                "QPushButton#SidebarToggleBtn { "
                "  background: transparent; "
                "  border: none; "
                "  border-radius: 6px; "
                "  font-size: 18px; "
                "  color: #A6ACB8; "
                "  padding: 0; "
                "} "
                "QPushButton#SidebarToggleBtn:hover { "
                "  background-color: rgba(255, 255, 255, 0.08); "
                "  color: #FFFFFF; "
                "}"
            )
            
            self.new_chat_btn.setText("＋")
            self.new_chat_btn.setToolTip("New Chat (Ctrl+N)")
            self.new_chat_btn.setFixedHeight(38)
            self.new_chat_btn.setStyleSheet(
                "QPushButton#NewChatBtn { "
                "  padding: 0; "
                "  text-align: center; "
                "  font-size: 20px; "
                "  font-weight: bold; "
                "  border-radius: 8px; "
                "}"
            )
            
            self.search_bar.hide()
            self.chat_list.hide()
            self.middle_spacer.show()
            
            action_style = (
                "QPushButton#SidebarActionBtn { "
                "  padding: 0; "
                "  text-align: center; "
                "  font-size: 18px; "
                "  border-radius: 8px; "
                "}"
            )
            
            self.memory_row.set_collapsed(True)
            self.knowledge_row.set_collapsed(True)
            self.archive_row.set_collapsed(True)
            self.archive_row.show()
            
            self.settings_btn.setText("⚙")
            self.settings_btn.setToolTip("Settings (Ctrl+,)")
            self.settings_btn.setFixedHeight(36)
            self.settings_btn.setStyleSheet(action_style)
        else:
            self.setFixedWidth(260)
            self.main_layout.setContentsMargins(12, 14, 12, 14)
            self.title_label.show()
            if hasattr(self, "brand_icon"):
                self.brand_icon.show()
            self.toggle_btn.setToolTip("Collapse sidebar (Ctrl+B)")
            self.toggle_btn.setStyleSheet(
                "QPushButton#SidebarToggleBtn { "
                "  background: transparent; "
                "  border: none; "
                "  border-radius: 6px; "
                "  font-size: 16px; "
                "  color: #888888; "
                "} "
                "QPushButton#SidebarToggleBtn:hover { "
                "  background-color: rgba(255, 255, 255, 0.08); "
                "  color: #FFFFFF; "
                "}"
            )
            
            self.new_chat_btn.setText("＋  New Chat")
            self.new_chat_btn.setToolTip("")
            self.new_chat_btn.setMinimumHeight(0)
            self.new_chat_btn.setMaximumHeight(16777215)
            self.new_chat_btn.setStyleSheet("")
            
            self.search_bar.show()
            self.chat_list.show()
            self.middle_spacer.hide()
            
            self.memory_row.set_collapsed(False)
            self.knowledge_row.set_collapsed(False)
            self.archive_row.set_collapsed(False)
            self.archive_row.set_active(self.showing_archived)
            self.archive_row.show()

            self.settings_btn.setText("⚙  Settings")
            self.settings_btn.setToolTip("")
            self.settings_btn.setMinimumHeight(0)
            self.settings_btn.setMaximumHeight(16777215)
            self.settings_btn.setStyleSheet("")

        self.sidebar_toggled.emit(self.is_collapsed)
        
    def load_conversations(self):
        self.chat_list.clear()
        search_term = self.search_bar.text().strip()
        
        if search_term:
            convs = self.chat_manager.conv_repo.search_conversations(search_term, include_archived=self.showing_archived)
        else:
            convs = self.chat_manager.conv_repo.list_conversations(include_archived=self.showing_archived)

        # Group conversations by date
        groups = self._group_by_date(convs)
        
        active_id = None
        if hasattr(self.chat_manager, "app_state") and self.chat_manager.app_state:
            active_id = self.chat_manager.app_state.get("active_conversation_id")

        active_item_to_select = None

        for group_name, group_convs in groups:
            if not group_convs:
                continue
            # Add section header
            header_item = QListWidgetItem(group_name)
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            header_item.setData(Qt.ItemDataRole.UserRole, None)
            font = header_item.font()
            font.setPixelSize(11)
            font.setWeight(QFont.Weight.Bold)
            header_item.setFont(font)
            header_item.setSizeHint(QSize(0, 24))
            self.chat_list.addItem(header_item)
            
            for conv in group_convs:
                title = conv["title"]
                if conv.get("is_pinned"):
                    title = f"📌 {title}"
                elif conv.get("is_archived"):
                    title = f"📦 {title}"
                    
                item = QListWidgetItem(f"  {title}")
                item.setData(Qt.ItemDataRole.UserRole, conv)
                item.setToolTip(title)
                font = item.font()
                font.setPixelSize(13)
                font.setWeight(QFont.Weight.Normal)
                item.setFont(font)
                item.setSizeHint(QSize(0, 32))
                self.chat_list.addItem(item)

                if active_id is not None and conv.get("id") == active_id:
                    active_item_to_select = item

        if active_item_to_select:
            self.chat_list.setCurrentItem(active_item_to_select)
    
    def _group_by_date(self, convs):
        """Group conversations into Pinned, Today, Yesterday, Previous 7 Days, Older."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        
        pinned = []
        today = []
        yesterday = []
        this_week = []
        older = []
        archived = []
        
        for conv in convs:
            if conv.get("is_archived"):
                archived.append(conv)
                continue
            if conv.get("is_pinned"):
                pinned.append(conv)
                continue
                
            # Parse updated_at
            updated = conv.get("updated_at", "")
            try:
                dt = datetime.fromisoformat(updated)
            except (ValueError, TypeError):
                older.append(conv)
                continue
            
            if dt >= today_start:
                today.append(conv)
            elif dt >= yesterday_start:
                yesterday.append(conv)
            elif dt >= week_start:
                this_week.append(conv)
            else:
                older.append(conv)
        
        groups = []
        if pinned:
            groups.append(("PINNED", pinned))
        if today:
            groups.append(("TODAY", today))
        if yesterday:
            groups.append(("YESTERDAY", yesterday))
        if this_week:
            groups.append(("THIS WEEK", this_week))
        if older:
            groups.append(("OLDER", older))
        if archived:
            groups.append(("ARCHIVED", archived))
        
        return groups
            
    def _toggle_archived_view(self):
        self.showing_archived = not self.showing_archived
        self.archive_btn.set_active(self.showing_archived)
        self.load_conversations()

    def _toggle_memory(self):
        if hasattr(self.chat_manager, "app_state") and self.chat_manager.app_state:
            curr = self.chat_manager.app_state.get("memory_enabled", True)
            new_val = not curr
            self.chat_manager.app_state.set("memory_enabled", new_val)
            self.memory_row.set_active(new_val)

    def _toggle_knowledge(self):
        if hasattr(self.chat_manager, "app_state") and self.chat_manager.app_state:
            curr_mode = self.chat_manager.app_state.get("active_knowledge_mode", "none")
            conv_id = self.chat_manager.app_state.get("active_conversation_id")
            new_mode = "none" if curr_mode != "none" else "all"
            self.chat_manager.set_conversation_knowledge(conv_id, new_mode, [])
            self.knowledge_row.set_active(new_mode != "none")

    def _on_app_state_changed(self, key: str, value):
        if key == "memory_enabled":
            self.memory_row.set_active(bool(value))
        elif key == "active_knowledge_mode":
            self.knowledge_row.set_active(value != "none")

    def _on_knowledge_mode_changed(self, mode: str, doc_ids: list):
        self.knowledge_row.set_active(mode != "none")
        
    def _on_new_chat(self):
        self.chat_manager.start_new_conversation()
        self.chat_list.clearSelection()
        
    def _on_chat_selected(self, item: QListWidgetItem):
        conv = item.data(Qt.ItemDataRole.UserRole)
        if conv is None:
            return  # Section header clicked
        self.chat_manager.load_conversation(conv["id"])
        
    def select_conversation(self, conv_id: int):
        """Visually highlights the item corresponding to conv_id in chat_list."""
        if conv_id is None:
            self.chat_list.setCurrentItem(None)
            self.chat_list.clearSelection()
            return
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            conv = item.data(Qt.ItemDataRole.UserRole)
            if conv and conv.get("id") == conv_id:
                self.chat_list.setCurrentItem(item)
                return
        self.chat_list.setCurrentItem(None)
        self.chat_list.clearSelection()

    def _show_context_menu(self, position):
        item = self.chat_list.itemAt(position)
        if not item:
            return
            
        conv = item.data(Qt.ItemDataRole.UserRole)
        if conv is None:
            return  # Section header
            
        # Select item under mouse immediately
        self.chat_list.setCurrentItem(item)
            
        conv_id = conv["id"]
        
        menu = QMenu(self)
        
        is_pinned = bool(conv.get("is_pinned"))
        pin_label = "📍  Unpin from Top" if is_pinned else "📌  Pin to Top"
        pin_action = menu.addAction(pin_label)
        
        is_archived = bool(conv.get("is_archived"))
        archive_label = "📥  Restore from Archive" if is_archived else "📦  Archive Chat"
        archive_action = menu.addAction(archive_label)
        
        menu.addSeparator()
        rename_action = menu.addAction("✏️  Rename Chat")
        
        export_menu = menu.addMenu("📤  Export Chat")
        export_md_action = export_menu.addAction("📄  Export as Markdown (.md)")
        export_txt_action = export_menu.addAction("📝  Export as Plain Text (.txt)")
        export_json_action = export_menu.addAction("🏷️  Export as JSON (.json)")
        
        menu.addSeparator()
        delete_action = menu.addAction("🗑️  Delete Chat")
        
        action = menu.exec(self.chat_list.mapToGlobal(position))
        
        if action == pin_action:
            self.chat_manager.conv_repo.update_conversation(conv_id, is_pinned=not is_pinned)
            self.load_conversations()
            
        elif action == archive_action:
            self.chat_manager.conv_repo.update_conversation(conv_id, is_archived=not is_archived)
            self.load_conversations()
            
        elif action == rename_action:
            new_title, ok = QInputDialog.getText(self, "Rename Chat", "Enter new title for conversation:", text=conv["title"])
            if ok and new_title.strip():
                self.chat_manager.conv_repo.update_conversation(conv_id, title=new_title.strip())
                self.load_conversations()
                
        elif action == export_md_action:
            self._export_chat(conv, "markdown")
            
        elif action == export_txt_action:
            self._export_chat(conv, "txt")
            
        elif action == export_json_action:
            self._export_chat(conv, "json")
                
        elif action == delete_action:
            reply = QMessageBox.question(
                self, 
                "Delete Chat", 
                f"Are you sure you want to delete '{conv['title']}'?\nAll messages in this conversation will be permanently removed.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.chat_manager.conv_repo.delete_conversation(conv_id)
                self.load_conversations()
                if self.chat_manager.app_state.get("active_conversation_id") == conv_id:
                    self.chat_manager.start_new_conversation()

    def _export_chat(self, conv: dict, fmt: str):
        from core.export_manager import prompt_and_export
        messages = self.chat_manager.msg_repo.get_messages(conv["id"])
        success, path = prompt_and_export(self, conv, messages, export_format=fmt)
        if success:
            QMessageBox.information(self, "Export Successful", f"Conversation exported successfully to:\n{path}")
                    
    def _open_memory_dialog(self):
        dialog = MemoryDialog(self.chat_manager.memory_manager, self)
        dialog.exec()
        
    def _open_knowledge_dialog(self):
        if self.document_manager:
            from ui.knowledge_panel import KnowledgeDialog
            dialog = KnowledgeDialog(self.document_manager, self)
            dialog.exec()
