"""SQLite-backed transcription history available even when audio archiving is off."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
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
    def __init__(self, path: Path | str = "data/history.db") -> None:
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
            return int(cursor.lastrowid)

    def recent(self, limit: int = 100, query: str = "") -> list[TranscriptionRecord]:
        limit = max(1, min(1000, limit))
        sql = "SELECT * FROM transcriptions"
        parameters: list[object] = []
        if query.strip():
            sql += " WHERE text LIKE ? OR service LIKE ? OR model LIKE ?"
            pattern = f"%{query.strip()}%"
            parameters.extend([pattern, pattern, pattern])
        sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
        parameters.append(limit)

        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [TranscriptionRecord(**dict(row)) for row in rows]

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
