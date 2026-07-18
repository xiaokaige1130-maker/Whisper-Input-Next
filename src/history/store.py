"""SQLite-backed transcription history available even when audio archiving is off."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from time import monotonic
from typing import Optional


@dataclass(frozen=True)
class TranscriptionRecord:
    id: int
    created_at: str
    text: str
    service: str
    model: str
    mode: str
    duration_seconds: Optional[float]
    latency_seconds: Optional[float]
    audio_path: Optional[str]
    status: str
    error: Optional[str]
    attempt: int


class HistoryStore:
    def __init__(
        self,
        path: Path | str = "data/history.db",
        *,
        retention_days: int | None = None,
        max_records: int | None = None,
    ) -> None:
        self.path = Path(path)
        self.retention_days = self._positive_or_zero(retention_days)
        self.max_records = self._positive_or_zero(max_records)
        self._last_cleanup_at = 0.0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self.maybe_cleanup(force=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    text TEXT NOT NULL DEFAULT '',
                    service TEXT NOT NULL DEFAULT 'unknown',
                    model TEXT NOT NULL DEFAULT 'unknown',
                    mode TEXT NOT NULL DEFAULT 'transcriptions',
                    duration_seconds REAL,
                    latency_seconds REAL,
                    audio_path TEXT,
                    status TEXT NOT NULL DEFAULT 'success',
                    error TEXT,
                    attempt INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at
                ON transcriptions(created_at DESC)
                """
            )

    def add_success(
        self,
        *,
        text: str,
        service: str,
        model: str,
        mode: str = "transcriptions",
        duration_seconds: float | None = None,
        latency_seconds: float | None = None,
        audio_path: str | None = None,
        attempt: int = 1,
    ) -> int:
        return self._insert(
            text=text,
            service=service,
            model=model,
            mode=mode,
            duration_seconds=duration_seconds,
            latency_seconds=latency_seconds,
            audio_path=audio_path,
            status="success",
            error=None,
            attempt=attempt,
        )

    def add_failure(
        self,
        *,
        error: str,
        service: str,
        model: str,
        mode: str = "transcriptions",
        duration_seconds: float | None = None,
        latency_seconds: float | None = None,
        audio_path: str | None = None,
        attempt: int = 1,
    ) -> int:
        return self._insert(
            text="",
            service=service,
            model=model,
            mode=mode,
            duration_seconds=duration_seconds,
            latency_seconds=latency_seconds,
            audio_path=audio_path,
            status="failure",
            error=error,
            attempt=attempt,
        )

    def _insert(
        self,
        *,
        text: str,
        service: str,
        model: str,
        mode: str,
        duration_seconds: float | None,
        latency_seconds: float | None,
        audio_path: str | None,
        status: str,
        error: str | None,
        attempt: int,
    ) -> int:
        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO transcriptions (
                    created_at, text, service, model, mode,
                    duration_seconds, latency_seconds, audio_path,
                    status, error, attempt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    text,
                    service or "unknown",
                    model or "unknown",
                    mode or "transcriptions",
                    duration_seconds,
                    latency_seconds,
                    audio_path,
                    status,
                    error,
                    max(1, attempt),
                ),
            )
            record_id = int(cursor.lastrowid)
        self.maybe_cleanup()
        return record_id

    def recent(
        self,
        limit: int = 100,
        query: str = "",
        *,
        offset: int = 0,
    ) -> list[TranscriptionRecord]:
        limit = max(1, min(1000, limit))
        offset = max(0, offset)
        where_sql, parameters = self._search_clause(query)
        sql = (
            f"SELECT * FROM transcriptions{where_sql} "
            "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        )
        parameters.extend([limit, offset])

        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [TranscriptionRecord(**dict(row)) for row in rows]

    def count(self, query: str = "") -> int:
        where_sql, parameters = self._search_clause(query)
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS total FROM transcriptions{where_sql}",
                parameters,
            ).fetchone()
        return int(row["total"] or 0)

    def successful_texts(self, *, days: int = 7, limit: int = 5000) -> list[str]:
        limit = max(1, min(100_000, int(limit)))
        clauses = ["status = 'success'", "text != ''"]
        parameters: list[object] = []
        if days > 0:
            cutoff = (
                datetime.now().astimezone() - timedelta(days=int(days))
            ).isoformat(timespec="seconds")
            clauses.append("created_at >= ?")
            parameters.append(cutoff)
        parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT text FROM transcriptions
                WHERE {' AND '.join(clauses)}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [str(row["text"]) for row in rows]

    def configure_retention(
        self,
        *,
        retention_days: int | None,
        max_records: int | None,
    ) -> int:
        self.retention_days = self._positive_or_zero(retention_days)
        self.max_records = self._positive_or_zero(max_records)
        return self.maybe_cleanup(force=True)

    def maybe_cleanup(self, *, force: bool = False) -> int:
        if not self.retention_days and not self.max_records:
            return 0
        now = monotonic()
        if not force and now - self._last_cleanup_at < 24 * 60 * 60:
            return 0
        self._last_cleanup_at = now
        return self.cleanup(
            retention_days=self.retention_days,
            max_records=self.max_records,
        )

    def cleanup(
        self,
        *,
        retention_days: int | None = None,
        max_records: int | None = None,
    ) -> int:
        retention_days = self._positive_or_zero(retention_days)
        max_records = self._positive_or_zero(max_records)
        with self._connect() as connection:
            before = connection.total_changes
            if retention_days:
                cutoff = (
                    datetime.now().astimezone() - timedelta(days=retention_days)
                ).isoformat(timespec="seconds")
                connection.execute(
                    "DELETE FROM transcriptions WHERE created_at < ?",
                    (cutoff,),
                )
            if max_records:
                connection.execute(
                    """
                    DELETE FROM transcriptions
                    WHERE id NOT IN (
                        SELECT id
                        FROM transcriptions
                        ORDER BY created_at DESC, id DESC
                        LIMIT ?
                    )
                    """,
                    (max_records,),
                )
            return connection.total_changes - before

    def stats_today(self) -> dict[str, float | int]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success,
                    AVG(CASE WHEN status = 'success' THEN latency_seconds END) AS avg_latency,
                    SUM(CASE WHEN status = 'success' THEN duration_seconds ELSE 0 END) AS duration
                FROM transcriptions
                WHERE date(created_at, 'localtime') = date('now', 'localtime')
                """
            ).fetchone()
        total = int(row["total"] or 0)
        success = int(row["success"] or 0)
        return {
            "total": total,
            "success": success,
            "success_rate": (success / total * 100.0) if total else 0.0,
            "avg_latency": float(row["avg_latency"] or 0.0),
            "duration": float(row["duration"] or 0.0),
        }

    def delete(self, record_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM transcriptions WHERE id = ?",
                (record_id,),
            )

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM transcriptions")

    @staticmethod
    def _positive_or_zero(value: int | None) -> int:
        if value is None:
            return 0
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _search_clause(query: str) -> tuple[str, list[object]]:
        if not query.strip():
            return "", []
        pattern = f"%{query.strip()}%"
        return (
            " WHERE text LIKE ? OR service LIKE ? OR model LIKE ?",
            [pattern, pattern, pattern],
        )
