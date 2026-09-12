from PySide6.QtWidgets import QWidget, QHBoxLayout, QTextEdit, QPushButton
from PySide6.QtCore import Qt, Signal, QEvent
from ui.theme.spacing import Dimensions


class MessageInput(QWidget):
    send_requested = Signal(str)
    stop_requested = Signal()
    
    def __init__(self, app_state=None):
        super().__init__()
        self.app_state = app_state
        self.setObjectName("ComposerContainer")
        self.is_generating = False
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(10)
        
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
        
        layout.addWidget(self.text_edit)
        layout.addWidget(self.action_btn)
        
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
