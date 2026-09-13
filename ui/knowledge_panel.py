import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QCheckBox, QProgressBar, QFrame, QWidget,
    QLineEdit, QStackedWidget
)
from PySide6.QtCore import Qt, Slot, QSize
from core.document_manager import DocumentManager
from ui.theme.theme_manager import ThemeManager
from ui.doc_icon_helper import create_document_icon
from utils.logger import logger


def format_size(size_bytes: int) -> str:
    """Formats bytes into human readable string (KB, MB, GB)."""
    if not size_bytes or size_bytes <= 0:
        return "0 B"
    val = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if val < 1024.0:
            return f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} PB"


class DocumentCardWidget(QWidget):
    """Custom rich card widget representing a single indexed document in the library."""
    
    def __init__(self, doc: dict, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.init_ui()
        
    def init_ui(self):
        c = ThemeManager.instance().colors
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        filename = self.doc.get("filename", "Untitled")
        ext = os.path.splitext(filename)[1].lower()
        size_str = format_size(self.doc.get("file_size", 0))
        real_count = self.doc.get("real_chunk_count", self.doc.get("chunk_count", 0))
        status = self.doc.get("status", "Unknown")
        
        # 1. File Type Icon Badge
        self.icon_badge = QLabel()
        self.icon_badge.setFixedSize(38, 38)
        self.icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        is_dark = (ThemeManager.instance().theme == "dark")
        self.icon_badge.setPixmap(create_document_icon(ext, size=38, dark=is_dark, with_container=True))
        layout.addWidget(self.icon_badge)
        
        # 2. Document Info Layout (Title + Subtitle)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        title_lbl = QLabel(filename)
        title_lbl.setObjectName("DocCardTitle")
        title_lbl.setToolTip(filename)
        title_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c.TEXT_PRIMARY};")
        info_layout.addWidget(title_lbl)
        
        # Subtitle metadata
        sub_text = f"{size_str} • {ext.upper().lstrip('.')} Document"
        sub_lbl = QLabel(sub_text)
        sub_lbl.setObjectName("DocCardSubtitle")
        sub_lbl.setStyleSheet(f"font-size: 11px; color: {c.TEXT_MUTED};")
        info_layout.addWidget(sub_lbl)
        
        layout.addLayout(info_layout, 1)
        
        # 3. Status Badge
        self.status_badge = QLabel()
        self.status_badge.setFixedHeight(24)
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if real_count > 0 and status == "Indexed":
            self.status_badge.setText(f"✓ {real_count} Chunks")
            self.status_badge.setStyleSheet("""
                QLabel {
                    background-color: rgba(53, 199, 89, 0.14);
                    color: #35C759;
                    border: 1px solid rgba(53, 199, 89, 0.35);
                    border-radius: 12px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        elif status == "Indexing":
            self.status_badge.setText("⌛ Indexing...")
            self.status_badge.setStyleSheet("""
                QLabel {
                    background-color: rgba(91, 157, 240, 0.15);
                    color: #5B9DF0;
                    border: 1px solid rgba(91, 157, 240, 0.40);
                    border-radius: 12px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        elif status == "Failed":
            self.status_badge.setText("✕ Failed")
            self.status_badge.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 85, 85, 0.15);
                    color: #FF5555;
                    border: 1px solid rgba(255, 85, 85, 0.40);
                    border-radius: 12px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        else:
            self.status_badge.setText("⚠ Needs Re-indexing")
            self.status_badge.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 181, 69, 0.15);
                    color: #FFB545;
                    border: 1px solid rgba(255, 181, 69, 0.40);
                    border-radius: 12px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
            
        layout.addWidget(self.status_badge)


