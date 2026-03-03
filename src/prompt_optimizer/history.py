"""SQLite-backed prompt history management."""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SCHEMA = """\
CREATE TABLE IF NOT EXISTS prompts (
    id TEXT PRIMARY KEY,
    original TEXT NOT NULL,
    optimized TEXT NOT NULL,
    tags TEXT DEFAULT '',
    scores TEXT DEFAULT '{}',
    mode TEXT DEFAULT 'interactive',
    created_at TEXT NOT NULL
);
"""


class HistoryDB:
    """Manages prompt history in a local SQLite database."""

    def __init__(self, db_path: str = "prompt_history.db"):
        self._path = Path(db_path)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def save(
        self,
        original: str,
        optimized: str,
        tags: str = "",
        scores: str = "{}",
        mode: str = "interactive",
    ) -> str:
        """Save a prompt pair to history. Returns the new record ID."""
        record_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO prompts (id, original, optimized, tags, scores, mode, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (record_id, original, optimized, tags, scores, mode, now),
        )
        self._conn.commit()
        return record_id

    def list_all(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent prompt history entries."""
        rows = self._conn.execute(
            "SELECT * FROM prompts ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search history by original or optimized prompt text."""
        rows = self._conn.execute(
            "SELECT * FROM prompts WHERE original LIKE ? OR optimized LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get(self, record_id: str) -> dict[str, Any] | None:
        """Get a single history entry by ID."""
        row = self._conn.execute(
            "SELECT * FROM prompts WHERE id = ?", (record_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete(self, record_id: str) -> bool:
        """Delete a history entry. Returns True if a row was deleted."""
        cursor = self._conn.execute("DELETE FROM prompts WHERE id = ?", (record_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def close(self):
        """Close the database connection."""
        self._conn.close()
