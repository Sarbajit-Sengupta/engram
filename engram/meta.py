import sqlite3
import uuid
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MetaStore:
    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id               TEXT PRIMARY KEY,
                dataset          TEXT NOT NULL,
                text             TEXT NOT NULL,
                strength         REAL DEFAULT 1.0,
                created_at       TEXT NOT NULL,
                last_accessed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS datasets (
                name       TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                item_count INTEGER DEFAULT 0
            );
        """)
        self._conn.commit()

    def insert(self, text: str, dataset: str) -> str:
        memory_id = str(uuid.uuid4())
        now = _now()
        self._conn.execute(
            "INSERT INTO memories (id, dataset, text, strength, created_at, last_accessed_at)"
            " VALUES (?, ?, ?, 1.0, ?, ?)",
            (memory_id, dataset, text, now, now),
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO datasets (name, created_at, item_count) VALUES (?, ?, 0)",
            (dataset, now),
        )
        self._conn.execute(
            "UPDATE datasets SET item_count = item_count + 1 WHERE name = ?",
            (dataset,),
        )
        self._conn.commit()
        return memory_id

    def get_by_ids(self, ids: list[str]) -> list[dict]:
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        rows = self._conn.execute(
            f"SELECT * FROM memories WHERE id IN ({placeholders})", ids  # nosec B608 — placeholders is "?,?,?" not user input
        ).fetchall()
        return [dict(r) for r in rows]

    def update_accessed(self, memory_id: str, new_strength: float):
        self._conn.execute(
            "UPDATE memories SET last_accessed_at = ?, strength = ? WHERE id = ?",
            (_now(), new_strength, memory_id),
        )
        self._conn.commit()

    def get_all_in_dataset(self, dataset: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE dataset = ?", (dataset,)
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_by_ids(self, ids: list[str]):
        if not ids:
            return
        placeholders = ",".join("?" * len(ids))
        self._conn.execute(
            f"DELETE FROM memories WHERE id IN ({placeholders})", ids  # nosec B608 — placeholders is "?,?,?" not user input
        )
        self._conn.commit()

    def delete_dataset(self, dataset: str):
        self._conn.execute("DELETE FROM memories WHERE dataset = ?", (dataset,))
        self._conn.execute("DELETE FROM datasets WHERE name = ?", (dataset,))
        self._conn.commit()

    def list_datasets(self) -> list[dict]:
        return [dict(r) for r in self._conn.execute("SELECT * FROM datasets").fetchall()]
