"""Lightweight, on-demand agent for personal memory and glossary upkeep."""

from __future__ import annotations

import json
import re
import subprocess
import webbrowser
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.glossary import GlossaryStore
from src.history import HistoryStore
from src.memory import PersonalMemoryStore
from src.utils.logger import logger


_SPACED_ACRONYM = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z]\s+){1,}[A-Za-z](?![A-Za-z0-9])"
)
_LATIN_TOKEN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9.+#_-]{3,}(?![A-Za-z0-9])")
_GLOSSARY_COMMAND = re.compile(
    r"^\s*(?:以后)?(?:我说|听到)?\s*(.+?)\s*"
    r"(?:统一写成|改成|替换成|纠正为)\s*(.+?)\s*[。.!！?？]?\s*$",
    re.IGNORECASE,
)
_REMEMBER_COMMAND = re.compile(
    r"^\s*(?:请)?(?:记住|记到知识库|加入知识库)\s*[:：]?\s*(.+?)\s*[。.!！?？]?\s*$",
    re.IGNORECASE,
)
_ORGANIZE_COMMAND = re.compile(
    r"^\s*(?:帮我)?整理(?:最近)?"
    r"(一天|七天|三十天|全部)?(?:的)?(?:历史记录|历史)?(?:里的)?"
    r"(?:词库|知识库)\s*[。.!！?？]?\s*$"
)
_OPEN_COMMAND = re.compile(
    r"^\s*打开\s*(GitHub|YouTube|Codex|Grok|微信|QQ)\s*[。.!！?？]?\s*$",
    re.IGNORECASE,
)

_AMBIGUOUS_TOKENS = {"codecs", "glock", "rock", "local", "home"}
_OPEN_TARGETS = {
    "github": ("url", "https://github.com"),
    "youtube": ("url", "https://www.youtube.com"),
    "codex": ("desktop", "codex-desktop.desktop"),
    "grok": ("desktop", "grok-desktop.desktop"),
    "微信": ("desktop", "wechat.desktop"),
    "qq": ("desktop", "qq.desktop"),
}


@dataclass(frozen=True)
class GlossarySuggestion:
    source: str
    replacement: str
    count: int
    confidence: str
    reason: str


@dataclass(frozen=True)
class AgentResult:
    message: str
    action: str
    changed_count: int = 0


