import os
import sqlite3
from database.schema import SCHEMA_QUERIES
from utils.logger import logger
from utils.resource_path import get_user_data_dir

DB_DIR = get_user_data_dir()
DB_FILE = os.path.join(DB_DIR, "rootChat.db")

class DatabaseManager:
    """Handles connection and basic operations for the SQLite database."""
    
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self._migrate_old_paths()
        self.initialize_database()

    def _migrate_old_paths(self):
        if self.db_path != DB_FILE:
            return
        old_db_path = os.path.expanduser("~/.config/rootChat/rootChat.db")
        if os.path.exists(old_db_path) and not os.path.exists(self.db_path):
            try:
                import shutil
                shutil.copy2(old_db_path, self.db_path)
                logger.info(f"Migrated database from {old_db_path} to {self.db_path}")
            except Exception as e:
                logger.error(f"Failed to migrate database: {e}")

    def get_connection(self):
        """Returns a connection to the SQLite database with row factory enabled."""
        try:
            # Enable foreign keys for the connection
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn
        except sqlite3.Error as e:
            logger.error("Failed to connect to SQLite database at %s: %s", self.db_path, e)
            raise

    def initialize_database(self):
        """Creates the database directory and initializes schema tables."""
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception as e:
                logger.error("Could not create database directory %s: %s", db_dir, e)

        logger.info("Initializing SQLite database at %s", self.db_path)
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Execute schema creation queries
            for query in SCHEMA_QUERIES:
                cursor.execute(query)
                
            # Migrations for Phase 3 & Presets
            cursor.execute("PRAGMA table_info(conversations);")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'is_pinned' not in columns:
                cursor.execute("ALTER TABLE conversations ADD COLUMN is_pinned BOOLEAN DEFAULT 0;")
            if 'is_archived' not in columns:
                cursor.execute("ALTER TABLE conversations ADD COLUMN is_archived BOOLEAN DEFAULT 0;")
            if 'preset' not in columns:
                cursor.execute("ALTER TABLE conversations ADD COLUMN preset TEXT DEFAULT 'general';")
                
            cursor.execute("PRAGMA table_info(memories);")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'is_enabled' not in columns and len(columns) > 0:
                cursor.execute("ALTER TABLE memories ADD COLUMN is_enabled BOOLEAN DEFAULT 1;")
            if 'source' not in columns and len(columns) > 0:
                cursor.execute("ALTER TABLE memories ADD COLUMN source TEXT DEFAULT 'user';")
            
            conn.commit()
            logger.info("Database tables initialized successfully.")
        except sqlite3.Error as e:
            logger.critical("SQLite database initialization failed: %s", e)
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(self, query, params=(), commit=False):
        """Executes a single SQL query, optionally committing changes."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
                result = cursor.lastrowid
            else:
                result = cursor.fetchall()
            return result
        except sqlite3.Error as e:
            logger.error("Database query error: '%s' with params %s: %s", query, params, e)
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def execute_transaction(self, operations: list):
        """
        Executes multiple SQL operations in a single atomic transaction.
        operations: list of tuples (query, params)
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            for query, params in operations:
                cursor.execute(query, params)
            conn.commit()
        except sqlite3.Error as e:
            logger.error("Database transaction error: %s", e)
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

