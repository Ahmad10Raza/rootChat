"""Keyboard Shortcuts Help Dialog for rootChat."""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QScrollArea, QWidget, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

SHORTCUTS_DATA = [
    {
        "category": "Navigation & Layout",
        "shortcuts": [
            (["Ctrl", "N"], "Start a new conversation"),
            (["Ctrl", "B"], "Toggle sidebar collapse / expand"),
            (["Ctrl", "K"], "Focus conversation search bar"),
            (["Ctrl", ","], "Open application settings"),
            (["Ctrl", "M"], "Open local model manager"),
        ]
    },
    {
        "category": "Quick Access & Popups",
        "shortcuts": [
            (["Ctrl", "Space"], "Toggle Spotlight-style Mini-Chat"),
            (["Ctrl", "Shift", "Space"], "Alternative Mini-Chat shortcut"),
            (["Ctrl", "/"], "Show keyboard shortcuts help"),
            (["?"], "Show keyboard shortcuts help"),
            (["F1"], "Show keyboard shortcuts help"),
        ]
    },
    {
        "category": "Chat & Messaging",
        "shortcuts": [
            (["Enter"], "Send message"),
            (["Shift", "Enter"], "Insert newline in composer"),
            (["Escape"], "Stop active AI generation"),
        ]
    },
    {
        "category": "Context Menus & Actions",
        "shortcuts": [
            (["Right-Click", "Sidebar Chat"], "Pin, rename, archive, export, delete chat"),
            (["Right-Click", "Message"], "Copy text, copy markdown, regenerate, delete"),
        ]
    }
]


class ShortcutsDialog(QDialog):
    """Categorized and searchable keyboard shortcuts help modal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(540, 560)
        self.resize(560, 600)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 20)
        main_layout.setSpacing(14)

        # Header
        header = QLabel("⌨️  Keyboard Shortcuts")
        header.setObjectName("DialogHeader")
        main_layout.addWidget(header)

        subtitle = QLabel("Quick keyboard actions for fast navigation and control.")
        subtitle.setStyleSheet("color: #888888; font-size: 13px;")
        main_layout.addWidget(subtitle)

        # Search / Filter Bar
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("Search shortcuts (e.g. chat, model, sidebar)...")
        self.search_input.textChanged.connect(self._filter_shortcuts)
        main_layout.addWidget(self.search_input)

        # Scroll area for shortcut categories
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 8, 8, 8)
        self.container_layout.setSpacing(16)
        
        self.rows = []  # List of (row_widget, search_text)
        self._build_shortcuts_ui()
        self.container_layout.addStretch()

        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area, 1)

        # Bottom row: Close Button
        btn_layout = QHBoxLayout()
        hint = QLabel("Press Esc to close")
        hint.setStyleSheet("color: #666666; font-size: 12px;")
        btn_layout.addWidget(hint)
        btn_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("SecondaryBtn")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        main_layout.addLayout(btn_layout)

    def _build_shortcuts_ui(self):
        for sec in SHORTCUTS_DATA:
            category_name = sec["category"]
            cat_header = QLabel(category_name.upper())
            cat_header.setObjectName("ShortcutCategory")
            cat_header.setStyleSheet("color: #888888; font-size: 11px; font-weight: 700; padding-top: 6px;")
            self.container_layout.addWidget(cat_header)

            for keys, desc in sec["shortcuts"]:
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 4, 0, 4)
                row_layout.setSpacing(12)

                desc_lbl = QLabel(desc)
                desc_lbl.setObjectName("ShortcutDesc")
                desc_lbl.setStyleSheet("color: #D0D0D0; font-size: 13px;")
                row_layout.addWidget(desc_lbl, 1)

                # Badges layout
                badges_widget = QWidget()
                badges_layout = QHBoxLayout(badges_widget)
                badges_layout.setContentsMargins(0, 0, 0, 0)
                badges_layout.setSpacing(4)

                for i, k in enumerate(keys):
                    if i > 0 and k not in ("Chat", "Message"):
                        plus = QLabel("+")
                        plus.setStyleSheet("color: #666666; font-size: 11px;")
                        badges_layout.addWidget(plus)
                    
                    badge = QLabel(k)
                    badge.setObjectName("KbdBadge")
                    badge.setStyleSheet(
                        "QLabel#KbdBadge { "
                        "  background-color: #262626; "
                        "  color: #E0E0E0; "
                        "  border: 1px solid #404040; "
                        "  border-radius: 4px; "
                        "  padding: 3px 7px; "
                        "  font-family: monospace; "
                        "  font-size: 11px; "
                        "  font-weight: 600; "
                        "}"
                    )
                    badges_layout.addWidget(badge)

                row_layout.addWidget(badges_widget)
                self.container_layout.addWidget(row)

                search_text = f"{category_name} {desc} {' '.join(keys)}".lower()
                self.rows.append((row, cat_header, search_text))

    def _filter_shortcuts(self, text: str):
        query = text.strip().lower()
        visible_categories = set()

        for row, cat_header, search_text in self.rows:
            if not query or query in search_text:
                row.show()
                visible_categories.add(cat_header)
            else:
                row.hide()

        # Hide category headers that have no matching visible rows
        for _, cat_header, _ in self.rows:
            cat_header.setVisible(cat_header in visible_categories)
