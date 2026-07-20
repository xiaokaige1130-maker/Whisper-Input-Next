"""Manage the long-running voice service and its log files."""

from __future__ import annotations

import re
import shlex
import subprocess
from datetime import datetime
from pathlib import Path


_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class ServiceManager:
    def __init__(
        self,
        root: Path,
        *,
        session_name: str = "whisper-input",
    ) -> None:
        self.root = Path(root)
        self.session_name = session_name
        self.log_dir = self.root / "logs"

    def run(
        self,
        args: list[str],
        *,
        timeout: int = 10,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=self.root,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )

    def is_running(self) -> bool:
        try:
            result = self.run(
                ["tmux", "has-session", "-t", self.session_name],
                timeout=5,
            )
        except FileNotFoundError:
            # tmux missing (dev machine / partial install) → treat as stopped.
            return False
        return result.returncode == 0

    def start(self) -> tuple[bool, str]:
        if self.is_running():
            return True, "语音输入服务已经在运行。"

        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_file = self.log_dir / (
            f"Whisper-Input-Next-{datetime.now():%Y%m%d-%H%M%S}.log"
        )
        command = (
            f"cd {shlex.quote(str(self.root))} && "
            "source .venv/bin/activate && "
            f"python main.py 2>&1 | tee {shlex.quote(str(log_file))}"
        )
        result = self.run(
            [
                "tmux",
                "new-session",
                "-d",
                "-s",
                self.session_name,
                "bash",
                "-lc",
                command,
            ],
            timeout=10,
        )
        if result.returncode != 0:
            return False, (result.stderr or result.stdout or "tmux 启动失败").strip()
        return True, f"服务已启动，日志写入 {log_file.name}。"

    def stop(self) -> tuple[bool, str]:
        if not self.is_running():
            return True, "语音输入服务当前未运行。"

        self.run(
            ["tmux", "send-keys", "-t", self.session_name, "C-c"],
            timeout=5,
        )
        result = self.run(
            ["tmux", "kill-session", "-t", self.session_name],
            timeout=5,
        )
        if result.returncode != 0:
            return False, (result.stderr or result.stdout or "停止失败").strip()
        return True, "语音输入服务已停止。"

    def restart(self) -> tuple[bool, str]:
        stopped, message = self.stop()
        if not stopped:
            return False, message
        return self.start()

    def latest_log(self) -> Path | None:
        logs = sorted(
            self.log_dir.glob("Whisper-Input-Next-*.log"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return logs[0] if logs else None

    def latest_log_lines(self, limit: int = 220) -> tuple[Path | None, list[str]]:
        log_path = self.latest_log()
        if log_path is None:
            return None, []
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        cleaned = [_ANSI_ESCAPE.sub("", line) for line in lines[-limit:]]
        return log_path, cleaned
