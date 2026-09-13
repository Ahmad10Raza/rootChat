from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal, QEvent
from ui.theme.spacing import Dimensions


class MessageInput(QWidget):
    send_requested = Signal(str)
    stop_requested = Signal()
    knowledge_scope_requested = Signal()
    knowledge_clear_requested = Signal()
    
    def __init__(self, app_state=None):
        super().__init__()
        self.app_state = app_state
        self.setObjectName("ComposerContainer")
        self.is_generating = False
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 4, 16, 14)
        main_layout.setSpacing(6)
        
        # Knowledge Context Pill Row
        self.pill_container = QWidget()
        self.pill_container.setObjectName("PillContainer")
        pill_layout = QHBoxLayout(self.pill_container)
        pill_layout.setContentsMargins(0, 0, 0, 0)
        pill_layout.setSpacing(6)
        pill_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.pill_frame = QFrame()
        self.pill_frame.setObjectName("ComposerKnowledgePill")
        self.pill_frame.setStyleSheet("""
            QFrame#ComposerKnowledgePill {
                background-color: rgba(255, 95, 21, 0.12);
                border: 1px solid rgba(255, 95, 21, 0.35);
                border-radius: 12px;
            }
            QFrame#ComposerKnowledgePill:hover {
                background-color: rgba(255, 95, 21, 0.20);
                border-color: #FF5F15;
            }
        """)
        pill_frame_layout = QHBoxLayout(self.pill_frame)
        pill_frame_layout.setContentsMargins(8, 2, 4, 2)
        pill_frame_layout.setSpacing(4)
        
        self.pill_btn = QPushButton("📚 All Documents")
        self.pill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pill_btn.setToolTip("Click to configure linked documents for this chat")
        self.pill_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #FF7A3D;
                font-size: 11px;
                font-weight: 600;
                padding: 0;
            }
        """)
        self.pill_btn.clicked.connect(self.knowledge_scope_requested.emit)
        pill_frame_layout.addWidget(self.pill_btn)
        
        self.pill_clear_btn = QPushButton("✕")
        self.pill_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pill_clear_btn.setToolTip("Remove knowledge context from this chat")
        self.pill_clear_btn.setFixedSize(16, 16)
        self.pill_clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8B949E;
                font-size: 11px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                color: #FF5F15;
            }
        """)
        self.pill_clear_btn.clicked.connect(self.knowledge_clear_requested.emit)
        pill_frame_layout.addWidget(self.pill_clear_btn)
        
        pill_layout.addWidget(self.pill_frame)
        self.pill_container.hide()
        main_layout.addWidget(self.pill_container)
        
        # Message input row
        input_row = QWidget()
        input_layout = QHBoxLayout(input_row)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("MessageInput")
        self.text_edit.setPlaceholderText("Type your message... (Shift+Enter for new line)")
        self.text_edit.setMaximumHeight(Dimensions.INPUT_MAX_HEIGHT)
        self.text_edit.installEventFilter(self)
        
        self.action_btn = QPushButton("Send")
        self.action_btn.setObjectName("SendBtn")
        self.action_btn.setMinimumHeight(42)
        self.action_btn.setMinimumWidth(80)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.clicked.connect(self._on_action_clicked)
        
        input_layout.addWidget(self.text_edit)
        input_layout.addWidget(self.action_btn)
        main_layout.addWidget(input_row)
        
    def set_knowledge_context(self, mode: str, doc_ids: list):
        """Updates the indicator pill state above the composer."""
        mode = mode or "none"
        doc_ids = doc_ids or []
        
        if mode == "all":
            self.pill_btn.setText("📚 Knowledge: All Documents")
            self.pill_container.show()
        elif mode == "specific" and len(doc_ids) > 0:
            count = len(doc_ids)
            file_text = "1 Document" if count == 1 else f"{count} Documents"
            self.pill_btn.setText(f"📚 Knowledge: {file_text}")
            self.pill_container.show()
        else:
            self.pill_container.hide()
        
    def _on_action_clicked(self):
        if self.is_generating:
            self.stop_requested.emit()
        else:
            text = self.text_edit.toPlainText().strip()
            if text:
                self.send_requested.emit(text)
                
    def set_generating_state(self, generating: bool):
        self.is_generating = generating
        if generating:
            self.action_btn.setText("■ Stop")
            self.action_btn.setObjectName("StopBtn")
            self.text_edit.setReadOnly(True)
        else:
            self.action_btn.setText("Send")
            self.action_btn.setObjectName("SendBtn")
            self.text_edit.setReadOnly(False)
        # Force style refresh after objectName change
        self.action_btn.style().unpolish(self.action_btn)
        self.action_btn.style().polish(self.action_btn)
            
    def clear_input(self):
        self.text_edit.clear()

    def eventFilter(self, obj, event):
        if obj == self.text_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                enter_to_send = True
                if self.app_state:
                    enter_to_send = self.app_state.get("enter_to_send", True)
                if enter_to_send:
                    self._on_action_clicked()
                    return True
        return super().eventFilter(obj, event)
