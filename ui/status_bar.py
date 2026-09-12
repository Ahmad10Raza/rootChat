from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Slot, Qt
from ui.theme.spacing import Dimensions
from utils.logger import logger

class StatusBar(QWidget):
    """
    Modern status bar displaying:
    - Ollama server connection status
    - Active conversation message count
    - Memory and RAG context augmentation indicators
    - Token generation speed meter (eval_count, tok/s)
    - Active model name
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setFixedHeight(Dimensions.STATUS_BAR_HEIGHT)
        self.message_count = 0
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(6)

        # Connection status indicator
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setStyleSheet("color: #FF5555; font-size: 10px;")
        
        self.status_text = QLabel("Ollama: Offline")
        self.status_text.setObjectName("StatusText")

        # Separator 1
        self.sep1 = QLabel("│")
        self.sep1.setObjectName("StatusSeparator")

        # Message count
        self.msg_count_text = QLabel("💬 0 messages")
        self.msg_count_text.setObjectName("StatusMessages")

        # Context indicators (memories / sources)
        self.sep2 = QLabel("│")
        self.sep2.setObjectName("StatusSeparator")
        self.sep2.hide()

        self.context_text = QLabel("")
        self.context_text.setObjectName("StatusContext")
        self.context_text.hide()

        # Layout stretches between left information and right statistics
        layout.addWidget(self.status_dot)
        layout.addWidget(self.status_text)
        layout.addWidget(self.sep1)
        layout.addWidget(self.msg_count_text)
        layout.addWidget(self.sep2)
        layout.addWidget(self.context_text)

        layout.addStretch()

        # Token speed meter (Right side)
        self.speed_text = QLabel("")
        self.speed_text.setObjectName("StatusSpeed")
        self.speed_text.hide()

        # Separator 3
        self.sep3 = QLabel("│")
        self.sep3.setObjectName("StatusSeparator")
        self.sep3.hide()

        # Active Model
        self.model_text = QLabel("Model: None")
        self.model_text.setObjectName("StatusModel")

        layout.addWidget(self.speed_text)
        layout.addWidget(self.sep3)
        layout.addWidget(self.model_text)

    @Slot(bool, str)
    def update_connection_status(self, is_connected: bool, message: str):
        if is_connected:
            self.status_dot.setStyleSheet("color: #35C759; font-size: 10px;")
            self.status_text.setText("Ollama: Connected")
            logger.debug("Status bar updated: Connected.")
        else:
            self.status_dot.setStyleSheet("color: #FF5555; font-size: 10px;")
            self.status_text.setText(f"Ollama: {message}")
            logger.debug("Status bar updated: Offline (%s).", message)

    @Slot(str)
    def update_selected_model(self, model_name: str):
        if model_name:
            self.model_text.setText(f"Model: {model_name}")
        else:
            self.model_text.setText("Model: None")
        logger.debug("Status bar model updated: %s", model_name)

    @Slot(int)
    def set_message_count(self, count: int):
        self.message_count = max(0, count)
        plural = "s" if self.message_count != 1 else ""
        self.msg_count_text.setText(f"💬 {self.message_count} message{plural}")

    def increment_message_count(self, delta: int = 1):
        self.set_message_count(self.message_count + delta)

    def decrement_message_count(self, delta: int = 1):
        self.set_message_count(self.message_count - delta)

    @Slot(bool)
    def set_generation_active(self, is_generating: bool):
        if is_generating:
            self.speed_text.setText("⚡ Generating...")
            self.speed_text.setToolTip("Ollama is generating response...")
            self.speed_text.show()
            self.sep3.show()
        else:
            if self.speed_text.text() == "⚡ Generating...":
                self.speed_text.setText("")
                self.speed_text.hide()
                self.sep3.hide()

    @Slot(dict)
    def update_generation_stats(self, stats: dict):
        if not stats:
            self.speed_text.setText("")
            self.speed_text.hide()
            self.sep3.hide()
            return

        eval_count = stats.get("eval_count", 0)
        eval_rate = stats.get("eval_rate", 0.0)
        eval_dur_sec = stats.get("eval_duration", 0) / 1e9
        prompt_count = stats.get("prompt_eval_count", 0)
        prompt_dur_sec = stats.get("prompt_eval_duration", 0) / 1e9

        if eval_count > 0:
            if eval_rate > 0:
                text = f"⚡ {eval_count} tokens • {eval_rate:.1f} tok/s"
            elif eval_dur_sec > 0:
                text = f"⚡ {eval_count} tokens ({eval_dur_sec:.1f}s)"
            else:
                text = f"⚡ {eval_count} tokens"

            self.speed_text.setText(text)

            tooltip_lines = [f"Generated: {eval_count} tokens"]
            if eval_dur_sec > 0:
                tooltip_lines[0] += f" in {eval_dur_sec:.2f}s"
            if eval_rate > 0:
                tooltip_lines[0] += f" ({eval_rate:.1f} tok/s)"
            if prompt_count > 0:
                prompt_line = f"Prompt context: {prompt_count} tokens"
                if prompt_dur_sec > 0:
                    prompt_line += f" in {prompt_dur_sec:.2f}s"
                tooltip_lines.append(prompt_line)

            self.speed_text.setToolTip("\n".join(tooltip_lines))
            self.speed_text.show()
            self.sep3.show()
        else:
            self.speed_text.setText("")
            self.speed_text.hide()
            self.sep3.hide()

    @Slot(int, int)
    def set_context_stats(self, memories_count: int = 0, sources_count: int = 0):
        parts = []
        if memories_count > 0:
            mem_str = "memory" if memories_count == 1 else "memories"
            parts.append(f"🧠 {memories_count} {mem_str}")
        if sources_count > 0:
            src_str = "source" if sources_count == 1 else "sources"
            parts.append(f"📚 {sources_count} {src_str}")

        if parts:
            self.context_text.setText(" • ".join(parts))
            self.context_text.setToolTip("Active memories and document sources injected into Ollama prompt")
            self.context_text.show()
            self.sep2.show()
        else:
            self.context_text.setText("")
            self.context_text.hide()
            self.sep2.hide()

    def reset_session_stats(self):
        self.set_message_count(0)
        self.set_context_stats(0, 0)
        self.speed_text.setText("")
        self.speed_text.hide()
        self.sep3.hide()
