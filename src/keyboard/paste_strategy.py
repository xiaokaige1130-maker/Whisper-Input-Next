from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TERMINAL_HINTS = (
    "terminal",
    "gnome-terminal",
    "konsole",
    "kitty",
    "alacritty",
    "wezterm",
    "xterm",
    "tilix",
    "terminator",
    "xfce4-terminal",
    "ghostty",
    "foot",
    "tabby",
    "hyper",
    "grok cli",
    "qute cli",
    "qwen cli",
)


@dataclass(frozen=True)
class PasteContext:
    window_class: str = ""
    title: str = ""
    process_name: str = ""

    @property
    def searchable_text(self) -> str:
        return " ".join(
            part.strip().casefold()
            for part in (self.window_class, self.title, self.process_name)
            if part.strip()
        )


def _run_xdotool(*args: str) -> str:
    try:
        result = subprocess.run(
            ["xdotool", *args],
            capture_output=True,
            text=True,
            timeout=0.5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def detect_active_window() -> PasteContext:
    if os.name != "posix" or not os.getenv("DISPLAY"):
        return PasteContext()

    window_id = _run_xdotool("getactivewindow")
    if not window_id:
        return PasteContext()

    window_class = _run_xdotool("getwindowclassname", window_id)
    title = _run_xdotool("getwindowname", window_id)
    pid = _run_xdotool("getwindowpid", window_id)
    process_name = ""
    if pid.isdigit():
        try:
            process_name = (Path("/proc") / pid / "comm").read_text(
                encoding="utf-8",
            ).strip()
        except OSError:
            process_name = ""

    return PasteContext(
        window_class=window_class,
        title=title,
        process_name=process_name,
    )


def is_terminal_context(
    context: PasteContext,
    extra_hints: str = "",
) -> bool:
    searchable = context.searchable_text
    if not searchable:
        return False

    custom_hints = tuple(
        item.strip().casefold()
        for item in extra_hints.replace("，", ",").split(",")
        if item.strip()
    )
    return any(
        hint in searchable
        for hint in (*DEFAULT_TERMINAL_HINTS, *custom_hints)
    )


def resolve_paste_hotkey(
    configured_mode: str,
    system_platform: str,
    *,
    context: PasteContext | None = None,
    extra_hints: str = "",
) -> str:
    mode = (configured_mode or "auto").strip().lower()
    if mode not in {"auto", "smart"}:
        return mode

    platform = (system_platform or "").strip().lower()
    if platform in {"win", "windows"}:
        return "ctrl+v"
    if platform not in {"linux"}:
        return "cmd+v"

    active_context = context if context is not None else detect_active_window()
    if is_terminal_context(active_context, extra_hints):
        return "ctrl+shift+v"

    # Ctrl+Shift+V is the safer fallback when X11 cannot identify the window.
    if not active_context.searchable_text:
        return "ctrl+shift+v"
    return "ctrl+v"
