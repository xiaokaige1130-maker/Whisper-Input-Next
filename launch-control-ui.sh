#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
PID_FILE="$RUNTIME_DIR/whisper-input-control-ui.pid"
LOG_FILE="$RUNTIME_DIR/whisper-input-control-ui.log"

focus_existing_window() {
  if command -v wmctrl >/dev/null 2>&1; then
    wmctrl -x -a "whisper-input-control" >/dev/null 2>&1 && return 0
    wmctrl -a "小凯哥语音输入法" >/dev/null 2>&1 && return 0
  fi

  if command -v xdotool >/dev/null 2>&1; then
    window_id="$(
      xdotool search --class "whisper-input-control" 2>/dev/null | head -n 1 || true
    )"
    if [[ -n "${window_id:-}" ]]; then
      xdotool windowactivate "$window_id" >/dev/null 2>&1 && return 0
    fi
  fi

  return 1
}

if [[ -r "$PID_FILE" ]]; then
  pid="$(cat "$PID_FILE")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    focus_existing_window || true
    exit 0
  fi
  rm -f "$PID_FILE"
fi

for process_dir in /proc/[0-9]*; do
  [[ -r "$process_dir/cmdline" ]] || continue
  mapfile -d '' -t argv < "$process_dir/cmdline" || continue
  [[ "${argv[0]:-}" == *python* ]] || continue
  script_path="${argv[1]:-}"
  process_cwd="$(readlink "$process_dir/cwd" 2>/dev/null || true)"
  if [[ "$script_path" == "$ROOT/control_ui.py" ]] ||
     [[ "$script_path" == "control_ui.py" && "$process_cwd" == "$ROOT" ]]; then
    printf '%s\n' "${process_dir##*/}" > "$PID_FILE"
    focus_existing_window || true
    exit 0
  fi
done

cd "$ROOT"
setsid "$ROOT/.venv/bin/python" "$ROOT/control_ui.py" \
  >>"$LOG_FILE" 2>&1 </dev/null &
printf '%s\n' "$!" > "$PID_FILE"
