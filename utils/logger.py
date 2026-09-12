import os
import logging
from logging.handlers import RotatingFileHandler
from utils.resource_path import get_user_state_dir

# Define the log directory and file path
LOG_DIR = get_user_state_dir()
LOG_FILE = os.path.join(LOG_DIR, "rootChat.log")

def setup_logger():
    """Initializes and configures the application logger."""
    # Ensure config/log directory exists
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create log directory {LOG_DIR}: {e}")
        # Fallback to local directory if user directory is not writable
        os.makedirs("logs", exist_ok=True)
        global LOG_FILE
        LOG_FILE = os.path.join("logs", "rootChat.log")

    logger = logging.getLogger("rootChat")
    logger.setLevel(logging.DEBUG)

    # Prevent adding duplicate handlers if setup_logger is called multiple times
    if logger.handlers:
        return logger

    # Formatter for the logs
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating File Handler (Max 5MB per file, keep 3 backup files)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create file log handler: {e}")

    logger.info("Logging initialized. Log file path: %s", LOG_FILE)
    return logger

# Get the logger instance
logger = setup_logger()
