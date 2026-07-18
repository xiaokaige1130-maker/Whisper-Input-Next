"""Lightweight Markdown-backed personal memory for rewriting and quick replies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_STYLE = """# 我的表达风格

- 直接、简洁，优先使用自然中文。
- 保留原文中的人名、数字、地址、代码和技术名词。
- 不添加没有明确说过的事实。
"""

DEFAULT_COMMON_REPLIES = """# 收到

- 收到，我看一下。

# 稍后回复

- 我先处理一下，确认后回复你。

# 跟进

- 这个事情现在进展到哪一步了？
"""

_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_LIST_ITEM = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
_ALNUM_TOKEN = re.compile(r"[a-z0-9_+#.-]{2,}")
_CHINESE_RUN = re.compile(r"[\u3400-\u9fff]+")
_QUICK_REPLY_PREFIX = re.compile(
    r"^\s*(?:快捷回复|固定回复|回复模板)\s*[:：]?\s*(.*?)\s*[。.!！?？]?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MemoryContext:
    style: str = ""
    common_reply: str = ""
    knowledge: tuple[tuple[str, str], ...] = ()

    def render(self) -> str:
        sections: list[str] = []
        if self.style:
            sections.append(f"## 我的表达风格\n{self.style}")
        if self.common_reply:
            sections.append(f"## 相关固定回复\n{self.common_reply}")
        for name, content in self.knowledge:
            sections.append(f"## 相关资料：{name}\n{content}")
        return "\n\n".join(sections)


class PersonalMemoryStore:
    def __init__(self, root: Path | str = "data/memory") -> None:
        self.root = Path(root)
        self.style_path = self.root / "style.md"
        self.common_replies_path = self.root / "common_replies.md"
        self.knowledge_dir = self.root / "knowledge"
        self._initialize()

    def _initialize(self) -> None:
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        if not self.style_path.exists():
            self._atomic_write(self.style_path, DEFAULT_STYLE)
        if not self.common_replies_path.exists():
            self._atomic_write(self.common_replies_path, DEFAULT_COMMON_REPLIES)

    def load_style(self) -> str:
        return self._read(self.style_path)

    def save_style(self, content: str) -> None:
        self._atomic_write(self.style_path, content.strip() + "\n")

    def load_common_replies(self) -> str:
        return self._read(self.common_replies_path)

    def save_common_replies(self, content: str) -> None:
        self._atomic_write(self.common_replies_path, content.strip() + "\n")

    def knowledge_files(self) -> list[Path]:
        return sorted(
            (
                path
                for path in self.knowledge_dir.glob("*.md")
                if path.is_file()
            ),
            key=lambda path: path.name.casefold(),
        )

    def resolve_quick_reply(self, text: str) -> str:
        match = _QUICK_REPLY_PREFIX.match(text or "")
        if match is None:
            return text

        query = match.group(1).strip()
        sections = self._reply_sections(self.load_common_replies())
        if not query or not sections:
            return text

        ranked = sorted(
            (
                (
                    self._score(query, f"{title}\n" + "\n".join(replies)),
                    title,
                    replies,
                )
                for title, replies in sections
            ),
            key=lambda item: (-item[0], item[1]),
        )
        score, _title, replies = ranked[0]
        if score <= 0 or not replies:
            return text
        return replies[0]

    def context_for(
        self,
        text: str,
        *,
        max_chars: int = 3200,
        max_knowledge_notes: int = 2,
    ) -> MemoryContext:
        limit = max(500, min(int(max_chars), 12_000))
        style = self._strip_heading(self.load_style())
        common_reply = self._best_reply_section(text)

        ranked_notes: list[tuple[int, str, str]] = []
        for path in self.knowledge_files():
            content = self._read(path)
            score = self._score(text, f"{path.stem}\n{content}")
            if score > 0:
                ranked_notes.append((score, path.stem, content))
        ranked_notes.sort(key=lambda item: (-item[0], item[1]))

        remaining = limit
        style = style[:remaining].strip()
        remaining -= len(style)
        common_reply = common_reply[: max(0, remaining)].strip()
        remaining -= len(common_reply)

        selected: list[tuple[str, str]] = []
        for _score, name, content in ranked_notes[: max(0, max_knowledge_notes)]:
            if remaining <= 0:
                break
            trimmed = content[:remaining].strip()
            if trimmed:
                selected.append((name, trimmed))
                remaining -= len(trimmed)

        return MemoryContext(
            style=style,
            common_reply=common_reply,
            knowledge=tuple(selected),
        )

    def _best_reply_section(self, text: str) -> str:
        ranked = sorted(
            (
                (
                    self._score(text, f"{title}\n" + "\n".join(replies)),
                    title,
                    replies,
                )
                for title, replies in self._reply_sections(
                    self.load_common_replies()
                )
            ),
            key=lambda item: (-item[0], item[1]),
        )
        if not ranked or ranked[0][0] <= 0:
            return ""
        _score, title, replies = ranked[0]
        return f"### {title}\n" + "\n".join(f"- {reply}" for reply in replies)

    @staticmethod
    def _reply_sections(content: str) -> list[tuple[str, list[str]]]:
        sections: list[tuple[str, list[str]]] = []
        title = ""
        replies: list[str] = []
        for line in content.splitlines():
            heading = _HEADING.match(line)
            if heading:
                if title and replies:
                    sections.append((title, replies))
                title = heading.group(1).strip()
                replies = []
                continue
            item = _LIST_ITEM.match(line)
            if item and title:
                reply = item.group(1).strip()
                if reply:
                    replies.append(reply)
        if title and replies:
            sections.append((title, replies))
        return sections

    @classmethod
    def _score(cls, query: str, candidate: str) -> int:
        normalized_query = (query or "").casefold().strip()
        normalized_candidate = (candidate or "").casefold()
        if not normalized_query or not normalized_candidate:
            return 0

        score = 0
        if normalized_query in normalized_candidate:
            score += 100
        query_tokens = cls._tokens(normalized_query)
        candidate_tokens = cls._tokens(normalized_candidate)
        score += len(query_tokens & candidate_tokens) * 8
        return score

    @staticmethod
    def _tokens(text: str) -> set[str]:
        tokens = set(_ALNUM_TOKEN.findall(text))
        for run in _CHINESE_RUN.findall(text):
            if len(run) == 1:
                tokens.add(run)
                continue
            tokens.update(run[index : index + 2] for index in range(len(run) - 1))
        return tokens

    @staticmethod
    def _strip_heading(content: str) -> str:
        lines = content.splitlines()
        if lines and _HEADING.match(lines[0]):
            lines = lines[1:]
        return "\n".join(lines).strip()

    @staticmethod
    def _read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)
