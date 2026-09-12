import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QListWidget, QListWidgetItem, QFileDialog, 
                               QMessageBox, QCheckBox, QProgressBar)
from PySide6.QtCore import Qt, Slot
from core.document_manager import DocumentManager

class KnowledgeDialog(QDialog):
    """Provides a local dashboard for managing indexed documents, triggering re-indexing, and showing RAG status."""
    def __init__(self, doc_manager: DocumentManager, parent=None):
        super().__init__(parent)
        self.doc_manager = doc_manager
        self.setWindowTitle("Knowledge Base")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header
        header = QLabel("📚  Knowledge Base")
        header.setObjectName("DialogHeader")
        layout.addWidget(header)
        
        # Toggle Global
        self.global_toggle = QCheckBox("Enable RAG (Document Context)")
        self.global_toggle.setChecked(self.doc_manager.app_state.get("knowledge_enabled", True))
        self.global_toggle.toggled.connect(self._on_global_toggle)
        layout.addWidget(self.global_toggle)
        
        # Description
        desc = QLabel("Add local documents to enhance AI responses with your personal data.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # List
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        add_btn = QPushButton("+ Add Documents")
        add_btn.clicked.connect(self._add_documents)
        
        reindex_btn = QPushButton("Re-index Selected")
        reindex_btn.clicked.connect(self._reindex_document)
        
        del_btn = QPushButton("Delete Selected")
        del_btn.clicked.connect(self._delete_document)
        
        for btn in [add_btn, reindex_btn, del_btn]:
            btn_layout.addWidget(btn)
            
        layout.addLayout(btn_layout)
        
        # Connections
        self.doc_manager.document_added.connect(self.load_documents)
        self.doc_manager.indexing_progress.connect(self._on_progress)
        self.doc_manager.indexing_finished.connect(self._on_finished)
        
        self.load_documents()
        
    def load_documents(self):
        self.list_widget.clear()
        docs = self.doc_manager.repo.list_documents()
        
        if not docs:
            item = QListWidgetItem("No documents yet — add files to enhance AI responses")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(item)
            return
        
        for doc in docs:
            status_icon = "✓" if doc["status"] == "Indexed" else "⚠" if doc["status"] == "Failed" else "⌛"
            chunk_text = f"{doc['chunk_count']} chunks" if doc.get('chunk_count') else "processing"
            text = f"{status_icon}  📄 {doc['filename']}  —  {chunk_text}  —  {doc['status']}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, doc)
            self.list_widget.addItem(item)
            
    def _on_global_toggle(self, checked):
        self.doc_manager.app_state.set("knowledge_enabled", checked)
        
    def _add_documents(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Documents", "", "Documents (*.pdf *.txt *.md *.csv *.json *.docx)"
        )
        for f in files:
            doc_id, msg = self.doc_manager.add_document(f)
            if doc_id is None:
                QMessageBox.warning(self, "Error", msg)
        self.load_documents()
        
    def _reindex_document(self):
        item = self.list_widget.currentItem()
        if item:
            doc = item.data(Qt.ItemDataRole.UserRole)
            if doc:
                self.doc_manager.reindex_document(doc["id"], doc["file_path"])
                self.load_documents()
            
    def _delete_document(self):
        item = self.list_widget.currentItem()
        if item:
            doc = item.data(Qt.ItemDataRole.UserRole)
            if doc:
                reply = QMessageBox.question(self, "Delete Document", 
                                              f"Delete {doc['filename']}? This removes all vectors.",
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.doc_manager.delete_document(doc["id"])
                    self.load_documents()

    @Slot(int, str, int)
    def _on_progress(self, doc_id, msg, pct):
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_label.setText(f"Indexing... {msg}")
        self.progress_bar.setValue(pct)
        
    @Slot(int, bool, str)
    def _on_finished(self, doc_id, success, msg):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.load_documents()
        if not success:
            QMessageBox.warning(self, "Indexing Failed", msg)
