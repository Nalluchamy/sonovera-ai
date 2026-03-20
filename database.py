import sqlite3
from typing import List, Dict
from typing import List, Dict, Any

class ChatDatabase:
    """
    Simple SQLite database for persistent chat history.
    """
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self._create_table()

    def _create_table(self) -> None:
        """Creates the messages table if it doesn't already exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    audio TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_message(self, user_id: str, role: str, content: str, audio: str = None) -> None:
        """Adds a new message to the database for a specific user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (user_id, role, content, audio) VALUES (?, ?, ?, ?)",
                (user_id, role, content, audio)
            )
            conn.commit()

    def get_all_messages(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves all chat messages for a specific user from the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT role, content, audio, timestamp FROM messages WHERE user_id = ? ORDER BY timestamp ASC", (user_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def clear_user_history(self, user_id: str) -> None:
        """Clears all messages for a specific user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            conn.commit()
