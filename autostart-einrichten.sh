#!/usr/bin/env bash
set -euo pipefail
TARGET_DIR="$HOME/.local/share/drivemonitor"
[ -f "$TARGET_DIR/drivemonitor.py" ] || { echo "Bitte zuerst ./installieren.sh ausführen."; exit 1; }
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/drivemonitor.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=DriveMonitor 4.5 Professional
Exec=sh -c 'sleep 8; /usr/bin/python3 "$TARGET_DIR/drivemonitor.py"'
Icon=$TARGET_DIR/icons/drivemonitor-128.png
Terminal=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF
echo "Autostart wurde eingerichtet. DriveMonitor startet als normaler Benutzer."
