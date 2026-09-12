import os
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Slot, Qt, Signal
from utils.resource_path import get_resource_path
from utils.logger import logger


class RootChatTrayIcon(QSystemTrayIcon):
    """System tray integration for Linux desktop with quick actions and notifications."""
    
    new_chat_requested = Signal()
    mini_chat_requested = Signal()
    settings_requested = Signal()

    def __init__(self, main_window, app_state, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.app_state = app_state

        # Load icon
        icon_path = get_resource_path("resources/icons/rootChat.png")
        if not os.path.exists(icon_path):
            icon_path = get_resource_path("resources/icons/rootChat.svg")
        
        self.setIcon(QIcon(icon_path))
        self.setToolTip("rootChat — Private AI for Linux")

        self.init_menu()
        self.activated.connect(self._on_activated)
        self.messageClicked.connect(self._on_message_clicked)

    def init_menu(self):
        self.menu = QMenu()
        self.menu.setObjectName("TrayMenu")

        # Toggle Show / Hide
        self.toggle_action = QAction("Show rootChat", self)
        self.toggle_action.triggered.connect(self._toggle_window)
        self.menu.addAction(self.toggle_action)

        self.menu.addSeparator()

        # New Chat
        self.new_chat_action = QAction("New Chat", self)
        self.new_chat_action.triggered.connect(self._on_new_chat)
        self.menu.addAction(self.new_chat_action)

        # Quick Mini-Chat
        self.mini_chat_action = QAction("⚡ Quick Mini-Chat", self)
        self.mini_chat_action.triggered.connect(self._on_mini_chat)
        self.menu.addAction(self.mini_chat_action)

        self.menu.addSeparator()

        # Settings
        self.settings_action = QAction("⚙ Settings", self)
        self.settings_action.triggered.connect(self._on_settings)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        # Quit
        self.quit_action = QAction("Quit rootChat", self)
        self.quit_action.triggered.connect(self._quit_app)
        self.menu.addAction(self.quit_action)

        self.setContextMenu(self.menu)

    def _toggle_window(self):
        if self.main_window.isVisible() and not self.main_window.isMinimized():
            self.main_window.hide()
            self.toggle_action.setText("Show rootChat")
        else:
            self._show_and_activate_window()

    def _show_and_activate_window(self):
        self.main_window.showNormal()
        self.main_window.activateWindow()
        self.main_window.raise_()
        self.toggle_action.setText("Hide rootChat")

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._toggle_window()

    def _on_message_clicked(self):
        self._show_and_activate_window()

    def _on_new_chat(self):
        self._show_and_activate_window()
        self.new_chat_requested.emit()

    def _on_mini_chat(self):
        self.mini_chat_requested.emit()

    def _on_settings(self):
        self._show_and_activate_window()
        self.settings_requested.emit()

    def _quit_app(self):
        logger.info("Quitting application via system tray.")
        self.hide()
        QApplication.quit()

    def notify_response_ready(self, model: str, summary: str = ""):
        """Displays a desktop notification when an AI response finishes in the background."""
        if not self.app_state.get("notifications_enabled", True):
            return

        title = "rootChat — Response Ready"
        preview = summary.strip().replace("\n", " ")
        if len(preview) > 120:
            preview = preview[:117] + "..."
        message = f"[{model}] {preview}" if preview else f"Response from {model} is complete."

        try:
            self.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                4000
            )
            logger.debug("Tray notification shown: %s", message)
        except Exception as e:
            logger.warning("Could not display tray notification: %s", e)
