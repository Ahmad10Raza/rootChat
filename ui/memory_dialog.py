from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QListWidget, QListWidgetItem, QInputDialog, 
                               QMessageBox, QCheckBox)
from PySide6.QtCore import Qt
from core.memory_manager import MemoryManager

class MemoryDialog(QDialog):
    """Dedicated interface for viewing and managing explicit user memories."""
    
    def __init__(self, memory_manager: MemoryManager, parent=None):
        super().__init__(parent)
        self.memory_manager = memory_manager
        self.setWindowTitle("Memory Management")
        self.setMinimumSize(520, 480)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header
        header = QLabel("🧠  Memory")
        header.setObjectName("DialogHeader")
        layout.addWidget(header)
        
        # Toggle Global
        self.global_toggle = QCheckBox("Enable Memory Engine")
        self.global_toggle.setChecked(self.memory_manager.app_state.get("memory_enabled", True))
        self.global_toggle.toggled.connect(self._on_global_toggle)
        layout.addWidget(self.global_toggle)
        
        # Description
        desc = QLabel("Your saved memories help rootChat personalize responses.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._edit_memory)
        layout.addWidget(self.list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        add_btn = QPushButton("+ Add Memory")
        add_btn.clicked.connect(self._add_memory)
        
        toggle_btn = QPushButton("Toggle Active")
        toggle_btn.clicked.connect(self._toggle_selected)
        
        del_btn = QPushButton("Delete Selected")
        del_btn.clicked.connect(self._delete_memory)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        
        for btn in [add_btn, toggle_btn, del_btn, clear_btn]:
            btn_layout.addWidget(btn)
            
        layout.addLayout(btn_layout)
        
        self.load_memories()
        
    def load_memories(self):
        self.list_widget.clear()
        memories = self.memory_manager.repo.list_memories()
        
        if not memories:
            item = QListWidgetItem("No memories yet — tell rootChat to remember something")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(item)
            return
            
        for mem in memories:
            status = "✓" if mem["is_enabled"] else "○"
            text = f"{status}  [{mem['category']}]  {mem['content']}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, mem)
            self.list_widget.addItem(item)
            
    def _on_global_toggle(self, checked):
        self.memory_manager.app_state.set("memory_enabled", checked)
        
    def _add_memory(self):
        content, ok = QInputDialog.getText(self, "Add Memory", "Memory content:")
        if ok and content.strip():
            self.memory_manager.create_memory(content.strip(), category="user")
            self.load_memories()
            
    def _edit_memory(self, item):
        mem = item.data(Qt.ItemDataRole.UserRole)
        if not mem:
            return
        content, ok = QInputDialog.getText(self, "Edit Memory", "Update content:", text=mem["content"])
        if ok and content.strip():
            self.memory_manager.repo.update_memory(mem["id"], content=content.strip())
            self.load_memories()
            
    def _toggle_selected(self):
        item = self.list_widget.currentItem()
        if item:
            mem = item.data(Qt.ItemDataRole.UserRole)
            if mem:
                self.memory_manager.repo.update_memory(mem["id"], is_enabled=not mem["is_enabled"])
                self.load_memories()
            
    def _delete_memory(self):
        item = self.list_widget.currentItem()
        if item:
            mem = item.data(Qt.ItemDataRole.UserRole)
            if mem:
                self.memory_manager.repo.delete_memory(mem["id"])
                self.load_memories()
            
    def _clear_all(self):
        reply = QMessageBox.question(self, "Clear All Memories", "Are you sure? This cannot be undone.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.memory_manager.repo.clear_all_memories()
            self.load_memories()
