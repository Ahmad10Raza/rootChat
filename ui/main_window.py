from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QPushButton, QStackedWidget, QFrame, QApplication,
    QMenu, QMessageBox, QSystemTrayIcon, QSizePolicy
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from core.ollama_client import OllamaClient
from core.app_state import AppState
from core.ollama_worker import OllamaConnectionWorker, OllamaModelsWorker
from ui.sidebar import Sidebar
from ui.status_bar import StatusBar
from ui.model_selector import ModelSelector
from ui.preset_selector import PresetSelector
from ui.chat_window import ChatWindow
from ui.toast import Toast
from core.chat_manager import ChatManager
from database.database import DatabaseManager
from database.repositories.conversation_repository import ConversationRepository
from database.repositories.message_repository import MessageRepository
from utils.logger import logger
from utils.resource_path import get_app_icon

class MainWindow(QMainWindow):
    """Main application window coordinates UI pages, layout, and background threads."""
    
    def __init__(self, app_state: AppState, client: OllamaClient, db_manager: DatabaseManager):
        super().__init__()
        # Repositories & Phase 4 Modules
        from database.repositories.memory_repository import MemoryRepository
        from database.repositories.document_repository import DocumentRepository
        from core.memory_manager import MemoryManager
        from core.context_manager import ContextManager
        from core.document_manager import DocumentManager
        from documents.embeddings.ollama_embeddings import OllamaEmbeddings
        from retrieval.local_vector_store import LocalVectorStore
        from retrieval.retriever import Retriever
        
        self.app_state = app_state
        self.client = client
        self.db_manager = db_manager
        
        self.conv_repo = ConversationRepository(self.db_manager)
        self.msg_repo = MessageRepository(self.db_manager)
        self.mem_repo = MemoryRepository(self.db_manager)
        self.doc_repo = DocumentRepository(self.db_manager)
        
        # RAG / Knowledge Components
        self.embeddings = OllamaEmbeddings(self.client, model_name=self.app_state.get("embedding_model", "nomic-embed-text"))
        self.vector_store = LocalVectorStore(self.doc_repo)
        self.retriever = Retriever(self.embeddings, self.vector_store)
        self.document_manager = DocumentManager(self.app_state, self.doc_repo, self.embeddings)
        
        # Managers
        self.memory_manager = MemoryManager(self.app_state, self.mem_repo)
        self.context_manager = ContextManager(self.app_state, self.memory_manager, self.msg_repo, self.retriever)
        self.chat_manager = ChatManager(self.app_state, self.client, self.db_manager, self.memory_manager, self.context_manager)
        
        self.setWindowTitle("rootChat")
        self.setWindowIcon(get_app_icon())
        self.setMinimumSize(800, 500)
        
        # Track background threads
        self.connection_worker = None
        self.models_worker = None
        self.workers = []

        self.init_ui()
        self._setup_shortcuts()
        self._setup_tray_icon()
        self.check_ollama_connection()

    def init_ui(self):
        # Main stacked container
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # ============ CONNECTED PAGE ============
        self.main_page = QWidget()
        main_layout = QVBoxLayout(self.main_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Horizontal: Sidebar + Content
        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar(self.chat_manager, self.document_manager)
        self.sidebar.settings_requested.connect(self._open_settings)
        self.sidebar.sidebar_toggled.connect(lambda c: self.app_state.set("sidebar_collapsed", c))
        if self.app_state.get("sidebar_collapsed", False):
            self.sidebar.set_collapsed(True)
        content_layout.addWidget(self.sidebar)

        # Right side: Top bar + Chat
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Top Bar
        top_bar = QWidget()
        top_bar.setObjectName("TopBar")
        top_bar.setFixedHeight(54)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(14, 0, 14, 0)
        top_bar_layout.setSpacing(8)

        # Model Selector
        self.model_selector = ModelSelector()
        self.model_selector.model_changed.connect(self._on_model_selected)
        self.model_selector.refresh_requested.connect(self.fetch_models)
        self.model_selector.manage_requested.connect(self._open_model_manager)
        top_bar_layout.addWidget(self.model_selector)

        # Separator between Model and Persona
        sep1 = QFrame()
        sep1.setObjectName("TopBarSeparator")
        sep1.setFixedSize(1, 20)
        top_bar_layout.addWidget(sep1)

        # Persona Selector
        self.preset_selector = PresetSelector()
        self.preset_selector.preset_changed.connect(self._on_preset_selected)
        self.preset_selector.set_preset(self.app_state.get("active_preset", "general"))
        top_bar_layout.addWidget(self.preset_selector)
        
        top_bar_layout.addStretch(1)

        # Right Action Buttons
        self.mini_chat_btn = QPushButton("⚡ Mini Chat")
        self.mini_chat_btn.setObjectName("TopBarMiniChatBtn")
        self.mini_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mini_chat_btn.setToolTip("Quick spotlight-style query (Ctrl+Space)")
        self.mini_chat_btn.setFixedHeight(30)
        self.mini_chat_btn.clicked.connect(self._open_mini_chat)
        top_bar_layout.addWidget(self.mini_chat_btn)

        self.export_btn = QPushButton("📤 Export")
        self.export_btn.setObjectName("TopBarBtn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setToolTip("Export the active chat to Markdown, Text, or JSON")
        self.export_btn.setFixedHeight(30)
        self.export_btn.clicked.connect(self._on_export_current_chat)
        top_bar_layout.addWidget(self.export_btn)

        self.shortcuts_btn = QPushButton("⌨")
        self.shortcuts_btn.setObjectName("TopBarIconBtn")
        self.shortcuts_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.shortcuts_btn.setToolTip("Keyboard Shortcuts (Ctrl+/ or ?)")
        self.shortcuts_btn.setFixedSize(30, 30)
        self.shortcuts_btn.clicked.connect(self._open_shortcuts_dialog)
        top_bar_layout.addWidget(self.shortcuts_btn)

        # Separator before status
        sep2 = QFrame()
        sep2.setObjectName("TopBarSeparator")
        sep2.setFixedSize(1, 20)
        top_bar_layout.addWidget(sep2)

        # Connection status pill badge
        self.conn_pill = QFrame()
        self.conn_pill.setObjectName("ConnectionPill")
        self.conn_pill.setFixedHeight(26)
        self.conn_pill.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        conn_layout = QHBoxLayout(self.conn_pill)
        conn_layout.setContentsMargins(8, 0, 8, 0)
        conn_layout.setSpacing(4)

        self.conn_dot = QLabel("●")
        self.conn_dot.setStyleSheet("color: #FF5555; font-size: 8px;")
        self.conn_label = QLabel("Connecting...")
        self.conn_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #FF5555;")
        conn_layout.addWidget(self.conn_dot)
        conn_layout.addWidget(self.conn_label)
        top_bar_layout.addWidget(self.conn_pill)

        right_layout.addWidget(top_bar)

        # Chat Window
        self.chat_window = ChatWindow(self.chat_manager)
        right_layout.addWidget(self.chat_window, 1)

        content_layout.addWidget(right_panel, 1)

        # Listen for conversation changes
        self.app_state.state_changed.connect(self._on_state_changed)

        main_layout.addWidget(content_container, 1)

        # Status bar
        self.status_bar = StatusBar()
        main_layout.addWidget(self.status_bar)

        # Wire chat manager to status bar
        self.chat_manager.generation_started.connect(lambda: self.status_bar.set_generation_active(True))
        self.chat_manager.stats_received.connect(self.status_bar.update_generation_stats)
        self.chat_manager.generation_stopped.connect(lambda: self.status_bar.set_generation_active(False))
        self.chat_manager.message_added.connect(lambda _: self.status_bar.increment_message_count())
        self.chat_manager.message_removed.connect(lambda _: self.status_bar.decrement_message_count())

        self.stacked_widget.addWidget(self.main_page)

        # ============ OFFLINE PAGE ============
        self.offline_page = QWidget()
        self.offline_page.setObjectName("OfflinePage")
        
        offline_layout = QVBoxLayout(self.offline_page)
        offline_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        offline_layout.setSpacing(16)

        self.offline_title = QLabel("Ollama Offline")
        self.offline_title.setObjectName("OfflineTitle")
        self.offline_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        offline_layout.addWidget(self.offline_title)

        self.offline_body = QLabel("")
        self.offline_body.setObjectName("OfflineBody")
        self.offline_body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        offline_layout.addWidget(self.offline_body)

        self.retry_btn = QPushButton("Retry Connection")
        self.retry_btn.setObjectName("RetryBtn")
        self.retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retry_btn.clicked.connect(self.check_ollama_connection)
        offline_layout.addWidget(self.retry_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.start_ollama_btn = QPushButton("Start Ollama")
        self.start_ollama_btn.setObjectName("StartOllamaBtn")
        self.start_ollama_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_ollama_btn.clicked.connect(self.prompt_start_ollama)
        offline_layout.addWidget(self.start_ollama_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.offline_settings_btn = QPushButton("⚙ Open Settings")
        self.offline_settings_btn.setObjectName("OfflineSettingsBtn")
        self.offline_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.offline_settings_btn.clicked.connect(self._open_settings)
        offline_layout.addWidget(self.offline_settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.stacked_widget.addWidget(self.offline_page)
        
        # Toast notification
        self.toast = Toast(self)

    def _setup_shortcuts(self):
        """Register global keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+N"), self, self._shortcut_new_chat)
        QShortcut(QKeySequence("Ctrl+K"), self, self._shortcut_search)
        QShortcut(QKeySequence("Ctrl+B"), self, self.sidebar.toggle_collapse)
        QShortcut(QKeySequence("Ctrl+M"), self, self._open_model_manager)
        QShortcut(QKeySequence("Ctrl+Space"), self, self._open_mini_chat)
        QShortcut(QKeySequence("Ctrl+Shift+Space"), self, self._open_mini_chat)
        QShortcut(QKeySequence("Ctrl+,"), self, self._open_settings)
        QShortcut(QKeySequence("Escape"), self, self._shortcut_stop)
        QShortcut(QKeySequence("Ctrl+/"), self, self._open_shortcuts_dialog)
        QShortcut(QKeySequence("?"), self, self._open_shortcuts_dialog)
        QShortcut(QKeySequence("F1"), self, self._open_shortcuts_dialog)
    
    def _shortcut_new_chat(self):
        self.sidebar._on_new_chat()
    
    def _shortcut_search(self):
        self.sidebar.search_bar.setFocus()
        self.sidebar.search_bar.selectAll()
    
    def _shortcut_stop(self):
        self.chat_manager.stop_generation()

    def _open_shortcuts_dialog(self):
        from ui.shortcuts_dialog import ShortcutsDialog
        dialog = ShortcutsDialog(self)
        dialog.exec()

    def _setup_tray_icon(self):
        from ui.tray_icon import RootChatTrayIcon
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = RootChatTrayIcon(self, self.app_state)
            self.tray_icon.new_chat_requested.connect(self.sidebar._on_new_chat)
            self.tray_icon.mini_chat_requested.connect(self._open_mini_chat)
            self.tray_icon.settings_requested.connect(self._open_settings)
            if self.app_state.get("tray_icon_enabled", True):
                self.tray_icon.show()
        else:
            self.tray_icon = None

        self.chat_manager.generation_finished.connect(self._on_generation_finished)

    def _on_generation_finished(self, full_response: str):
        if self.tray_icon and (self.isMinimized() or not self.isVisible() or not self.isActiveWindow()):
            model = self.app_state.get("selected_model", "Model")
            self.tray_icon.notify_response_ready(model, full_response)

    def check_ollama_connection(self):
        """Launches background worker to check connection status to Ollama."""
        logger.info("Initiating connection check to Ollama server.")
        self.retry_btn.setEnabled(False)
        self.retry_btn.setText("Connecting...")
        
        worker = OllamaConnectionWorker(self.client)
        worker.finished.connect(self._on_connection_check_finished)
        self.workers.append(worker)
        worker.start()

    def prompt_start_ollama(self):
        from PySide6.QtWidgets import QInputDialog, QLineEdit
        
        password, ok = QInputDialog.getText(
            self, 
            "Sudo Required", 
            "Enter your sudo password to start the Ollama system service:",
            QLineEdit.EchoMode.Password
        )
        
        if ok and password:
            self.start_ollama_btn.setEnabled(False)
            self.start_ollama_btn.setText("Starting...")
            
            from core.ollama_worker import OllamaStartWorker
            worker = OllamaStartWorker(password)
            worker.finished.connect(self._on_ollama_start_finished)
            self.workers.append(worker)
            worker.start()

    @Slot(bool, str)
    def _on_ollama_start_finished(self, success: bool, message: str):
        self.start_ollama_btn.setEnabled(True)
        self.start_ollama_btn.setText("Start Ollama")
        
        if success:
            logger.info("Ollama started successfully. Triggering connection check.")
            self.toast.show_message("Ollama service started!", "success")
            self.check_ollama_connection()
        else:
            self.toast.show_message(f"Failed: {message}", "error")

    def _on_state_changed(self, key, value):
        if key == "current_messages":
            self.chat_window.load_messages(value)
            count = len(value) if isinstance(value, list) else 0
            self.status_bar.set_message_count(count)
            if count == 0:
                self.status_bar.reset_session_stats()
        elif key in ("last_memories_used", "last_sources_used"):
            mem = self.app_state.get("last_memories_used", 0)
            src = self.app_state.get("last_sources_used", 0)
            self.status_bar.set_context_stats(mem, src)
        elif key == "active_preset":
            self.preset_selector.set_preset(value)
        elif key == "active_conversation_id":
            self.sidebar.select_conversation(value)
        elif key == "tray_icon_enabled" and self.tray_icon:
            if value:
                self.tray_icon.show()
            else:
                self.tray_icon.hide()

    @Slot(bool, str)
    def _on_connection_check_finished(self, is_connected: bool, message: str):
        """Slot called when the Ollama server connection check QThread returns."""
        self.retry_btn.setEnabled(True)
        self.retry_btn.setText("Retry Connection")
        self.connection_worker = None

        if is_connected:
            logger.info("Ollama is reachable. Showing main UI page.")
            self.app_state.ollama_status = "Connected"
            self.status_bar.update_connection_status(True, "Connected")
            self.conn_dot.setStyleSheet("color: #35C759; font-size: 8px;")
            self.conn_label.setText("Connected")
            self.conn_label.setStyleSheet("color: #35C759; font-size: 11px; font-weight: 600;")
            self.conn_pill.setStyleSheet("#ConnectionPill { background-color: rgba(53, 199, 89, 0.12); border: 1px solid rgba(53, 199, 89, 0.28); border-radius: 14px; }")
            self.stacked_widget.setCurrentWidget(self.main_page)
            self.fetch_models()
        else:
            logger.warning("Ollama is unreachable: %s. Displaying offline screen.", message)
            self.app_state.ollama_status = "Offline"
            self.conn_dot.setStyleSheet("color: #FF5555; font-size: 8px;")
            self.conn_label.setText("Offline")
            self.conn_label.setStyleSheet("color: #FF5555; font-size: 11px; font-weight: 600;")
            self.conn_pill.setStyleSheet("#ConnectionPill { background-color: rgba(255, 85, 85, 0.12); border: 1px solid rgba(255, 85, 85, 0.28); border-radius: 14px; }")
            
            endpoint = self.app_state.ollama_endpoint
            self.offline_body.setText(
                f"Ollama could not be reached at:\n"
                f"{endpoint}\n\n"
                f"Please ensure the Ollama service is running\n"
                f"and verify the URL in settings."
            )
            self.stacked_widget.setCurrentWidget(self.offline_page)

    def fetch_models(self):
        """Launches background worker to fetch installed Ollama models."""
        logger.info("Fetching installed models from Ollama.")
        self.model_selector.set_loading(True)
        
        self.models_worker = OllamaModelsWorker(self.client)
        self.models_worker.finished.connect(self._on_models_fetch_finished)
        self.models_worker.error.connect(self._on_models_fetch_error)
        self.models_worker.start()

    @Slot(list)
    def _on_models_fetch_finished(self, models: list):
        self.models_worker = None
        self.app_state.available_models = models
        self.model_selector.set_loading(False)
        
        selected = self.app_state.selected_model
        self.model_selector.set_models(models, selected)

    @Slot(str)
    def _on_models_fetch_error(self, err_msg: str):
        self.models_worker = None
        self.model_selector.set_loading(False)
        self.model_selector.set_models([])
        logger.error("Failed to retrieve models asynchronously: %s", err_msg)

    @Slot(str)
    def _on_model_selected(self, model_name: str):
        self.app_state.selected_model = model_name
        self.status_bar.update_selected_model(model_name)

    @Slot(str)
    def _on_preset_selected(self, preset_id: str):
        self.app_state.set("active_preset", preset_id)
        conv_id = self.app_state.get("active_conversation_id")
        if conv_id:
            self.conv_repo.update_conversation(conv_id, preset=preset_id)
            logger.info("Updated active conversation %d preset to '%s'", conv_id, preset_id)

    def _open_model_manager(self):
        from ui.model_manager_dialog import ModelManagerDialog
        dialog = ModelManagerDialog(self.client, self.app_state, self)
        dialog.models_updated.connect(self.fetch_models)
        dialog.exec()
        self.fetch_models()

    def _open_mini_chat(self):
        from ui.mini_chat_dialog import MiniChatDialog
        dialog = MiniChatDialog(self.client, self.app_state, self.chat_manager, self)
        dialog.chat_promoted.connect(lambda cid: self.sidebar.load_conversations())
        dialog.exec()

    def _open_settings(self):
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.app_state, self)
        dialog.theme_changed.connect(self._on_theme_changed)
        dialog.endpoint_changed.connect(self.update_endpoint)
        dialog.manage_models_requested.connect(self._open_model_manager)
        dialog.exec()
    
    def _on_theme_changed(self, mode: str):
        from ui.theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.set_mode(mode)
        tm.apply(QApplication.instance())

    @Slot(str)
    def update_endpoint(self, new_endpoint: str):
        self.app_state.ollama_endpoint = new_endpoint
        self.client.set_endpoint(new_endpoint)
        self.check_ollama_connection()

    def _on_export_current_chat(self):
        conv_id = self.app_state.get("active_conversation_id")
        if not conv_id:
            QMessageBox.information(self, "Export Chat", "There is no active conversation to export.")
            return
        conv = self.conv_repo.get_conversation(conv_id)
        if not conv:
            return

        from core.export_manager import prompt_and_export
        menu = QMenu(self)
        md_action = menu.addAction("Export as Markdown (.md)")
        txt_action = menu.addAction("Export as Plain Text (.txt)")
        json_action = menu.addAction("Export as JSON (.json)")

        action = menu.exec(self.export_btn.mapToGlobal(self.export_btn.rect().bottomLeft()))
        fmt = None
        if action == md_action:
            fmt = "markdown"
        elif action == txt_action:
            fmt = "txt"
        elif action == json_action:
            fmt = "json"

        if fmt:
            messages = self.msg_repo.get_messages(conv_id)
            success, path = prompt_and_export(self, conv, messages, export_format=fmt)
            if success:
                self.toast.show_message("Conversation exported successfully!", "success")

    def closeEvent(self, event):
        if (
            getattr(self, "tray_icon", None)
            and self.app_state.get("minimize_to_tray", False)
            and self.app_state.get("tray_icon_enabled", True)
        ):
            event.ignore()
            self.hide()
            if self.app_state.get("notifications_enabled", True):
                self.tray_icon.showMessage(
                    "rootChat",
                    "Application minimized to system tray. Click icon to restore.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        else:
            event.accept()
