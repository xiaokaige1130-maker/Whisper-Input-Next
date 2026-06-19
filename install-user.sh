#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DESKTOP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"
LOCAL_BIN="$HOME/.local/bin"

mkdir -p "$APP_DESKTOP_DIR" "$AUTOSTART_DIR" "$LOCAL_BIN"

chmod +x "$APP_DIR/launch-control-ui.sh" "$APP_DIR/launch-service.sh" "$APP_DIR/start.sh"

ln -sf "$APP_DIR/launch-control-ui.sh" "$LOCAL_BIN/whisper-input-control"
ln -sf "$APP_DIR/launch-service.sh" "$LOCAL_BIN/whisper-input-start"

cat > "$APP_DESKTOP_DIR/whisper-input-control.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Whisper Input 控制台
Comment=启动、停止和调试 AI 语音输入
Exec=$APP_DIR/launch-control-ui.sh
Icon=$APP_DIR/assets/icons/whisper-input.png
Terminal=false
Categories=Utility;
StartupNotify=true
EOF

cat > "$AUTOSTART_DIR/whisper-input-service.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Whisper Input Service
Comment=Start AI voice input service after login
Exec=$APP_DIR/launch-service.sh
Icon=$APP_DIR/assets/icons/whisper-input.png
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

chmod +x "$APP_DESKTOP_DIR/whisper-input-control.desktop" "$AUTOSTART_DIR/whisper-input-service.desktop"
update-desktop-database "$APP_DESKTOP_DIR" >/dev/null 2>&1 || true

echo "Installed Whisper Input user app."
echo "Open it from the application menu: Whisper Input 控制台"
echo "CLI commands: whisper-input-control, whisper-input-start"
