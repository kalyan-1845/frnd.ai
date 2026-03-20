"""
Database Layer — Thread-safe SQLite storage for the AI assistant.
Uses connection-per-call pattern for thread safety.
"""
import sqlite3
import threading
from datetime import datetime
import os

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nova_memory.db")

_db_lock = threading.Lock()


class DatabaseManager:
    def __init__(self):
        self.initialize_db()

    def _connect(self):
        """Create a new connection for the current call."""
        return sqlite3.connect(DB_FILE, check_same_thread=False)

    def initialize_db(self):
        """Create all tables if they don't exist."""
        with _db_lock:
            conn = self._connect()
            try:
                c = conn.cursor()

                # 1. Conversations (short-term context, can be cleared per session)
                c.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 2. Long-term memories (facts, preferences, goals, etc.)
                c.execute('''
                    CREATE TABLE IF NOT EXISTS memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT,
                        content TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 3. User profile (key-value store)
                c.execute('''
                    CREATE TABLE IF NOT EXISTS user_profile (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE,
                        value TEXT
                    )
                ''')

                # 4. Command frequency tracker
                c.execute('''
                    CREATE TABLE IF NOT EXISTS command_frequency (
                        command TEXT PRIMARY KEY,
                        count INTEGER DEFAULT 1,
                        last_used DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 5. Project context (key-value for project-related memory)
                c.execute('''
                    CREATE TABLE IF NOT EXISTS project_context (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                conn.commit()
            finally:
                conn.close()

    # --- Conversations ---

    def add_message(self, role, content):
        with _db_lock:
            conn = self._connect()
            try:
                conn.execute("INSERT INTO conversations (role, content) VALUES (?, ?)", (role, content))
                conn.commit()
            finally:
                conn.close()

    def get_recent_history(self, limit=10):
        with _db_lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
                return rows[::-1]
            finally:
                conn.close()

    def clear_conversations(self):
        with _db_lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM conversations")
                conn.commit()
            finally:
                conn.close()

    # --- Long-term Memories ---

    def add_memory(self, category, content):
        with _db_lock:
            conn = self._connect()
            try:
                conn.execute("INSERT INTO memories (category, content) VALUES (?, ?)", (category, content))
                conn.commit()
            finally:
                conn.close()

    def get_memories(self, category=None):
        with _db_lock:
            conn = self._connect()
            try:
                if category:
                    rows = conn.execute(
                        "SELECT content FROM memories WHERE category = ? ORDER BY id DESC", (category,)
                    ).fetchall()
                else:
                    rows = conn.execute("SELECT content FROM memories ORDER BY id DESC").fetchall()
                return [row[0] for row in rows]
            finally:
                conn.close()

    def delete_memory(self, category, content=None):
        """Delete a specific memory or all memories in a category."""
        with _db_lock:
            conn = self._connect()
            try:
                if content:
                    conn.execute("DELETE FROM memories WHERE category = ? AND content = ?", (category, content))
                else:
                    conn.execute("DELETE FROM memories WHERE category = ?", (category,))
                conn.commit()
            finally:
                conn.close()

    def clear_all_memories(self):
        """Wipe all long-term memories."""
        with _db_lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM memories")
                conn.execute("DELETE FROM user_profile")
                conn.execute("DELETE FROM command_frequency")
                conn.execute("DELETE FROM project_context")
                conn.execute("DELETE FROM conversations")
                conn.commit()
            finally:
                conn.close()

    # --- User Profile ---

    def set_profile(self, key, value):
        with _db_lock:
            conn = self._connect()
            try:
                conn.execute("INSERT OR REPLACE INTO user_profile (key, value) VALUES (?, ?)", (key, value))
                conn.commit()
                return True
            except Exception as e:
                print(f"[DB Error] set_profile {key}: {e}")
                return False
            finally:
                conn.close()

    def get_profile(self, key):
        with _db_lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT value FROM user_profile WHERE key = ?", (key,)).fetchone()
                return row[0] if row else None
            finally:
                conn.close()

    def delete_profile(self, key):
        with _db_lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM user_profile WHERE key = ?", (key,))
                conn.commit()
            finally:
                conn.close()

    def get_all_profile(self):
        """Return all profile entries as a dict."""
        with _db_lock:
            conn = self._connect()
            try:
                rows = conn.execute("SELECT key, value FROM user_profile").fetchall()
                return {k: v for k, v in rows}
            finally:
                conn.close()

    # --- Command Frequency ---

    def increment_command(self, command):
        """Track how often a command is used."""
        with _db_lock:
            conn = self._connect()
            try:
                conn.execute('''
                    INSERT INTO command_frequency (command, count, last_used)
                    VALUES (?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(command) DO UPDATE SET
                        count = count + 1,
                        last_used = CURRENT_TIMESTAMP
                ''', (command,))
                conn.commit()
            finally:
                conn.close()

    def get_top_commands(self, limit=5):
        """Return the most frequently used commands."""
        with _db_lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT command, count FROM command_frequency ORDER BY count DESC LIMIT ?", (limit,)
                ).fetchall()
                return rows
            finally:
                conn.close()

    # --- Project Context ---

    def set_project_context(self, key, value):
        with _db_lock:
            conn = self._connect()
            try:
                conn.execute('''
                    INSERT OR REPLACE INTO project_context (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, value))
                conn.commit()
                return True
            except Exception as e:
                print(f"[DB Error] set_project_context {key}: {e}")
                return False
            finally:
                conn.close()

    def get_project_context(self, key):
        with _db_lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT value FROM project_context WHERE key = ?", (key,)).fetchone()
                return row[0] if row else None
            finally:
                conn.close()

    def get_all_project_context(self):
        with _db_lock:
            conn = self._connect()
            try:
                rows = conn.execute("SELECT key, value FROM project_context").fetchall()
                return {k: v for k, v in rows}
            finally:
                conn.close()

    def clear_project_context(self):
        with _db_lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM project_context")
                conn.commit()
            finally:
                conn.close()


# Global Instance
db = DatabaseManager()
