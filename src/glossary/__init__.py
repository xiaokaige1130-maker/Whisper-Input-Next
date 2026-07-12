"""Custom vocabulary and deterministic text correction."""

from .processor import GlossaryProcessor
from .store import GlossaryEntry, GlossaryStore

__all__ = ["GlossaryEntry", "GlossaryProcessor", "GlossaryStore"]
