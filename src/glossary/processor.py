"""Apply enabled glossary entries to recognized text."""

from __future__ import annotations

import re

from src.utils.logger import logger

from .store import GlossaryEntry, GlossaryStore


_ASCII_SOURCE = re.compile(r"^[A-Za-z0-9\s·•._,，、-]+$")
_ASCII_SEPARATOR = r"[\s·•._,，、-]*"


class GlossaryProcessor:
    def __init__(self, store: GlossaryStore | None = None) -> None:
        self.store = store or GlossaryStore()

    def apply(self, text: str) -> str:
        if not text:
            return text

        corrected = text
        entries = sorted(
            self.store.entries(enabled_only=True),
            key=lambda entry: len(self._compact_source(entry.source)),
            reverse=True,
        )
        for entry in entries:
            corrected = self._apply_entry(corrected, entry)

        if corrected != text:
            logger.info("词库纠错: %s -> %s", text, corrected)
        return corrected

    def _apply_entry(self, text: str, entry: GlossaryEntry) -> str:
        pattern = self._compile_pattern(entry.source)
        return pattern.sub(lambda _match: entry.replacement, text)

    @classmethod
    def _compile_pattern(cls, source: str) -> re.Pattern[str]:
        stripped = source.strip()
        compact = cls._compact_source(stripped)
        if compact and _ASCII_SOURCE.fullmatch(stripped):
            body = _ASCII_SEPARATOR.join(re.escape(char) for char in compact)
            return re.compile(
                rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])",
                flags=re.IGNORECASE,
            )

        chunks = [re.escape(chunk) for chunk in re.split(r"\s+", stripped) if chunk]
        body = r"\s*".join(chunks)
        return re.compile(body, flags=re.IGNORECASE)

    @staticmethod
    def _compact_source(source: str) -> str:
        return re.sub(r"[\s·•._,，、-]+", "", source)
