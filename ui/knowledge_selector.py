"""Knowledge Selector Widget & Scoping Dialog for rootChat.
Allows per-conversation selection of RAG knowledge mode (None, All, or Specific documents)
using modern interactive selection tiles, search filtering, and theme integration.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, 
    QDialog, QButtonGroup, QListWidget, QListWidgetItem, 
    QCheckBox, QFrame, QLineEdit, QScrollArea
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal, Slot, QSize
from ui.theme.theme_manager import ThemeManager
from ui.doc_icon_helper import create_document_icon
from utils.logger import logger


class ScopeOptionTile(QFrame):
    """Interactive modern selection tile representing a knowledge scoping mode."""
    clicked = Signal(str)

    def __init__(self, mode_id: str, icon: str, title: str, desc: str, badge_text: str = "", parent=None):
        super().__init__(parent)
        self.mode_id = mode_id
        self.icon = icon
        self.title = title
        self.desc = desc
        self.badge_text = badge_text
        self.is_selected = False
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.init_ui()
        self.update_style()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)
        self.setFixedHeight(64)

        # 1. Icon Container
        self.icon_lbl = QLabel(self.icon)
        self.icon_lbl.setFixedSize(36, 36)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_lbl)

        # 2. Text Info (Title + Subtitle)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        text_layout.setContentsMargins(0, 0, 0, 0)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        self.title_lbl = QLabel(self.title)
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 600;")
        title_row.addWidget(self.title_lbl)

        if self.badge_text:
            self.badge_lbl = QLabel(self.badge_text)
            self.badge_lbl.setObjectName("TileBadge")
            title_row.addWidget(self.badge_lbl)

        title_row.addStretch(1)
        text_layout.addLayout(title_row)

        self.desc_lbl = QLabel(self.desc)
        self.desc_lbl.setStyleSheet("font-size: 11px;")
        self.desc_lbl.setWordWrap(True)
        text_layout.addWidget(self.desc_lbl)

        layout.addLayout(text_layout, 1)

        # 3. Radio Indicator Circle
        self.radio_indicator = QLabel()
        self.radio_indicator.setFixedSize(18, 18)
        self.radio_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.radio_indicator, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.mode_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_style()

    def update_badge(self, text: str):
        self.badge_text = text
        if hasattr(self, "badge_lbl"):
            self.badge_lbl.setText(text)
            self.badge_lbl.setVisible(bool(text))

    def update_style(self):
        c = ThemeManager.instance().colors
        if self.is_selected:
            self.setStyleSheet(f"""
                ScopeOptionTile {{
                    background-color: rgba(255, 95, 21, 0.08);
                    border: 1.5px solid {c.ACCENT};
                    border-radius: 8px;
                }}
            """)
            self.icon_lbl.setStyleSheet(f"""
                background-color: rgba(255, 95, 21, 0.16);
                border: 1px solid rgba(255, 95, 21, 0.40);
                border-radius: 8px;
                font-size: 16px;
            """)
            self.title_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {c.TEXT_PRIMARY};")
            self.desc_lbl.setStyleSheet(f"font-size: 11px; color: {c.TEXT_SECONDARY};")
            if hasattr(self, "badge_lbl"):
                self.badge_lbl.setStyleSheet(f"""
                    background-color: rgba(255, 95, 21, 0.20);
                    color: {c.ACCENT};
                    border: 1px solid rgba(255, 95, 21, 0.40);
                    border-radius: 10px;
                    padding: 1px 8px;
                    font-size: 10px;
                    font-weight: 700;
                """)
            self.radio_indicator.setStyleSheet(f"""
                background-color: {c.ACCENT};
                border: 3px solid {c.BG_CARD};
                border-radius: 9px;
            """)
        else:
            self.setStyleSheet(f"""
                ScopeOptionTile {{
                    background-color: {c.BG_CARD};
                    border: 1px solid {c.BORDER};
                    border-radius: 8px;
                }}
                ScopeOptionTile:hover {{
                    background-color: {c.BG_HOVER};
                    border-color: {c.BORDER_FOCUS};
                }}
            """)
            self.icon_lbl.setStyleSheet(f"""
                background-color: {c.BG_INPUT};
                border: 1px solid {c.BORDER};
                border-radius: 8px;
                font-size: 16px;
            """)
            self.title_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c.TEXT_PRIMARY};")
            self.desc_lbl.setStyleSheet(f"font-size: 11px; color: {c.TEXT_MUTED};")
            if hasattr(self, "badge_lbl"):
                self.badge_lbl.setStyleSheet(f"""
                    background-color: {c.BG_INPUT};
                    color: {c.TEXT_MUTED};
                    border: 1px solid {c.BORDER};
                    border-radius: 10px;
                    padding: 1px 8px;
                    font-size: 10px;
                    font-weight: 600;
                """)
            self.radio_indicator.setStyleSheet("""
                background-color: transparent;
                border: 2px solid rgba(128, 134, 144, 0.45);
                border-radius: 9px;
            """)


class KnowledgeScopeDialog(QDialog):
    """Modal dialog allowing users to choose the knowledge scope for the active conversation."""
    
    knowledge_applied = Signal(str, list)
    manage_library_requested = Signal()
    
    def __init__(self, doc_manager=None, current_mode: str = "none", current_doc_ids: list = None, parent=None):
        super().__init__(parent)
        self.doc_manager = doc_manager
        self.current_mode = current_mode or "none"
        self.current_doc_ids = list(current_doc_ids or [])
        self._filter_text = ""
        
        self.setWindowTitle("Conversation Knowledge Scope")
        self.setFixedWidth(540)
        self.setObjectName("KnowledgeScopeDialog")
        
        self.init_ui()
        self._apply_theme()

        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        
        # ============ 1. HEADER ============
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        header_icon = QLabel("📚")
        header_icon.setObjectName("HeaderIconBadge")
        header_icon.setFixedSize(38, 38)
        header_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(header_icon)

        header_titles = QVBoxLayout()
        header_titles.setSpacing(2)
        header_titles.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Conversation Knowledge Scope")
        title.setObjectName("DialogHeaderTitle")
        header_titles.addWidget(title)
        
        subtitle = QLabel("Choose what local reference documents rootChat references for this chat:")
        subtitle.setObjectName("DialogHeaderSubtitle")
        subtitle.setWordWrap(True)
        header_titles.addWidget(subtitle)

        header_layout.addLayout(header_titles, 1)
        layout.addLayout(header_layout)
        
        # ============ 2. INTERACTIVE TILES ============
        tiles_container = QVBoxLayout()
        tiles_container.setSpacing(8)

        # Tile 1: Pure Chat
        self.tile_none = ScopeOptionTile(
            mode_id="none",
            icon="⚡",
            title="No Knowledge Base",
            desc="Fastest response. Standard chat without document retrieval.",
            badge_text="Pure Chat"
        )
        self.tile_none.clicked.connect(self._select_mode)
        tiles_container.addWidget(self.tile_none)

        # Tile 2: All Documents
        docs_count = len(self.doc_manager.repo.list_documents()) if self.doc_manager else 0
        file_badge = f"{docs_count} Files" if docs_count != 1 else "1 File"
        self.tile_all = ScopeOptionTile(
            mode_id="all",
            icon="🌐",
            title="All Documents",
            desc="Searches across all indexed files in your Knowledge Base.",
            badge_text=file_badge
        )
        self.tile_all.clicked.connect(self._select_mode)
        tiles_container.addWidget(self.tile_all)

        # Tile 3: Specific Documents
        self.tile_specific = ScopeOptionTile(
            mode_id="specific",
            icon="📑",
            title="Specific Documents",
            desc="Query only selected documents for focused, relevant answers.",
            badge_text="Scoped"
        )
        self.tile_specific.clicked.connect(self._select_mode)
        tiles_container.addWidget(self.tile_specific)

        layout.addLayout(tiles_container)
        
        # ============ 3. SPECIFIC DOCUMENTS DRAWER ============
        self.specific_container = QFrame()
        self.specific_container.setObjectName("SpecificDrawer")
        drawer_layout = QVBoxLayout(self.specific_container)
        drawer_layout.setContentsMargins(12, 10, 12, 10)
        drawer_layout.setSpacing(8)

        # Drawer Toolbar
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.filter_edit = QLineEdit()
        self.filter_edit.setObjectName("DrawerFilterInput")
        self.filter_edit.setPlaceholderText("🔍  Filter documents...")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setFixedHeight(30)
        self.filter_edit.textChanged.connect(self._filter_items)
        filter_row.addWidget(self.filter_edit, 1)

        btn_sel_all = QPushButton("Select All")
        btn_sel_all.setObjectName("DrawerChipBtn")
        btn_sel_all.setFixedHeight(28)
        btn_sel_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sel_all.clicked.connect(self._select_all)
        filter_row.addWidget(btn_sel_all)

        btn_clear = QPushButton("Clear")
        btn_clear.setObjectName("DrawerChipBtn")
        btn_clear.setFixedHeight(28)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_all)
        filter_row.addWidget(btn_clear)

        drawer_layout.addLayout(filter_row)

        # Scoped Document Checklist
        self.doc_list = QListWidget()
        self.doc_list.setObjectName("DrawerDocList")
        self.doc_list.setFixedHeight(150)
        self.doc_list.setIconSize(QSize(18, 18))
        self.doc_list.itemChanged.connect(self._on_item_check_changed)
        drawer_layout.addWidget(self.doc_list)

        # Selection Count Footer
        self.sel_count_lbl = QLabel("0 documents selected")
        self.sel_count_lbl.setObjectName("DrawerCountLabel")
        drawer_layout.addWidget(self.sel_count_lbl)

        layout.addWidget(self.specific_container)

        # Populate and configure initial state
        self.populate_documents()
        self._select_mode(self.current_mode)
        
        # ============ 4. FOOTER ============
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        bottom_row.setContentsMargins(0, 4, 0, 0)
        
        self.manage_btn = QPushButton("⚙ Manage Library...")
        self.manage_btn.setObjectName("DrawerManageBtn")
        self.manage_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_btn.clicked.connect(self._on_manage_library)
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
            #SpecificDrawer {{
                background-color: {c.BG_CARD};
                border: 1px solid {c.BORDER};
                border-radius: 8px;
            }}
            #DrawerFilterInput {{
                background-color: {c.BG_INPUT};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                color: {c.TEXT_PRIMARY};
                padding: 4px 10px;
                font-size: 12px;
            }}
            #DrawerFilterInput:focus {{
                border-color: {c.ACCENT};
            }}
            #DrawerChipBtn {{
                background-color: {c.BG_INPUT};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                color: {c.TEXT_SECONDARY};
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 500;
            }}
            #DrawerChipBtn:hover {{
                background-color: {c.BG_HOVER};
                color: {c.TEXT_PRIMARY};
                border-color: {c.BORDER_FOCUS};
            }}
            #DrawerDocList {{
                background-color: {c.BG_PRIMARY};
                border: 1px solid {c.BORDER_SUBTLE};
                border-radius: 6px;
                padding: 4px;
            }}
            #DrawerDocList::item {{
                padding: 6px 8px;
                border-radius: 4px;
                color: {c.TEXT_PRIMARY};
            }}
            #DrawerDocList::item:hover {{
                background-color: {c.BG_HOVER};
            }}
            #DrawerCountLabel {{
                font-size: 11px;
                color: {c.TEXT_MUTED};
                font-weight: 500;
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

    def _select_mode(self, mode: str):
        self.current_mode = mode
        self.tile_none.set_selected(mode == "none")
        self.tile_all.set_selected(mode == "all")
        self.tile_specific.set_selected(mode == "specific")
        
        is_specific = (mode == "specific")
        self.specific_container.setVisible(is_specific)
        self.adjustSize()

    def populate_documents(self):
        self.doc_list.blockSignals(True)
        self.doc_list.clear()
        if not self.doc_manager:
            self.doc_list.blockSignals(False)
            return
            
        docs = self.doc_manager.repo.list_documents()
        
        # Update tile_all badge with live document count
        doc_count = len(docs)
        badge_text = f"{doc_count} Files" if doc_count != 1 else "1 File"
        self.tile_all.update_badge(badge_text)

        if not docs:
            item = QListWidgetItem("No indexed documents in library yet.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.doc_list.addItem(item)
            self.doc_list.blockSignals(False)
            self._update_selected_count()
            return
            
        for d in docs:
            real_count = d.get("real_chunk_count", d.get("chunk_count", 0))
            if real_count > 0 and d.get("status") == "Indexed":
                chunk_str = f"{real_count} chunks"
            elif d.get("status") == "Indexing":
                chunk_str = "indexing..."
            else:
                chunk_str = "needs re-indexing"
                
            filename = d.get("filename", "")
            ext = os.path.splitext(filename)[1].lower()
            is_dark = (ThemeManager.instance().theme == "dark")
            doc_icon = create_document_icon(ext, size=18, dark=is_dark, with_container=False)
            text = f"  {filename}  ({chunk_str})"
            
            item = QListWidgetItem()
            item.setText(text)
            item.setIcon(QIcon(doc_icon))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            is_checked = d["id"] in self.current_doc_ids
            item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, d["id"])
            self.doc_list.addItem(item)
            
        self.doc_list.blockSignals(False)
        self._update_selected_count()

    def _filter_items(self, text: str):
        text = text.lower()
        for i in range(self.doc_list.count()):
            item = self.doc_list.item(i)
            item.setHidden(text not in item.text().lower())

    def _select_all(self):
        self.doc_list.blockSignals(True)
        for i in range(self.doc_list.count()):
            item = self.doc_list.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked)
        self.doc_list.blockSignals(False)
        self._update_selected_count()

    def _clear_all(self):
        self.doc_list.blockSignals(True)
        for i in range(self.doc_list.count()):
            item = self.doc_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
        self.doc_list.blockSignals(False)
        self._update_selected_count()

    def _on_item_check_changed(self, _item):
        self._update_selected_count()

    def _update_selected_count(self):
        sel_count = 0
        total_count = 0
        for i in range(self.doc_list.count()):
            item = self.doc_list.item(i)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                total_count += 1
                if item.checkState() == Qt.CheckState.Checked:
                    sel_count += 1
                    
        self.sel_count_lbl.setText(f"{sel_count} of {total_count} documents selected")
        self.tile_specific.update_badge(f"{sel_count} selected" if sel_count > 0 else "Scoped")

    def _on_manage_library(self):
        self.manage_library_requested.emit()
        self.populate_documents()

    def _apply(self):
        if self.current_mode == "none":
            mode = "none"
            selected_ids = []
        elif self.current_mode == "all":
            mode = "all"
            selected_ids = []
        else:
            mode = "specific"
            selected_ids = []
            for i in range(self.doc_list.count()):
                item = self.doc_list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    doc_id = item.data(Qt.ItemDataRole.UserRole)
                    if doc_id is not None:
                        selected_ids.append(doc_id)
                        
            # If user selected specific mode but checked 0 documents, fallback to none
            if not selected_ids:
                mode = "none"

        self.knowledge_applied.emit(mode, selected_ids)
        self.accept()


class KnowledgeSelector(QWidget):
    """Top bar control displaying active knowledge context with 1-click scoping popover."""
    
    knowledge_changed = Signal(str, list)
    manage_requested = Signal()
    
    def __init__(self, doc_manager=None, parent=None):
        super().__init__(parent)
        self.doc_manager = doc_manager
        self.mode = "none"
        self.doc_ids = []
        self.setObjectName("KnowledgeSelector")
        
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.pill_btn = QPushButton("📚 Knowledge: Off ▾")
        self.pill_btn.setObjectName("TopBarKnowledgeBtn")
        self.pill_btn.setFixedHeight(28)
        self.pill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pill_btn.clicked.connect(self._open_scoping_dialog)
        layout.addWidget(self.pill_btn)
        
        self._update_button_appearance()
        
    def set_document_manager(self, doc_manager):
        self.doc_manager = doc_manager
        self._update_button_appearance()
        
    def set_knowledge(self, mode: str, doc_ids: list):
        """Sets active knowledge scope without emitting change signal."""
        self.mode = mode or "none"
        self.doc_ids = list(doc_ids or [])
        self._update_button_appearance()

    def _update_button_appearance(self):
        docs_count = len(self.doc_ids)
        
        if self.mode == "all":
            all_count = len(self.doc_manager.repo.list_documents()) if self.doc_manager else 0
            count_str = f" ({all_count})" if all_count > 0 else ""
            self.pill_btn.setText(f"📚 Knowledge: All{count_str} ▾")
            self.pill_btn.setToolTip("Active Knowledge: Searching entire library")
            self.pill_btn.setProperty("active", "true")
            self.pill_btn.setStyleSheet("""
                QPushButton#TopBarKnowledgeBtn {
                    background-color: rgba(255, 95, 21, 0.15);
                    border: 1px solid rgba(255, 95, 21, 0.45);
                    color: #FF5F15;
                    border-radius: 6px;
                    padding: 2px 7px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton#TopBarKnowledgeBtn:hover {
                    background-color: rgba(255, 95, 21, 0.25);
                    border-color: #FF5F15;
                    color: #FF5F15;
                }
            """)
        elif self.mode == "specific" and docs_count > 0:
            file_str = "1 File" if docs_count == 1 else f"{docs_count} Files"
            self.pill_btn.setText(f"📚 Knowledge: {file_str} ▾")
            self.pill_btn.setToolTip(f"Active Knowledge: Scoped to {docs_count} selected files")
            self.pill_btn.setProperty("active", "true")
            self.pill_btn.setStyleSheet("""
                QPushButton#TopBarKnowledgeBtn {
                    background-color: rgba(255, 95, 21, 0.15);
                    border: 1px solid rgba(255, 95, 21, 0.45);
                    color: #FF5F15;
                    border-radius: 6px;
                    padding: 2px 7px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton#TopBarKnowledgeBtn:hover {
                    background-color: rgba(255, 95, 21, 0.25);
                    border-color: #FF5F15;
                    color: #FF5F15;
                }
            """)
        else:
            self.pill_btn.setText("📚 Knowledge: Off ▾")
            self.pill_btn.setToolTip("Active Knowledge: Off (Pure chat, no document retrieval)")
            self.pill_btn.setProperty("active", "false")
            self.pill_btn.setStyleSheet("""
                QPushButton#TopBarKnowledgeBtn {
                    background-color: rgba(128, 134, 144, 0.12);
                    border: 1px solid rgba(128, 134, 144, 0.25);
                    color: #8B949E;
                    border-radius: 6px;
                    padding: 2px 7px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton#TopBarKnowledgeBtn:hover {
                    background-color: rgba(128, 134, 144, 0.20);
                    border-color: #FF5F15;
                    color: #FF5F15;
                }
            """)
            
        self.pill_btn.style().unpolish(self.pill_btn)
        self.pill_btn.style().polish(self.pill_btn)

    def _open_scoping_dialog(self):
        dialog = KnowledgeScopeDialog(
            doc_manager=self.doc_manager,
            current_mode=self.mode,
            current_doc_ids=self.doc_ids,
            parent=self.window()
        )
        dialog.knowledge_applied.connect(self._on_knowledge_applied)
        dialog.manage_library_requested.connect(self.manage_requested.emit)
        dialog.exec()

    @Slot(str, list)
    def _on_knowledge_applied(self, mode: str, doc_ids: list):
        self.mode = mode
        self.doc_ids = doc_ids
        self._update_button_appearance()
        logger.info("KnowledgeSelector applied mode=%s with %d doc_ids", mode, len(doc_ids))
        self.knowledge_changed.emit(mode, doc_ids)

