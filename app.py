import sys
import os
from PySide6.QtWidgets import QApplication
from utils.logger import logger
from core.app_config import AppConfig
from core.app_state import AppState
from core.ollama_client import OllamaClient
from database.database import DatabaseManager
from ui.main_window import MainWindow
from ui.theme.theme_manager import ThemeManager
from version import __version__

from PySide6.QtGui import QIcon
from utils.resource_path import get_resource_path, get_app_icon, set_linux_process_name

def main():
    # Set Linux process name to rootChat so GNOME Shell and window managers match properly
    set_linux_process_name("rootChat")

    logger.info("=========================================")
    logger.info("Starting LocalChat application v%s (Phase 6)", __version__)
    logger.info("=========================================")
    
    # 1. Initialize Configuration
    try:
        config = AppConfig()
    except Exception as e:
        logger.critical("Failed to initialize AppConfig: %s", e)
        sys.exit(1)

    # 2. Initialize Database
    try:
        db_manager = DatabaseManager()
    except Exception as e:
        logger.critical("Failed to initialize SQLite Database: %s", e)
        sys.exit(1)

    # 3. Create Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("rootChat")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("rootChat")
    
    # Set multi-resolution application icon (16x16 to 512x512)
    app.setWindowIcon(get_app_icon())

    # 4. Apply Theme
    theme_mode = config.get("theme", "dark")
    tm = ThemeManager.instance()
    tm.set_mode(theme_mode)
    tm.apply(app)

    # 5. Initialize Core State and Clients
    ollama_endpoint = config.get("ollama_endpoint", "http://localhost:11434")
    client = OllamaClient(endpoint=ollama_endpoint)
    app_state = AppState(config=config)

    # 6. Create and Display Main Window
    try:
        main_window = MainWindow(app_state=app_state, client=client, db_manager=db_manager)
        main_window.resize(1180, 740)
        main_window.show()
    except Exception as e:
        logger.critical("Failed to initialize MainWindow: %s", e)
        sys.exit(1)

    # 7. Start Qt Event Loop
    logger.info("Starting Qt Event Loop...")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
