from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
LOG_DIR = ROOT / "logs"
SESSION_NAME = "whisper-input"


def run_cmd(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def write_env(updates: dict[str, str]) -> None:
    existing = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    seen: set[str] = set()
    output: list[str] = []

    for line in existing:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            output.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            output.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            output.append(line)

    missing = [key for key in updates if key not in seen]
    if missing and output and output[-1].strip():
        output.append("")
    for key in missing:
        output.append(f"{key}={updates[key]}")

    ENV_PATH.write_text("\n".join(output) + "\n", encoding="utf-8")


class ControlUI(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Whisper Input 控制台")
        self.resize(980, 720)

        self.status_label = QLabel()
        self.detail_label = QLabel()
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)

        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.model_input = QLineEdit()
        self.hotkey_input = QLineEdit()
        self.hotkey_mode = QComboBox()
        self.hotkey_mode.addItems(["hold", "toggle"])
        self.paste_hotkey = QComboBox()
        self.paste_hotkey.addItems(["ctrl+v", "ctrl+shift+v"])
        self.archive_mode = QComboBox()
        self.archive_mode.addItems(["off", "all"])
        self.clean_fillers = QCheckBox("启用口头禅清理")

        self._build_ui()
        self.load_settings()
        self.refresh_status()
        self.refresh_logs()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(2000)

        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.refresh_logs)
        self.log_timer.start(2500)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        status_group = QGroupBox("运行状态")
        status_layout = QVBoxLayout(status_group)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.detail_label)
        root.addWidget(status_group)

        action_layout = QHBoxLayout()
        for text, handler in [
            ("启动", self.start_service),
            ("停止", self.stop_service),
            ("重启", self.restart_service),
            ("测试 ASR", self.test_asr),
            ("清理录音/缓存", self.cleanup_archive),
            ("刷新日志", self.refresh_logs),
        ]:
            button = QPushButton(text)
            button.clicked.connect(handler)
            action_layout.addWidget(button)
        root.addLayout(action_layout)

        config_group = QGroupBox("基础配置")
        config = QGridLayout(config_group)
        config.addWidget(QLabel("DashScope API Key"), 0, 0)
        config.addWidget(self.key_input, 0, 1, 1, 3)
        config.addWidget(QLabel("ASR 模型"), 1, 0)
        config.addWidget(self.model_input, 1, 1)
        config.addWidget(QLabel("触发键"), 1, 2)
        config.addWidget(self.hotkey_input, 1, 3)
        config.addWidget(QLabel("触发模式"), 2, 0)
        config.addWidget(self.hotkey_mode, 2, 1)
        config.addWidget(QLabel("粘贴快捷键"), 2, 2)
        config.addWidget(self.paste_hotkey, 2, 3)
        config.addWidget(QLabel("录音归档"), 3, 0)
        config.addWidget(self.archive_mode, 3, 1)
        config.addWidget(self.clean_fillers, 3, 2)
        save_button = QPushButton("保存配置")
        save_button.clicked.connect(self.save_settings)
        config.addWidget(save_button, 3, 3)
        root.addWidget(config_group)

        self.log_view.setStyleSheet(
            "QPlainTextEdit { background: #1f2933; color: #e5e7eb; "
            "font-family: monospace; font-size: 12px; }"
        )
        root.addWidget(QLabel("最近日志"))
        root.addWidget(self.log_view, stretch=1)

    def is_running(self) -> bool:
        return run_cmd(["tmux", "has-session", "-t", SESSION_NAME]).returncode == 0

    def latest_log(self) -> Path | None:
        logs = sorted(LOG_DIR.glob("Whisper-Input-Next-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        return logs[0] if logs else None

    def refresh_status(self) -> None:
        running = self.is_running()
        env = read_env()
        self.status_label.setText("状态：运行中" if running else "状态：未运行")
        self.status_label.setStyleSheet(f"font-weight: 700; color: {'#15803d' if running else '#b91c1c'};")
        self.detail_label.setText(
            "模型：{model} | 热键：{hotkey} ({mode}) | 粘贴：{paste} | 归档：{archive}".format(
                model=env.get("DASHSCOPE_ASR_MODEL", ""),
                hotkey=env.get("TRANSCRIPTION_HOTKEY", ""),
                mode=env.get("TRANSCRIPTION_HOTKEY_MODE", ""),
                paste=env.get("PASTE_HOTKEY", ""),
                archive=env.get("AUDIO_ARCHIVE_MODE", ""),
            )
        )

    def refresh_logs(self) -> None:
        log = self.latest_log()
        if not log:
            self.log_view.setPlainText("暂无日志")
            return
        try:
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()[-180:]
            self.log_view.setPlainText("\n".join(lines))
            self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())
        except Exception as exc:
            self.log_view.setPlainText(f"读取日志失败：{exc}")

    def load_settings(self) -> None:
        env = read_env()
        self.key_input.setText(env.get("DASHSCOPE_API_KEY", ""))
        self.model_input.setText(env.get("DASHSCOPE_ASR_MODEL", "qwen3-asr-flash"))
        self.hotkey_input.setText(env.get("TRANSCRIPTION_HOTKEY", "alt_r"))
        self.hotkey_mode.setCurrentText(env.get("TRANSCRIPTION_HOTKEY_MODE", "hold"))
        self.paste_hotkey.setCurrentText(env.get("PASTE_HOTKEY", "ctrl+v"))
        self.archive_mode.setCurrentText(env.get("AUDIO_ARCHIVE_MODE", "off"))
        self.clean_fillers.setChecked(env.get("CLEAN_ASR_FILLERS", "false").lower() == "true")

    def save_settings(self) -> None:
        write_env(
            {
                "TRANSCRIPTION_SERVICE": "aliyun",
                "BATCH_TRANSCRIPTION_SERVICE": "aliyun",
                "DASHSCOPE_API_KEY": self.key_input.text().strip(),
                "DASHSCOPE_ASR_MODEL": self.model_input.text().strip() or "qwen3-asr-flash",
                "TRANSCRIPTION_HOTKEY": self.hotkey_input.text().strip() or "alt_r",
                "TRANSCRIPTION_HOTKEY_MODE": self.hotkey_mode.currentText(),
                "PASTE_HOTKEY": self.paste_hotkey.currentText(),
                "AUDIO_ARCHIVE_MODE": self.archive_mode.currentText(),
                "CLEAN_ASR_FILLERS": "true" if self.clean_fillers.isChecked() else "false",
            }
        )
        self.refresh_status()
        QMessageBox.information(self, "已保存", "配置已保存。重启服务后生效。")

    def start_service(self) -> None:
        if self.is_running():
            self.refresh_status()
            QMessageBox.information(self, "已运行", "语音输入服务已经在运行。")
            return
        LOG_DIR.mkdir(exist_ok=True)
        log_file = LOG_DIR / f"Whisper-Input-Next-{datetime.now():%Y%m%d-%H%M%S}.log"
        result = run_cmd(["tmux", "new-session", "-d", "-s", SESSION_NAME], timeout=5)
        if result.returncode != 0:
            QMessageBox.critical(self, "启动失败", result.stderr or result.stdout)
            return
        commands = [
            f"cd {ROOT}",
            "source .venv/bin/activate",
            f"python main.py 2>&1 | tee {log_file}",
        ]
        for command in commands:
            run_cmd(["tmux", "send-keys", "-t", SESSION_NAME, command, "C-m"], timeout=5)
        self.refresh_status()
        self.refresh_logs()

    def stop_service(self) -> None:
        if not self.is_running():
            self.refresh_status()
            return
        run_cmd(["tmux", "send-keys", "-t", SESSION_NAME, "C-c"], timeout=5)
        run_cmd(["tmux", "kill-session", "-t", SESSION_NAME], timeout=5)
        self.refresh_status()

    def restart_service(self) -> None:
        self.stop_service()
        self.start_service()

    def cleanup_archive(self) -> None:
        audio_dir = ROOT / "audio_archive" / "audio"
        removed = 0
        if audio_dir.exists():
            for path in audio_dir.glob("*.wav"):
                path.unlink(missing_ok=True)
                removed += 1
        cache = ROOT / "audio_archive" / "cache.json"
        cache.unlink(missing_ok=True)
        QMessageBox.information(self, "已清理", f"已删除 {removed} 个录音文件，并清理转写缓存。")

    def test_asr(self) -> None:
        script = """
import os
from dotenv import load_dotenv
load_dotenv('.env')
os.environ['SERVICE_PLATFORM'] = 'aliyun'
from src.transcription.whisper import WhisperProcessor
p = WhisperProcessor()
with open('assets/audio/test_audio.wav', 'rb') as f:
    text, error = p.process_audio(f)
print(error or text)
"""
        result = run_cmd([".venv/bin/python", "-c", script], timeout=60)
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode == 0:
            QMessageBox.information(self, "ASR 测试结果", output.strip() or "测试完成")
        else:
            QMessageBox.critical(self, "ASR 测试失败", output.strip() or "未知错误")


if __name__ == "__main__":
    app = QApplication([])
    window = ControlUI()
    window.show()
    app.exec_()
