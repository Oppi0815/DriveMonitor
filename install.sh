#!/usr/bin/env bash
set -euo pipefail
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$HOME/.local/share/drivemonitor"
BIN="$HOME/.local/bin"
APP="$HOME/.local/share/applications"
mkdir -p "$TARGET" "$BIN" "$APP"
rm -rf "$TARGET/drivemonitor" "$TARGET/icons"
cp -a "$SOURCE_DIR/drivemonitor" "$TARGET/"
cp -a "$SOURCE_DIR/icons" "$TARGET/"
cp "$SOURCE_DIR/drivemonitor.py" "$TARGET/drivemonitor.py"
cat > "$BIN/drivemonitor" <<EOF
#!/usr/bin/env bash
exec /usr/bin/python3 "$TARGET/drivemonitor.py" "\$@"
EOF
chmod +x "$BIN/drivemonitor" "$TARGET/drivemonitor.py"
cat > "$APP/drivemonitor.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=DriveMonitor Professional
Comment=Gesundheitsmonitor für Laufwerke und Hardware unter Linux
Exec=$BIN/drivemonitor
Icon=$TARGET/icons/drivemonitor-128.png
Terminal=false
Categories=System;Utility;
StartupNotify=true
EOF
chmod 644 "$APP/drivemonitor.desktop"
echo "DriveMonitor Professional 5.0.0 wurde für den Benutzer installiert."
echo "Für passwortfreie SMART-Daten bitte einmalig ./smart-berechtigung-einrichten.sh ausführen."
