#!/usr/bin/env bash
set -euo pipefail
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
USER_HOME="$(getent passwd "$USER_NAME" | cut -d: -f6)"
TARGET_DIR="$USER_HOME/.local/share/drivemonitor"
APP_DIR="$USER_HOME/.local/share/applications"

command -v python3 >/dev/null || { echo "Python 3 fehlt."; exit 1; }
command -v smartctl >/dev/null || { echo "smartmontools fehlt. Bitte installieren: sudo apt install smartmontools"; exit 1; }

"$SOURCE_DIR/pruefen.sh"
mkdir -p "$TARGET_DIR" "$APP_DIR"
cp -a "$SOURCE_DIR/drivemonitor.py" "$SOURCE_DIR/drivemonitor_app" "$SOURCE_DIR/icons" "$TARGET_DIR/"
chmod +x "$TARGET_DIR/drivemonitor.py"

cat > "$APP_DIR/drivemonitor.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=DriveMonitor 4.5.1 Professional
Comment=SMART- und Temperaturüberwachung für Linux
Exec=/usr/bin/python3 $TARGET_DIR/drivemonitor.py
Icon=$TARGET_DIR/icons/drivemonitor-128.png
Terminal=false
Categories=System;Utility;
StartupNotify=true
EOF
chmod 644 "$APP_DIR/drivemonitor.desktop"

sudo install -d -m 755 /usr/local/libexec
sudo install -o root -g root -m 755 "$SOURCE_DIR/helpers/drivemonitor-smartctl" /usr/local/libexec/drivemonitor-smartctl
RULE_TMP="$(mktemp)"
cat > "$RULE_TMP" <<EOF
polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.policykit.exec" &&
        action.lookup("program") == "/usr/local/libexec/drivemonitor-smartctl" &&
        subject.user == "$USER_NAME" && subject.local && subject.active) {
        return polkit.Result.YES;
    }
});
EOF
sudo install -o root -g root -m 644 "$RULE_TMP" /etc/polkit-1/rules.d/49-drivemonitor.rules
rm -f "$RULE_TMP"
chown -R "$USER_NAME:$USER_NAME" "$TARGET_DIR" "$APP_DIR/drivemonitor.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true

echo
echo "DriveMonitor 4.5.1 Professional wurde installiert."
echo "Die Oberfläche läuft als normaler Benutzer; nur der geprüfte SMART-Helfer erhält Root-Rechte."
echo "Start über das Linux-Mint-Menü oder:"
echo "  python3 $TARGET_DIR/drivemonitor.py"
