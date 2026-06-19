#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if tmux has-session -t whisper-input 2>/dev/null; then
  exit 0
fi

mkdir -p logs
LOG_FILE="logs/Whisper-Input-Next-$(date +%Y%m%d-%H%M%S).log"
tmux new-session -d -s whisper-input
tmux send-keys -t whisper-input "cd $(pwd)" C-m
tmux send-keys -t whisper-input "source .venv/bin/activate" C-m
tmux send-keys -t whisper-input "python main.py 2>&1 | tee $LOG_FILE" C-m