class KnowledgeDialog(QDialog):
    """Provides a local dashboard for managing indexed documents, triggering re-indexing, and showing RAG status."""
    
    def __init__(self, doc_manager: DocumentManager, parent=None):
        super().__init__(parent)
        self.doc_manager = doc_manager
        self._filter_text = ""
        
        self.setWindowTitle("Knowledge Base Library")
        self.setMinimumSize(680, 560)
        self.resize(720, 580)
        
        self.init_ui()
        self._apply_theme()
        
        # Connections
        self.doc_manager.document_added.connect(self.load_documents)
        self.doc_manager.indexing_progress.connect(self._on_progress)
        self.doc_manager.indexing_finished.connect(self._on_finished)
        
        self.load_documents()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # ============ 1. HEADER ============
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Icon badge
        header_icon = QLabel("📚")
        header_icon.setObjectName("HeaderIconBadge")
        header_icon.setFixedSize(42, 42)
        header_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(header_icon)

        # Header titles
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(3)
        header_text_layout.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel("Knowledge Base Library")
        title_lbl.setObjectName("DialogHeaderTitle")
        header_text_layout.addWidget(title_lbl)

        subtitle_lbl = QLabel("Manage local files, vectorize documents, and supply context for your AI chats.")
        subtitle_lbl.setObjectName("DialogHeaderSubtitle")
        subtitle_lbl.setWordWrap(True)
        header_text_layout.addWidget(subtitle_lbl)

        header_layout.addLayout(header_text_layout, 1)

        # Stats Badge
        self.stats_badge = QLabel("0 Documents • 0 Chunks")
        self.stats_badge.setObjectName("StatsBadge")
        header_layout.addWidget(self.stats_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        main_layout.addLayout(header_layout)

        # ============ 2. RAG CONFIG CARD ============
        config_card = QFrame()
        config_card.setObjectName("RAGConfigCard")
        config_layout = QHBoxLayout(config_card)
        config_layout.setContentsMargins(14, 12, 14, 12)
        config_layout.setSpacing(12)

        toggle_layout = QVBoxLayout()
        toggle_layout.setSpacing(2)
        toggle_layout.setContentsMargins(0, 0, 0, 0)

        self.global_toggle = QCheckBox("Enable RAG Context (Document Retrieval)")
        self.global_toggle.setObjectName("RAGToggle")
        self.global_toggle.setChecked(self.doc_manager.app_state.get("knowledge_enabled", True))
        self.global_toggle.toggled.connect(self._on_global_toggle)
        toggle_layout.addWidget(self.global_toggle)

        rag_desc = QLabel("When enabled, chats can retrieve context from indexed documents to answer questions.")
        rag_desc.setObjectName("RAGDesc")
        rag_desc.setWordWrap(True)
        toggle_layout.addWidget(rag_desc)


        config_layout.addLayout(toggle_layout, 1)

        # Engine Badge
        engine_badge = QLabel("⚡ nomic-embed-text • Ready")
        engine_badge.setObjectName("EngineBadge")
        config_layout.addWidget(engine_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        main_layout.addWidget(config_card)

        # ============ 3. SEARCH & TOOLBAR ============
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("DocSearchInput")
        self.search_input.setPlaceholderText("🔍  Search documents by name...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedHeight(34)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_input, 1)

        main_layout.addLayout(search_layout)

        # ============ 4. DOCUMENT LIST & EMPTY STATE ============
        self.content_stack = QStackedWidget()

        # Page 0: List
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("KnowledgeDocList")
        self.list_widget.setSpacing(6)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self.content_stack.addWidget(self.list_widget)

        # Page 1: Empty State Card
        empty_card = QFrame()
        empty_card.setObjectName("EmptyStateCard")
        empty_layout = QVBoxLayout(empty_card)
        empty_layout.setContentsMargins(32, 36, 32, 36)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_icon = QLabel("📂")
        empty_icon.setStyleSheet("font-size: 36px;")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)

        empty_title = QLabel("No Documents in Library")
        empty_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #F5F7FA;")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)

        empty_desc = QLabel("Add PDFs, Word docs, Markdown, or text files to enhance AI chats with your private knowledge.")
        empty_desc.setStyleSheet("font-size: 12px; color: #8B949E;")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_desc.setWordWrap(True)
        empty_layout.addWidget(empty_desc)

        empty_btn = QPushButton("+ Add Your First Document")
        empty_btn.setObjectName("EmptyAddBtn")
        empty_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        empty_btn.clicked.connect(self._add_documents)
        empty_layout.addWidget(empty_btn, 0, Qt.AlignmentFlag.AlignCenter)

        self.content_stack.addWidget(empty_card)
        main_layout.addWidget(self.content_stack, 1)

        # ============ 5. PROGRESS CARD ============
        self.progress_card = QFrame()
        self.progress_card.setObjectName("ProgressCard")
        self.progress_card.setVisible(False)
        p_layout = QVBoxLayout(self.progress_card)
        p_layout.setContentsMargins(12, 10, 12, 10)
        p_layout.setSpacing(6)

        p_top = QHBoxLayout()
        self.progress_label = QLabel("Indexing...")
        self.progress_label.setObjectName("ProgressLabel")
        p_top.addWidget(self.progress_label, 1)

        self.progress_pct_lbl = QLabel("0%")
        self.progress_pct_lbl.setObjectName("ProgressPctLabel")
        p_top.addWidget(self.progress_pct_lbl)
        p_layout.addLayout(p_top)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("KnowledgeProgressBar")
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        p_layout.addWidget(self.progress_bar)

        main_layout.addWidget(self.progress_card)

        # ============ 6. BOTTOM ACTION TOOLBAR ============
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.setSpacing(10)

        self.add_btn = QPushButton("+ Add Documents")
        self.add_btn.setObjectName("ActionPrimaryBtn")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setFixedHeight(34)
        self.add_btn.clicked.connect(self._add_documents)
        btn_layout.addWidget(self.add_btn)

        self.reindex_btn = QPushButton("↻ Re-index Selected")
        self.reindex_btn.setObjectName("ActionSecondaryBtn")
        self.reindex_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reindex_btn.setFixedHeight(34)
        self.reindex_btn.setEnabled(False)
        self.reindex_btn.clicked.connect(self._reindex_document)
        btn_layout.addWidget(self.reindex_btn)

        self.del_btn = QPushButton("🗑 Delete Selected")
        self.del_btn.setObjectName("ActionDangerBtn")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setFixedHeight(34)
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self._delete_document)
        btn_layout.addWidget(self.del_btn)

        btn_layout.addStretch(1)

        close_btn = QPushButton("Done")
        close_btn.setObjectName("ActionSecondaryBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedHeight(34)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        main_layout.addLayout(btn_layout)

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
                border-radius: 10px;
                font-size: 20px;
            }}
            #DialogHeaderTitle {{
                font-size: 17px;
                font-weight: 700;
                color: {c.TEXT_PRIMARY};
            }}
            #DialogHeaderSubtitle {{
                font-size: 12px;
                color: {c.TEXT_SECONDARY};
            }}
            #StatsBadge {{
                background-color: {c.BG_CARD};
                border: 1px solid {c.BORDER};
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
                color: {c.TEXT_SECONDARY};
            }}
            #RAGConfigCard {{
                background-color: {c.BG_CARD};
                border: 1px solid {c.BORDER};
                border-radius: 8px;
            }}
            #RAGToggle {{
                font-size: 13px;
                font-weight: 600;
                color: {c.TEXT_PRIMARY};
            }}
            #RAGDesc {{
                font-size: 11px;
                color: {c.TEXT_MUTED};
            }}
            #EngineBadge {{
                background-color: rgba(53, 199, 89, 0.12);
                color: {c.SUCCESS};
                border: 1px solid rgba(53, 199, 89, 0.3);
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            #DocSearchInput {{
                background-color: {c.BG_INPUT};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                color: {c.TEXT_PRIMARY};
                padding: 6px 12px;
                font-size: 12px;
            }}
            #DocSearchInput:focus {{
                border-color: {c.ACCENT};
            }}
            #KnowledgeDocList {{
                background-color: {c.BG_CARD};
                border: 1px solid {c.BORDER};
                border-radius: 8px;
                padding: 6px;
            }}
            #KnowledgeDocList::item {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                margin-bottom: 4px;
            }}
            #KnowledgeDocList::item:hover {{
                background-color: {c.BG_HOVER};
                border-color: {c.BORDER};
            }}
            #KnowledgeDocList::item:selected {{
                background-color: {c.BG_SELECTED};
                border: 1px solid {c.ACCENT};
            }}
            #EmptyStateCard {{
                background-color: {c.BG_CARD};
                border: 1px dashed {c.BORDER};
                border-radius: 8px;
            }}
            #EmptyAddBtn {{
                background-color: {c.ACCENT};
                color: #FFFFFF;
                font-weight: 600;
                font-size: 12px;
                border-radius: 6px;
                padding: 8px 16px;
                border: none;
            }}
            #EmptyAddBtn:hover {{
                background-color: {c.ACCENT_HOVER};
            }}
            #ProgressCard {{
                background-color: {c.BG_CARD};
                border: 1px solid {c.BORDER};
                border-radius: 8px;
            }}
            #ProgressLabel {{
                font-size: 11px;
                font-weight: 600;
                color: {c.TEXT_PRIMARY};
            }}
            #ProgressPctLabel {{
                font-size: 11px;
                font-weight: 700;
                color: {c.ACCENT};
            }}
            #KnowledgeProgressBar {{
                background-color: {c.BG_INPUT};
                border-radius: 3px;
            }}
            #KnowledgeProgressBar::chunk {{
                background-color: {c.ACCENT};
                border-radius: 3px;
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
            #ActionSecondaryBtn:disabled {{
                color: {c.TEXT_MUTED};
                border-color: {c.BORDER_SUBTLE};
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
            #ActionDangerBtn:disabled {{
                color: {c.TEXT_MUTED};
                border-color: {c.BORDER_SUBTLE};
            }}
        """)

    def load_documents(self):
        self.list_widget.clear()
        docs = self.doc_manager.repo.list_documents() if self.doc_manager else []
        
        total_docs = len(docs)
        total_chunks = sum(d.get("real_chunk_count", d.get("chunk_count", 0)) for d in docs)
        doc_str = "1 Document" if total_docs == 1 else f"{total_docs} Documents"
        self.stats_badge.setText(f"{doc_str} • {total_chunks} Chunks")
        
        if not docs:
            self.content_stack.setCurrentIndex(1)  # Empty state
            self.reindex_btn.setEnabled(False)
            self.del_btn.setEnabled(False)
            return
            
        self.content_stack.setCurrentIndex(0)  # List state
        
        for doc in docs:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 68))
            item.setData(Qt.ItemDataRole.UserRole, doc)
            
            card_widget = DocumentCardWidget(doc)
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card_widget)
            
        self._filter_list()
        self._on_selection_changed(self.list_widget.currentItem(), None)

    def _filter_list(self):
        q = self._filter_text.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            doc = item.data(Qt.ItemDataRole.UserRole)
            if not doc:
                continue
            filename = doc.get("filename", "").lower()
            status = doc.get("status", "").lower()
            match = (not q) or (q in filename) or (q in status)
            item.setHidden(not match)

    def _on_search_text_changed(self, text: str):
        self._filter_text = text
        self._filter_list()

    def _on_selection_changed(self, current, _previous):
        has_sel = current is not None
        self.reindex_btn.setEnabled(has_sel)
        self.del_btn.setEnabled(has_sel)

    def _on_global_toggle(self, checked: bool):
        self.doc_manager.app_state.set("knowledge_enabled", checked)
        logger.info("Knowledge Base RAG enabled toggle changed to: %s", checked)

    def _add_documents(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Documents to Index", 
            "", 
            "Documents (*.pdf *.txt *.md *.csv *.json *.docx)"
        )
        if not files:
            return
            
        for f in files:
            doc_id, msg = self.doc_manager.add_document(f)
            if doc_id is None:
                QMessageBox.warning(self, "Add Document Failed", msg)
        self.load_documents()

    def _reindex_document(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        doc = item.data(Qt.ItemDataRole.UserRole)
        if doc:
            self.doc_manager.reindex_document(doc["id"], doc["file_path"])
            self.load_documents()

    def _delete_document(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        doc = item.data(Qt.ItemDataRole.UserRole)
        if not doc:
            return
            
        reply = QMessageBox.question(
            self, 
            "Delete Document", 
            f"Are you sure you want to remove '{doc['filename']}' from the library?\n\nThis will remove all associated vector embeddings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.doc_manager.delete_document(doc["id"])
            self.load_documents()

    @Slot(int, str, int)
    def _on_progress(self, _doc_id, msg, pct):
        self.progress_card.setVisible(True)
        self.progress_label.setText(f"Indexing: {msg}")
        self.progress_pct_lbl.setText(f"{pct}%")
        self.progress_bar.setValue(pct)

    @Slot(int, bool, str)
    def _on_finished(self, _doc_id, success, msg):
        self.progress_card.setVisible(False)
        self.load_documents()
        if not success:
            QMessageBox.warning(self, "Indexing Failed", msg)

