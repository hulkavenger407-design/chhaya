import sqlite3
from chhaya_v2.core.engine.config import settings

class EpisodicMemory:
    """SQLite store for episodic memory."""
    def __init__(self, db_path: str = settings.sqlite_db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def store(self, content: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO episodes (content) VALUES (?)", (content,))

    def retrieve(self, limit: int = 5) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            # We use id DESC to easily get latest inserts since timestamp might be identical in fast tests
            cursor = conn.execute("SELECT content FROM episodes ORDER BY id DESC LIMIT ?", (limit,))
            return [row[0] for row in cursor.fetchall()]
