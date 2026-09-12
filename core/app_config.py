import os
import sys
import json
import tempfile
from config.default_config import DEFAULT_CONFIG
from utils.logger import logger
from utils.resource_path import get_user_config_dir

CONFIG_DIR = get_user_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
_DEFAULT_CONFIG_FILE = CONFIG_FILE

class AppConfig:
    """Manages application settings persisted as a local JSON file."""
    
    def __init__(self, config_file: str = None):
        if config_file:
            self.config_file = config_file
        elif os.environ.get("ROOTCHAT_CONFIG_FILE"):
            self.config_file = os.environ.get("ROOTCHAT_CONFIG_FILE")
        elif CONFIG_FILE != _DEFAULT_CONFIG_FILE:
            # CONFIG_FILE was patched by a test runner (e.g. unittest.mock.patch)
            self.config_file = CONFIG_FILE
        elif "unittest" in sys.modules or "pytest" in sys.modules:
            # Auto-isolate unpatched test configs so tests never mutate real user settings
            self.config_file = os.path.join(tempfile.gettempdir(), f"rootchat_test_{id(self)}.json")
        else:
            self.config_file = CONFIG_FILE
        self.config_dir = os.path.dirname(self.config_file)
        self._config = {}
        self.load()

    def load(self):
        """Loads configuration from disk, creating directory/file if needed."""
        # Ensure configuration directory exists
        try:
            os.makedirs(self.config_dir, exist_ok=True)
        except Exception as e:
            logger.error("Could not create config directory %s: %s", self.config_dir, e)

        # Attempt to load existing config file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                
                # Ensure all default keys exist in loaded config
                updated = False
                for key, val in DEFAULT_CONFIG.items():
                    if key not in self._config:
                        self._config[key] = val
                        updated = True
                
                if updated:
                    self.save()
                
                logger.info("Configuration loaded successfully from %s", self.config_file)
            except Exception as e:
                logger.error("Failed to parse config file %s, falling back to defaults: %s", self.config_file, e)
                self._config = DEFAULT_CONFIG.copy()
        else:
            logger.info("Configuration file does not exist, creating default config.")
            self._config = DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        """Saves current configuration to disk."""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4)
            logger.debug("Configuration saved to %s", self.config_file)
        except Exception as e:
            logger.error("Failed to save configuration to %s: %s", self.config_file, e)

    def get(self, key, default=None):
        """Gets a configuration setting."""
        return self._config.get(key, default)

    def set(self, key, value):
        """Sets a configuration setting and saves to disk."""
        if key in self._config and self._config[key] == value:
            return
        self._config[key] = value
        logger.info("Configuration key '%s' updated to '%s'", key, value)
        self.save()

    def reset_to_defaults(self):
        """Resets the settings to default values."""
        self._config = DEFAULT_CONFIG.copy()
        logger.info("Configuration reset to defaults.")
        self.save()
