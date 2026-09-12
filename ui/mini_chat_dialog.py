from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QTextBrowser, QFrame,
    QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from core.ollama_client import OllamaClient
from core.app_state import AppState
from core.stream_worker import StreamWorker
from core.presets import get_preset
from ui.theme.theme_manager import ThemeManager
from utils.logger import logger


class MiniChatDialog(QDialog):
    """Modern Spotlight / HUD-style floating mini-chat for quick queries without opening full chats."""

    chat_promoted = Signal(int)  # Emits new conversation ID when promoted to full chat

    def __init__(self, client: OllamaClient, app_state: AppState, chat_manager=None, parent=None):
        super().__init__(parent)
        self.client = client
        self.app_state = app_state
        self.chat_manager = chat_manager
        self.worker = None
        self.full_response = ""
        self.last_query = ""
        self._was_stopped = False

        # Window configuration
        self.setWindowTitle("Quick Mini-Chat")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(680)
        self.setMinimumHeight(56)

        self.init_ui()
        self._setup_shortcuts()
        self._apply_theme()

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(14, 14, 14, 14)

        # Container Frame for shadow and border radius
        self.container = QFrame()
        self.container.setObjectName("MiniChatContainer")

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(16, 12, 16, 14)
        self.container_layout.setSpacing(10)

        # Top Bar: Icon + Seamless Input + Model & Persona Badge
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        self.icon_lbl = QLabel("✦")
        self.icon_lbl.setObjectName("MiniChatIcon")
        top_row.addWidget(self.icon_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        self.input_field = QLineEdit()
        self.input_field.setObjectName("MiniChatInput")
        self.input_field.setPlaceholderText("Ask Ollama anything... (Press Enter to ask, Esc to close)")
        self.input_field.returnPressed.connect(self._on_submit)
        top_row.addWidget(self.input_field, 1, Qt.AlignmentFlag.AlignVCenter)

        # Model & Persona Pill Badge
        self.badge_lbl = QLabel()
        self.badge_lbl.setObjectName("MiniChatBadge")
        self.badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_badge()
        top_row.addWidget(self.badge_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        self.container_layout.addLayout(top_row)

        # Separator Line (visible when response or footer is shown)
        self.separator = QFrame()
        self.separator.setObjectName("MiniChatSeparator")
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFixedHeight(1)
        self.separator.setVisible(False)
        self.container_layout.addWidget(self.separator)

        # Response text area (hidden initially until query submitted)
        self.response_browser = QTextBrowser()
        self.response_browser.setObjectName("MiniChatBrowser")
        self.response_browser.setOpenExternalLinks(True)
        self.response_browser.setMinimumHeight(160)
        self.response_browser.setMaximumHeight(360)
        self.response_browser.setVisible(False)
        self.container_layout.addWidget(self.response_browser, 1)

        # Status & Action footer (hidden until query)
        self.footer_widget = QFrame()
        self.footer_widget.setObjectName("MiniChatFooter")
        self.footer_widget.setVisible(False)
        footer_layout = QHBoxLayout(self.footer_widget)
        footer_layout.setContentsMargins(0, 2, 0, 0)
        footer_layout.setSpacing(8)

        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("MiniChatStatus")
        footer_layout.addWidget(self.status_lbl, 1, Qt.AlignmentFlag.AlignVCenter)

        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.setObjectName("MiniChatStopBtn")
        self.stop_btn.setAutoDefault(False)
        self.stop_btn.setDefault(False)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setVisible(False)
        footer_layout.addWidget(self.stop_btn)

        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setObjectName("MiniChatCopyBtn")
        self.copy_btn.setAutoDefault(False)
        self.copy_btn.setDefault(False)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._on_copy)
        footer_layout.addWidget(self.copy_btn)

        self.promote_btn = QPushButton("↗ Open in Chat")
        self.promote_btn.setObjectName("MiniChatPromoteBtn")
        self.promote_btn.setAutoDefault(False)
        self.promote_btn.setDefault(False)
        self.promote_btn.setToolTip("Save this exchange and continue in main chat window")
        self.promote_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.promote_btn.clicked.connect(self._on_promote_to_full_chat)
        footer_layout.addWidget(self.promote_btn)

        self.close_btn = QPushButton("Esc Close")
        self.close_btn.setObjectName("MiniChatCloseBtn")
        self.close_btn.setAutoDefault(False)
        self.close_btn.setDefault(False)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.close)
        footer_layout.addWidget(self.close_btn)

        self.container_layout.addWidget(self.footer_widget)
        outer_layout.addWidget(self.container)

    def _apply_theme(self):
        """Apply styles generated dynamically from centralized design tokens."""
        tm = ThemeManager.instance()
        c = tm.colors
        ff = tm.font_family
        mf = tm.mono_family

        self.container.setStyleSheet(f"""
            #MiniChatContainer {{
                background-color: {c.BG_CARD};
                border: 1px solid {c.BORDER};
                border-radius: 16px;
            }}
        """)

        self.icon_lbl.setStyleSheet(f"""
            QLabel#MiniChatIcon {{
                color: {c.TEXT_ACCENT};
                font-size: 16px;
                font-weight: bold;
                padding-left: 2px;
            }}
        """)

        self.input_field.setStyleSheet(f"""
            QLineEdit#MiniChatInput {{
                background: transparent;
                border: none;
                color: {c.TEXT_PRIMARY};
                font-size: 14px;
                font-family: '{ff}';
                padding: 4px 0;
                selection-background-color: {c.ACCENT};
            }}
            QLineEdit#MiniChatInput::placeholder {{
                color: {c.TEXT_MUTED};
            }}
        """)

        self.badge_lbl.setStyleSheet(f"""
            QLabel#MiniChatBadge {{
                background-color: {c.BG_HOVER};
                color: {c.TEXT_SECONDARY};
                border: 1px solid {c.BORDER};
                border-radius: 12px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)

        self.separator.setStyleSheet(f"""
            #MiniChatSeparator {{
                background-color: {c.BORDER_SUBTLE};
                border: none;
            }}
        """)

        self.response_browser.setStyleSheet(f"""
            QTextBrowser#MiniChatBrowser {{
                background-color: {c.BG_PRIMARY};
                border: 1px solid {c.BORDER_SUBTLE};
                border-radius: 10px;
                padding: 12px 14px;
                color: {c.TEXT_PRIMARY};
                font-family: '{ff}';
                font-size: 13px;
                line-height: 1.6;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {c.SCROLLBAR};
                border-radius: 3px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c.SCROLLBAR_HOVER};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

        # Rich markdown document stylesheet
        self.response_browser.document().setDefaultStyleSheet(f"""
            body {{ color: {c.TEXT_PRIMARY}; font-family: '{ff}'; font-size: 13px; line-height: 1.6; }}
            h1 {{ color: {c.TEXT_PRIMARY}; font-size: 17px; font-weight: 700; margin-top: 8px; margin-bottom: 6px; }}
            h2 {{ color: {c.TEXT_PRIMARY}; font-size: 15px; font-weight: 700; margin-top: 8px; margin-bottom: 4px; }}
            h3 {{ color: {c.TEXT_PRIMARY}; font-size: 14px; font-weight: 600; margin-top: 6px; margin-bottom: 4px; }}
            p {{ margin-bottom: 8px; }}
            code {{ background-color: {c.BG_CODE}; color: {c.TEXT_ACCENT}; border: 1px solid {c.BORDER_SUBTLE}; border-radius: 4px; padding: 2px 5px; font-family: '{mf}'; font-size: 12px; }}
            pre {{ background-color: {c.BG_CODE}; border: 1px solid {c.BORDER}; border-radius: 8px; padding: 10px; font-family: '{mf}'; font-size: 12px; }}
            ul, ol {{ margin-left: 18px; margin-bottom: 8px; }}
            li {{ margin-bottom: 4px; }}
            blockquote {{ border-left: 3px solid {c.ACCENT}; padding-left: 10px; margin-left: 0; color: {c.TEXT_SECONDARY}; }}
        """)

        self.status_lbl.setStyleSheet(f"""
            QLabel#MiniChatStatus {{
                color: {c.TEXT_MUTED};
                font-size: 12px;
                font-weight: 500;
            }}
        """)

        self.stop_btn.setStyleSheet(f"""
            QPushButton#MiniChatStopBtn {{
                background-color: rgba(255, 85, 85, 0.12);
                color: {c.ERROR};
                border: 1px solid rgba(255, 85, 85, 0.3);
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#MiniChatStopBtn:hover {{
                background-color: {c.ERROR};
                color: white;
            }}
        """)

        self.copy_btn.setStyleSheet(f"""
            QPushButton#MiniChatCopyBtn {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton#MiniChatCopyBtn:hover {{
                background-color: {c.BG_HOVER};
                border-color: {c.TEXT_MUTED};
            }}
        """)

        self.promote_btn.setStyleSheet(f"""
            QPushButton#MiniChatPromoteBtn {{
                background-color: {c.ACCENT};
                color: white;
                border: 1px solid {c.ACCENT};
                border-radius: 6px;
                padding: 5px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#MiniChatPromoteBtn:hover {{
                background-color: {c.ACCENT_HOVER};
                border-color: {c.ACCENT_HOVER};
            }}
            QPushButton#MiniChatPromoteBtn:pressed {{
                background-color: {c.ACCENT_PRESSED};
            }}
        """)

        self.close_btn.setStyleSheet(f"""
            QPushButton#MiniChatCloseBtn {{
                background-color: transparent;
                color: {c.TEXT_MUTED};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
            }}
            QPushButton#MiniChatCloseBtn:hover {{
                background-color: {c.BG_HOVER};
                color: {c.TEXT_PRIMARY};
                border-color: {c.BORDER};
            }}
        """)

    def _update_badge(self):
        """Update badge text and tooltip to match active model and persona."""
        active_model = self.app_state.get("selected_model", "Default")
        active_preset_id = self.app_state.get("active_preset", "general")
        preset_info = get_preset(active_preset_id)
        self.badge_lbl.setText(f"{preset_info.get('icon', '🤖')} {active_model}")
        self.badge_lbl.setToolTip(f"Model: {active_model} | Persona: {preset_info.get('name', 'General')}")

    def _setup_shortcuts(self):
        # Escape closes or stops
        QShortcut(QKeySequence("Escape"), self, self._on_escape)
        # Ctrl+Shift+C copies response
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self._on_copy)

    def keyPressEvent(self, event):

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # If the user presses Enter on a focused button, let that button handle it
            focused = QApplication.focusWidget()
            if isinstance(focused, QPushButton):
                focused.click()
                event.accept()
                return
            # If input field is active and not read-only, submit query
            if self.input_field.hasFocus() and not self.input_field.isReadOnly():
                self._on_submit()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Escape:
            self._on_escape()
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_escape(self):
        if self.worker and self.worker.isRunning():
            self._on_stop()
        else:
            self.close()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_badge()
        self._apply_theme()
        self.input_field.setFocus()
        if not self.full_response:
            self.separator.setVisible(False)
            self.response_browser.setVisible(False)
            self.footer_widget.setVisible(False)
            self.adjustSize()
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + 80  # Position slightly towards the top like Spotlight
            self.move(max(20, x), max(20, y))

    def _on_submit(self):
        if self.worker and self.worker.isRunning():
            return

        query = self.input_field.text().strip()
        if not query:
            return

        model = self.app_state.get("selected_model")
        if not model:
            self.status_lbl.setText("No active model selected in settings.")
            return

        self._was_stopped = False
        self.last_query = query
        self.full_response = ""
        self.response_browser.clear()
        self.separator.setVisible(True)
        self.response_browser.setVisible(True)
        self.footer_widget.setVisible(True)
        self.stop_btn.setVisible(True)
        self.status_lbl.setText(f"Asking {model}...")
        self.input_field.setReadOnly(True)
        self.adjustSize()

        # Build prompt
        preset_id = self.app_state.get("active_preset", "general")
        preset = get_preset(preset_id)
        sys_prompt = preset.get("system_prompt", "You are a helpful local AI assistant.")
        
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": query}
        ]

        self.worker = StreamWorker(self.client, model, messages, options={"temperature": 0.7})
        self.worker.chunk_received.connect(self._on_chunk)
        self.worker.generation_finished.connect(self._on_finished)
        self.worker.generation_error.connect(self._on_error)
        self.worker.start()

    @Slot(str)
    def _on_chunk(self, chunk: str):
        self.full_response += chunk
        self.response_browser.setMarkdown(self.full_response)
        scrollbar = self.response_browser.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @Slot(str)
    def _on_finished(self, full_text: str):
        self.stop_btn.setVisible(False)
        self.input_field.setReadOnly(False)
        if not self._was_stopped:
            self.status_lbl.setText("✓ Finished")
        if not self.full_response and full_text:
            self.full_response = full_text
            self.response_browser.setMarkdown(full_text)

    @Slot(str)
    def _on_error(self, err_msg: str):
        self.stop_btn.setVisible(False)
        self.input_field.setReadOnly(False)
        self.status_lbl.setText(f"Error: {err_msg}")

    def _on_stop(self):
        if self.worker and self.worker.isRunning():
            self._was_stopped = True
            self.worker.stop()
            self.stop_btn.setVisible(False)
            self.input_field.setReadOnly(False)
            self.status_lbl.setText("■ Stopped")

    def _on_copy(self):
        if self.full_response:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.full_response)
            prev_text = self.copy_btn.text()
            self.copy_btn.setText("✓ Copied!")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText(prev_text))

    def _on_promote_to_full_chat(self):
        if not self.chat_manager or not self.last_query:
            return

        model = self.app_state.get("selected_model")
        preset = self.app_state.get("active_preset", "general")
        
        # Build a title from the query
        words = self.last_query.split()
        short_title = " ".join(words[:4]) + ("..." if len(words) > 4 else "")
        title = f"Quick: {short_title}"

        conv_id = self.chat_manager.conv_repo.create_conversation(title, model, preset=preset)
        self.chat_manager.msg_repo.create_message(conv_id, "user", self.last_query)
        if self.full_response:
            self.chat_manager.msg_repo.create_message(conv_id, "assistant", self.full_response)

        # Load into main UI
        self.chat_manager.load_conversation(conv_id)
        self.chat_promoted.emit(conv_id)
        self.close()
