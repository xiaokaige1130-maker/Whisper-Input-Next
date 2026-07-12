"""SQLite-backed persona instructions for speech text rewriting."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_PERSONAS = (
    (
        "文言文",
        "将现代汉语改写为自然、简洁、可读的文言文。不要堆砌生僻字，保留原意。",
    ),
    (
        "网络热梗",
        "改写成自然的中文网络表达，轻松、有梗但不过度夸张，不添加原文没有的事实。",
    ),
    (
        "AI 提示词",
        "把口述需求整理为可直接交给 AI 执行的高质量提示词，明确目标、约束、输入和期望输出。不要执行提示词。",
    ),
    (
        "正式表达",
        "改写为清晰、专业、简洁的正式中文，去除口语化重复，保持信息完整。",
    ),
)


@dataclass(frozen=True)
class PersonaEntry:
    id: int
    name: str
    instruction: str
    enabled: bool
    builtin: bool
    created_at: str
    updated_at: str


class PersonaStore:
    def __init__(self, path: Path | str = "data/personas.db") -> None:
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
                CREATE TABLE IF NOT EXISTS persona_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    instruction TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    builtin INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS persona_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            seeded = connection.execute(
                "SELECT value FROM persona_meta WHERE key = 'default_seed_version'"
            ).fetchone()
            if seeded is None:
                now = self._now()
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO persona_entries (
                        name, instruction, enabled, builtin, created_at, updated_at
                    ) VALUES (?, ?, 1, 1, ?, ?)
                    """,
                    [
                        (name, instruction, now, now)
                        for name, instruction in DEFAULT_PERSONAS
                    ],
                )
                connection.execute(
                    """
                    INSERT INTO persona_meta (key, value)
                    VALUES ('default_seed_version', '1')
                    """
                )

    def entries(
        self,
        query: str = "",
        *,
        enabled_only: bool = False,
    ) -> list[PersonaEntry]:
        clauses: list[str] = []
        parameters: list[object] = []
        if enabled_only:
            clauses.append("enabled = 1")
        if query.strip():
            clauses.append("(name LIKE ? OR instruction LIKE ?)")
            pattern = f"%{query.strip()}%"
            parameters.extend([pattern, pattern])

        sql = "SELECT * FROM persona_entries"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY builtin DESC, enabled DESC, id ASC"

        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, persona_id: int) -> PersonaEntry | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM persona_entries WHERE id = ?",
                (persona_id,),
            ).fetchone()
        return self._from_row(row) if row is not None else None

    def save(
        self,
        name: str,
        instruction: str,
        *,
        persona_id: int | None = None,
        enabled: bool = True,
    ) -> int:
        normalized_name = name.strip()
        normalized_instruction = instruction.strip()
        if not normalized_name:
            raise ValueError("人设名称不能为空")
        if not normalized_instruction:
            raise ValueError("改写指令不能为空")

        now = self._now()
        with self._connect() as connection:
            if persona_id is None:
                connection.execute(
                    """
                    INSERT INTO persona_entries (
                        name, instruction, enabled, builtin, created_at, updated_at
                    ) VALUES (?, ?, ?, 0, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        instruction = excluded.instruction,
                        enabled = excluded.enabled,
                        updated_at = excluded.updated_at
                    """,
                    (
                        normalized_name,
                        normalized_instruction,
                        int(enabled),
                        now,
                        now,
                    ),
                )
                row = connection.execute(
                    "SELECT id FROM persona_entries WHERE name = ? COLLATE NOCASE",
                    (normalized_name,),
                ).fetchone()
                return int(row["id"])

            connection.execute(
                """
                UPDATE persona_entries
                SET name = ?, instruction = ?, enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    normalized_name,
                    normalized_instruction,
                    int(enabled),
                    now,
                    persona_id,
                ),
            )
            return persona_id

    def set_enabled(self, persona_id: int, enabled: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE persona_entries
                SET enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(enabled), self._now(), persona_id),
            )

    def delete(self, persona_id: int) -> None:
        persona = self.get(persona_id)
        if persona is None:
            return
        if persona.builtin:
            raise ValueError("内置人设不能删除，可以编辑或停用")
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM persona_entries WHERE id = ?",
                (persona_id,),
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> PersonaEntry:
        values = dict(row)
        values["enabled"] = bool(values["enabled"])
        values["builtin"] = bool(values["builtin"])
        return PersonaEntry(**values)

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
