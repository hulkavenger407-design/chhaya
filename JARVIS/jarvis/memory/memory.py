"""
jarvis/memory/memory.py

JARVIS Memory System
--------------------
Short-term : Last N messages in current session (in-memory list)
Long-term  : ChromaDB vector store — persists across sessions
Episodic   : SQLite log — task history, outcomes, timings
"""

import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path


# ── Paths ─────────────────────────────────────────────────────
MEMORY_PATH  = os.getenv("JARVIS_MEMORY_PATH", "./jarvis/data/memory")
LOG_PATH     = os.getenv("JARVIS_LOG_PATH",    "./jarvis/data/logs")
DB_PATH      = os.path.join(LOG_PATH, "jarvis_log.db")

Path(MEMORY_PATH).mkdir(parents=True, exist_ok=True)
Path(LOG_PATH).mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# SHORT-TERM MEMORY  (session only, in-memory)
# ══════════════════════════════════════════════════════════════

class ShortTermMemory:
    """Stores the last N messages of the current session."""

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self.messages: list = []
        self.user_name: str = "Sir"
        self.session_start = datetime.now().isoformat()

    def add(self, role: str, content: str):
        """Add a message. role = 'user' or 'assistant'"""
        self.messages.append({
            "role":      role,
            "content":   content,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last N messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_recent(self, n: int = 6) -> list:
        """Return last n messages as (role, content) tuples."""
        recent = self.messages[-n:] if len(self.messages) >= n else self.messages
        return [(m["role"], m["content"]) for m in recent]

    def set_user_name(self, name: str):
        self.user_name = name
        print(f"  [Memory] User name set to: {name}")

    def clear(self):
        self.messages = []
        print("  [Memory] Short-term memory cleared.")


# ══════════════════════════════════════════════════════════════
# LONG-TERM MEMORY  (ChromaDB — persists across sessions)
# ══════════════════════════════════════════════════════════════

class LongTermMemory:
    """
    Stores memories as vector embeddings in ChromaDB.
    Uses simple hash-based embeddings so no GPU or internet needed.
    When online + API available, can upgrade to better embeddings.
    """

    def __init__(self):
        self._db = None
        self._collection = None
        self._ready = False
        self._init_db()

    def _init_db(self):
        try:
            import chromadb
            self._db = chromadb.PersistentClient(path=MEMORY_PATH)
            self._collection = self._db.get_or_create_collection(
                name="jarvis_memory",
                metadata={"hnsw:space": "cosine"}
            )
            self._ready = True
            print(f"  [Memory] Long-term memory loaded — {self._collection.count()} memories stored.")
        except Exception as e:
            print(f"  [Memory] ChromaDB unavailable: {e}. Long-term memory disabled.")
            self._ready = False

    def remember(self, content: str, metadata: dict = None):
        """Store a memory."""
        if not self._ready:
            return
        try:
            meta = metadata or {}
            meta["timestamp"] = datetime.now().isoformat()
            meta["content_preview"] = content[:100]

            # Use simple ID based on timestamp
            mem_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

            self._collection.add(
                documents=[content],
                metadatas=[meta],
                ids=[mem_id]
            )
        except Exception as e:
            print(f"  [Memory] Failed to store memory: {e}")

    def recall(self, query: str, n: int = 3) -> list[str]:
        """Search memory by meaning. Returns list of relevant memories."""
        if not self._ready or self._collection.count() == 0:
            return []
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n, self._collection.count())
            )
            return results["documents"][0] if results["documents"] else []
        except Exception as e:
            print(f"  [Memory] Recall failed: {e}")
            return []

    def count(self) -> int:
        if not self._ready:
            return 0
        return self._collection.count()

    def clear(self):
        if not self._ready:
            return
        try:
            self._db.delete_collection("jarvis_memory")
            self._collection = self._db.get_or_create_collection("jarvis_memory")
            print("  [Memory] Long-term memory cleared.")
        except Exception as e:
            print(f"  [Memory] Clear failed: {e}")


# ══════════════════════════════════════════════════════════════
# EPISODIC MEMORY  (SQLite — task log)
# ══════════════════════════════════════════════════════════════

