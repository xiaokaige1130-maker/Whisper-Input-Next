#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
if pgrep -f "/home/hyk/Whisper-Input-Next/.venv/bin/python /home/hyk/Whisper-Input-Next/control_ui.py|.venv/bin/python control_ui.py" >/dev/null 2>&1; then
  exit 0
fi
exec .venv/bin/python control_ui.py