class KnowledgeAgent:
    def __init__(
        self,
        history: HistoryStore | None = None,
        glossary: GlossaryStore | None = None,
        memory: PersonalMemoryStore | None = None,
        *,
        root: Path | str = "data/agent",
        opener: Callable[[str, str], None] | None = None,
    ) -> None:
        self.history = history or HistoryStore()
        self.glossary = glossary or GlossaryStore()
        self.memory = memory or PersonalMemoryStore()
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.suggestions_path = self.root / "glossary_suggestions.json"
        self._opener = opener or self._open_target

    def execute(
        self,
        text: str,
        *,
        default_days: int = 7,
        automation: str = "semi",
    ) -> AgentResult:
        normalized = (text or "").strip()
        if not normalized:
            return AgentResult("Agent 没有收到有效指令。", "none")

        match = _OPEN_COMMAND.match(normalized)
        if match:
            label = match.group(1)
            key = label.casefold() if label.isascii() else label
            target = _OPEN_TARGETS.get(key)
            if target is None:
                return AgentResult(f"没有配置“{label}”的启动方式。", "open")
            self._opener(*target)
            return AgentResult(f"已打开 {label}。", "open")

        match = _GLOSSARY_COMMAND.match(normalized)
        if match:
            source = match.group(1).strip(" “”,，")
            replacement = match.group(2).strip(" “”,，")
            if not source or not replacement:
                return AgentResult("词库指令缺少口述形式或标准写法。", "glossary")
            self.glossary.save(source, replacement)
            return AgentResult(
                f"已记住：{source} → {replacement}",
                "glossary",
                1,
            )

        match = _REMEMBER_COMMAND.match(normalized)
        if match:
            note = match.group(1).strip()
            if not note:
                return AgentResult("没有找到需要保存的知识内容。", "remember")
            self._append_knowledge(note)
            return AgentResult("已加入小凯哥知识库。", "remember", 1)

        match = _ORGANIZE_COMMAND.match(normalized)
        if match:
            days = {
                "一天": 1,
                "七天": 7,
                "三十天": 30,
                "全部": 0,
            }.get(match.group(1), max(0, int(default_days)))
            suggestions = self.analyze_history(days=days)
            changed = 0
            if automation in {"semi", "auto"}:
                candidates = (
                    suggestion
                    for suggestion in suggestions
                    if automation == "auto" or suggestion.confidence == "high"
                )
                for suggestion in candidates:
                    self.glossary.save(
                        suggestion.source,
                        suggestion.replacement,
                    )
                    changed += 1
            return AgentResult(
                (
                    f"历史扫描完成，发现 {len(suggestions)} 条候选，"
                    f"已加入 {changed} 条高置信规则。"
                ),
                "organize",
                changed,
            )

        return AgentResult(
            "没有识别出知识库指令。可以说“整理最近七天词库”或"
            "“以后我说 X 统一写成 Y”。",
            "unknown",
        )

    def analyze_history(self, *, days: int = 7) -> list[GlossarySuggestion]:
        texts = self.history.successful_texts(days=days)
        existing = {
            entry.source.casefold()
            for entry in self.glossary.entries()
        }
        counts: Counter[tuple[str, str, str]] = Counter()

        for text in texts:
            for match in _SPACED_ACRONYM.finditer(text):
                source = match.group(0).strip()
                replacement = re.sub(r"\s+", "", source).upper()
                if len(replacement) < 2:
                    continue
                counts[(source, replacement, "逐字母口述")] += 1

        canonical_terms = {
            entry.replacement
            for entry in self.glossary.entries(enabled_only=True)
            if entry.source.casefold() == entry.replacement.casefold()
            and _LATIN_TOKEN.fullmatch(entry.replacement)
        }
        for text in texts:
            for token in _LATIN_TOKEN.findall(text):
                folded = token.casefold()
                if folded in _AMBIGUOUS_TOKENS:
                    continue
                for canonical in canonical_terms:
                    if folded == canonical.casefold():
                        continue
                    distance = self._edit_distance(folded, canonical.casefold())
                    if distance <= 1:
                        counts[(token, canonical, "接近常用专名")] += 1

        suggestions: list[GlossarySuggestion] = []
        for (source, replacement, reason), count in counts.most_common():
            if source.casefold() in existing or source.casefold() == replacement.casefold():
                continue
            confidence = "high" if reason == "逐字母口述" and count >= 2 else "medium"
            suggestions.append(
                GlossarySuggestion(
                    source=source,
                    replacement=replacement,
                    count=count,
                    confidence=confidence,
                    reason=reason,
                )
            )
        self._save_suggestions(suggestions)
        return suggestions

    def load_suggestions(self) -> list[GlossarySuggestion]:
        try:
            payload = json.loads(self.suggestions_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return []
        return [
            GlossarySuggestion(**item)
            for item in payload.get("suggestions", [])
            if isinstance(item, dict)
        ]

    def _save_suggestions(self, suggestions: list[GlossarySuggestion]) -> None:
        payload = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "suggestions": [asdict(item) for item in suggestions],
        }
        temp = self.suggestions_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.suggestions_path)

    def _append_knowledge(self, note: str) -> None:
        path = self.memory.knowledge_dir / "agent_notes.md"
        existing = path.read_text(encoding="utf-8") if path.exists() else "# Agent 记录\n"
        line = f"- {note.strip()}\n"
        if line not in existing:
            temp = path.with_name(f".{path.name}.tmp")
            temp.write_text(existing.rstrip() + "\n" + line, encoding="utf-8")
            temp.replace(path)

    @staticmethod
    def _open_target(kind: str, target: str) -> None:
        if kind == "url":
            webbrowser.open(target, new=2)
            return
        desktop_id = target.removesuffix(".desktop")
        subprocess.Popen(
            ["gtk-launch", desktop_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    @staticmethod
    def _edit_distance(left: str, right: str) -> int:
        previous = list(range(len(right) + 1))
        for left_index, left_char in enumerate(left, start=1):
            current = [left_index]
            for right_index, right_char in enumerate(right, start=1):
                current.append(
                    min(
                        current[-1] + 1,
                        previous[right_index] + 1,
                        previous[right_index - 1] + (left_char != right_char),
                    )
                )
            previous = current
        return previous[-1]