class EpisodicMemory:
    """
    Logs every task JARVIS performs.
    Tracks: task type, success, duration, errors.
    Used for self-improvement analysis.
    """

    def __init__(self):
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT,
                    task_type   TEXT,
                    input       TEXT,
                    success     INTEGER,
                    duration_ms INTEGER,
                    error       TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  [Memory] SQLite init failed: {e}")

    def log_task(self, task_type: str, user_input: str,
                 success: bool, duration_ms: int, error: str = None):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                INSERT INTO task_log
                (timestamp, task_type, input, success, duration_ms, error)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                task_type,
                user_input[:200],
                1 if success else 0,
                duration_ms,
                error
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  [Memory] Log failed: {e}")

    def get_stats(self) -> dict:
        """Returns task success rates by type."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute("""
                SELECT task_type,
                       COUNT(*) as total,
                       SUM(success) as successes,
                       AVG(duration_ms) as avg_ms
                FROM task_log
                GROUP BY task_type
            """)
            rows = cursor.fetchall()
            conn.close()
            return {
                row[0]: {
                    "total":    row[1],
                    "success":  row[2],
                    "avg_ms":   round(row[3]) if row[3] else 0
                }
                for row in rows
            }
        except:
            return {}

    def save_user_pref(self, key: str, value: str):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                INSERT OR REPLACE INTO user_profile (key, value) VALUES (?, ?)
            """, (key, value))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  [Memory] Save pref failed: {e}")

    def get_user_pref(self, key: str) -> str | None:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute(
                "SELECT value FROM user_profile WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except:
            return None


# ══════════════════════════════════════════════════════════════
# JARVIS MEMORY  (unified interface)
# ══════════════════════════════════════════════════════════════

class JARVISMemory:
    """
    Single interface to all three memory systems.
    This is what the agent uses — not the individual classes.
    """

    def __init__(self):
        print("  [Memory] Initialising memory systems...")
        self.short  = ShortTermMemory(max_messages=20)
        self.long   = LongTermMemory()
        self.log    = EpisodicMemory()

        # Load saved user name if exists
        saved_name = self.log.get_user_pref("user_name")
        if saved_name:
            self.short.set_user_name(saved_name)
            print(f"  [Memory] Welcome back, {saved_name}.")

    def add_exchange(self, user_input: str, assistant_response: str,
                     task_type: str = "chat", success: bool = True,
                     duration_ms: int = 0):
        """Record a full exchange to all memory systems."""
        # Short-term
        self.short.add("user", user_input)
        self.short.add("assistant", assistant_response)

        # Long-term — store meaningful exchanges only
        if len(user_input) > 20:
            self.long.remember(
                f"User asked: {user_input}\nJARVIS replied: {assistant_response[:200]}",
                metadata={"task_type": task_type, "success": str(success)}
            )

        # Episodic log
        self.log.log_task(task_type, user_input, success, duration_ms)

        # Auto-detect user name
        self._detect_name(user_input)

    def get_context(self, query: str) -> str:
        """
        Returns relevant context string for the current query.
        Combines recent conversation + relevant long-term memories.
        """
        context_parts = []

        # Relevant long-term memories
        memories = self.long.recall(query, n=2)
        if memories:
            context_parts.append("Relevant past context:\n" + "\n".join(memories))

        return "\n\n".join(context_parts)

    def get_recent_messages(self, n: int = 6) -> list:
        return self.short.get_recent(n)

    def _detect_name(self, text: str):
        """Detect if user mentioned their name."""
        import re
        patterns = [
            r"(?:my name is|i am|i'm|call me)\s+([A-Z][a-z]+)",
            r"(?:name's)\s+([A-Z][a-z]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).capitalize()
                if name.lower() not in ("jarvis", "sir", "an", "the", "a"):
                    self.short.set_user_name(name)
                    self.log.save_user_pref("user_name", name)
                    break

    @property
    def user_name(self) -> str:
        return self.short.user_name

    def status(self) -> str:
        return (f"Short-term: {len(self.short.messages)} messages | "
                f"Long-term: {self.long.count()} memories | "
                f"User: {self.short.user_name}")


# Global singleton
_memory = None

def get_memory() -> JARVISMemory:
    global _memory
    if _memory is None:
        _memory = JARVISMemory()
    return _memory
