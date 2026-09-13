import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
                               QLabel, QPushButton, QApplication)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from ui.message_widget import MessageWidget
from ui.message_input import MessageInput
from ui.theme.spacing import Dimensions
from core.chat_manager import ChatManager
from utils.resource_path import get_resource_path

class WelcomeScreen(QWidget):
    """Beautiful empty-state welcome screen with quick actions."""
    quick_action = Signal(str, str)
    
    def __init__(self):
        super().__init__()
        self.setObjectName("WelcomeScreen")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        
        # Icon
        icon = QLabel()
        icon.setObjectName("WelcomeIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = get_resource_path("resources/icons/rootChat_128.png")
        if not os.path.exists(logo_path):
            logo_path = get_resource_path("resources/icons/rootChat.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon.setPixmap(pix)
        else:
            icon.setText("🤖")
        layout.addWidget(icon)
        
        # Title
        title = QLabel("rootChat")
        title.setObjectName("WelcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Your private AI assistant — powered by local Ollama models")
        subtitle.setObjectName("WelcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Quick actions grid
        layout.addSpacing(20)
        
        actions_row1 = QHBoxLayout()
        actions_row1.setSpacing(10)
        actions_row2 = QHBoxLayout()
        actions_row2.setSpacing(10)
        
        prompts = [
            ("💡", "Explain a concept", "general"),
            ("💻", "Write Python code", "coding"),
            ("🗃️", "SQL query help", "sql"),
            ("🐧", "Linux commands", "linux"),
        ]
        
        for i, (emoji, text, preset_id) in enumerate(prompts):
            btn = QPushButton(f"{emoji}  {text}")
            btn.setObjectName("QuickAction")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(48)
            btn.setMinimumWidth(180)
            btn.clicked.connect(lambda _, t=text, p=preset_id: self.quick_action.emit(t, p))
            if i < 2:
                actions_row1.addWidget(btn)
            else:
                actions_row2.addWidget(btn)
        
        layout.addLayout(actions_row1)
        layout.addLayout(actions_row2)
        
        # Privacy indicator
        layout.addSpacing(16)
        privacy = QLabel("🔒 100% Local — No data leaves your machine")
        privacy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        privacy.setStyleSheet("font-size: 12px;")
        layout.addWidget(privacy)


class ChatWindow(QWidget):
    def __init__(self, chat_manager: ChatManager):
        super().__init__()
        self.setObjectName("ChatArea")
        self.chat_manager = chat_manager
        self.message_widgets = {}
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Welcome screen (shown when no messages)
        self.welcome = WelcomeScreen()
        self.welcome.quick_action.connect(self._on_quick_action)
        self.main_layout.addWidget(self.welcome)
        
        # Scroll area for messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("ChatScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Center container for max-width content
        self.scroll_content = QWidget()
        scroll_outer = QHBoxLayout(self.scroll_content)
        scroll_outer.setContentsMargins(0, 0, 0, 0)
        
        self.messages_container = QWidget()
        self.messages_container.setMaximumWidth(Dimensions.CHAT_MAX_WIDTH)
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(20, 16, 20, 24)
        self.messages_layout.setSpacing(16)
        self.messages_layout.addStretch()
        
        scroll_outer.addStretch(1)
        scroll_outer.addWidget(self.messages_container, 100)
        scroll_outer.addStretch(1)
        
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.hide()  # Hidden until messages exist
        self.main_layout.addWidget(self.scroll_area, 1)
        
        # Message input (centered)
        input_outer = QWidget()
        input_outer.setObjectName("ComposerContainer")
        input_outer_layout = QHBoxLayout(input_outer)
        input_outer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.message_input = MessageInput(app_state=self.chat_manager.app_state)
        self.message_input.setMaximumWidth(Dimensions.CHAT_MAX_WIDTH)
        self.message_input.send_requested.connect(self.chat_manager.send_message)
        self.message_input.stop_requested.connect(self.chat_manager.stop_generation)
        
        input_outer_layout.addStretch(1)
        input_outer_layout.addWidget(self.message_input, 100)
        input_outer_layout.addStretch(1)
        
        self.main_layout.addWidget(input_outer, 0)
        
        # Connect ChatManager signals
        self.chat_manager.message_added.connect(self.on_message_added)
        self.chat_manager.message_removed.connect(self.on_message_removed)
        self.chat_manager.chunk_received.connect(self.on_chunk_received)
        self.chat_manager.generation_started.connect(self.on_generation_started)
        self.chat_manager.generation_finished.connect(self.on_generation_finished)
        self.chat_manager.generation_error.connect(self.on_generation_error)
        self.chat_manager.generation_stopped.connect(self.on_generation_stopped)
    
    def _on_quick_action(self, text: str, preset_id: str = "general"):
        """Handle quick action button clicks from welcome screen."""
        if hasattr(self.chat_manager, "app_state") and self.chat_manager.app_state:
            self.chat_manager.app_state.set("active_preset", preset_id)
        self.message_input.text_edit.setPlainText(text)
        self.message_input.text_edit.setFocus()
        
    def _update_visibility(self):
        """Toggle between welcome screen and chat scroll based on message count."""
        has_messages = len(self.message_widgets) > 0
        self.welcome.setVisible(not has_messages)
        self.scroll_area.setVisible(has_messages)
        
    def clear_messages(self):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        self.message_widgets.clear()
        self._update_visibility()
        
    def load_messages(self, messages: list):
        self.clear_messages()
        for msg in messages:
            self.on_message_added(msg)
        self._update_visibility()
            
    def on_message_added(self, msg_dict: dict):
        idx = self.messages_layout.count() - 1
        widget = MessageWidget(msg_dict["role"], msg_dict["content"], msg_dict.get("id"))
        if msg_dict["role"] == "assistant":
            widget.regenerate_requested.connect(self.chat_manager.regenerate_response)
            memories = self.chat_manager.app_state.get("last_memories_data", [])
            if memories and hasattr(widget, "set_recalled_memories"):
                widget.set_recalled_memories(memories)
        widget.delete_requested.connect(self.chat_manager.delete_message)
        
        self.messages_layout.insertWidget(idx, widget)
        if "id" in msg_dict and msg_dict["id"] is not None:
            self.message_widgets[msg_dict["id"]] = widget
            
        if msg_dict.get("role") == "user":
            self.message_input.clear_input()
        
        self._update_visibility()
        self._scroll_to_bottom()

    def on_message_removed(self, msg_id: int):
        if msg_id in self.message_widgets:
            widget = self.message_widgets.pop(msg_id)
            self.messages_layout.removeWidget(widget)
            widget.hide()
            widget.deleteLater()
        
        self._update_visibility()
        self._scroll_to_bottom()
        
    def on_chunk_received(self, chunk: str):
        ast_id = self.chat_manager.current_assistant_msg_id
        if ast_id in self.message_widgets:
            widget = self.message_widgets[ast_id]
            new_content = widget.content + chunk
            widget.render_content(new_content)
            
            scrollbar = self.scroll_area.verticalScrollBar()
            if scrollbar.maximum() - scrollbar.value() < 50:
                self._scroll_to_bottom()
            
    def on_generation_started(self):
        self.message_input.set_generating_state(True)
        ast_id = self.chat_manager.current_assistant_msg_id
        if ast_id in self.message_widgets:
            widget = self.message_widgets[ast_id]
            memories = self.chat_manager.app_state.get("last_memories_data", [])
            if memories and hasattr(widget, "set_recalled_memories"):
                widget.set_recalled_memories(memories)
        
    def on_generation_finished(self, full_response: str):
        self.message_input.set_generating_state(False)
        ast_id = self.chat_manager.current_assistant_msg_id
        if ast_id in self.message_widgets:
            widget = self.message_widgets[ast_id]
            widget.render_content(full_response)
            memories = self.chat_manager.app_state.get("last_memories_data", [])
            if memories and hasattr(widget, "set_recalled_memories"):
                widget.set_recalled_memories(memories)
        
    def on_generation_error(self, error_msg: str):
        self.message_input.set_generating_state(False)
        self._add_system_message(f"Error: {error_msg}")
        
    def on_generation_stopped(self):
        self.message_input.set_generating_state(False)
        
    def _add_system_message(self, text: str):
        idx = self.messages_layout.count() - 1
        widget = MessageWidget("system", text)
        self.messages_layout.insertWidget(idx, widget)
        
    def _scroll_to_bottom(self):
        QTimer.singleShot(50, self._do_scroll)
        
    def _do_scroll(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
