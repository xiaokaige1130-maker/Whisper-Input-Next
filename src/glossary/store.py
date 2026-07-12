"""SQLite-backed custom vocabulary storage."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_ENTRIES = (
    ("S S H", "SSH"),
    ("V P S", "VPS"),
    ("香港杠", "香港-"),
)


@dataclass(frozen=True)
class GlossaryEntry:
    id: int
    source: str
    replacement: str
    enabled: bool
    created_at: str
    updated_at: str


class GlossaryStore:
    def __init__(self, path: Path | str = "data/glossary.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS glossary_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    replacement TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS glossary_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            seeded = connection.execute(
                "SELECT value FROM glossary_meta WHERE key = 'default_seed_version'"
            ).fetchone()
            if seeded is None:
                now = self._now()
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO glossary_entries (
                        source, replacement, enabled, created_at, updated_at
                    ) VALUES (?, ?, 1, ?, ?)
                    """,
                    [
                        (source, replacement, now, now)
                        for source, replacement in DEFAULT_ENTRIES
                    ],
                )
                connection.execute(
                    """
                    INSERT INTO glossary_meta (key, value)
                    VALUES ('default_seed_version', '1')
                    """
                )

    def entries(
        self,
        query: str = "",
        *,
        enabled_only: bool = False,
    ) -> list[GlossaryEntry]:
        clauses: list[str] = []
        parameters: list[object] = []
        if enabled_only:
            clauses.append("enabled = 1")
        if query.strip():
            clauses.append("(source LIKE ? OR replacement LIKE ?)")
            pattern = f"%{query.strip()}%"
            parameters.extend([pattern, pattern])

        sql = "SELECT * FROM glossary_entries"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY enabled DESC, updated_at DESC, id DESC"

        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [self._from_row(row) for row in rows]

    def save(
        self,
        source: str,
        replacement: str,
        *,
        entry_id: int | None = None,
        enabled: bool = True,
    ) -> int:
        normalized_source = source.strip()
        normalized_replacement = replacement.strip()
        if not normalized_source:
            raise ValueError("口述形式不能为空")

        now = self._now()
        with self._connect() as connection:
            if entry_id is None:
                connection.execute(
                    """
                    INSERT INTO glossary_entries (
                        source, replacement, enabled, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(source) DO UPDATE SET
                        replacement = excluded.replacement,
                        enabled = excluded.enabled,
                        updated_at = excluded.updated_at
                    """,
                    (
                        normalized_source,
                        normalized_replacement,
                        int(enabled),
                        now,
                        now,
                    ),
                )
                row = connection.execute(
                    "SELECT id FROM glossary_entries WHERE source = ? COLLATE NOCASE",
                    (normalized_source,),
                ).fetchone()
                return int(row["id"])

            connection.execute(
                """
                UPDATE glossary_entries
                SET source = ?, replacement = ?, enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    normalized_source,
                    normalized_replacement,
                    int(enabled),
                    now,
                    entry_id,
                ),
            )
            return entry_id

    def set_enabled(self, entry_id: int, enabled: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE glossary_entries
                SET enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(enabled), self._now(), entry_id),
            )

    def delete(self, entry_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM glossary_entries WHERE id = ?",
                (entry_id,),
            )

    def enabled_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM glossary_entries WHERE enabled = 1"
            ).fetchone()
        return int(row["count"] or 0)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> GlossaryEntry:
        values = dict(row)
        values["enabled"] = bool(values["enabled"])
        return GlossaryEntry(**values)

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
