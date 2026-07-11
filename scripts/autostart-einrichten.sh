#!/usr/bin/env bash
set -euo pipefail

USER_NAME="${SUDO_USER:-$USER}"
USER_HOME="$(getent passwd "$USER_NAME" | cut -d: -f6)"
SOURCE="$USER_HOME/.local/share/drivemonitor/drivemonitor.py"

if [ ! -f "$SOURCE" ]; then
    echo "DriveMonitor wurde nicht gefunden:"
    echo "$SOURCE"
    echo
    echo "Bitte zuerst DriveMonitor 4.3.1 normal installieren."
    exit 1
fi

echo "DriveMonitor-Autostart wird für Benutzer '$USER_NAME' eingerichtet."
echo "Dafür wird jetzt einmalig das Administratorpasswort benötigt."
echo

sudo install -d -m 755 /opt/drivemonitor
sudo install -o root -g root -m 755 "$SOURCE" /opt/drivemonitor/drivemonitor.py

tmp_wrapper="$(mktemp)"
cat > "$tmp_wrapper" <<'EOF'
#!/usr/bin/env bash
set -e

DISPLAY_ARG="${1:-:0}"
XAUTHORITY_ARG="${2:-}"

export DISPLAY="$DISPLAY_ARG"

if [ -n "$XAUTHORITY_ARG" ] && [ -f "$XAUTHORITY_ARG" ]; then
    export XAUTHORITY="$XAUTHORITY_ARG"
fi

exec /usr/bin/python3 /opt/drivemonitor/drivemonitor.py
EOF
sudo install -o root -g root -m 755 "$tmp_wrapper" /usr/local/bin/drivemonitor-launch
rm -f "$tmp_wrapper"

tmp_rule="$(mktemp)"
cat > "$tmp_rule" <<EOF
polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.policykit.exec" &&
        action.lookup("program") == "/usr/local/bin/drivemonitor-launch" &&
        subject.user == "$USER_NAME" &&
        subject.local == true &&
        subject.active == true) {
        return polkit.Result.YES;
    }
});
EOF
sudo install -o root -g root -m 644 "$tmp_rule" \
    /etc/polkit-1/rules.d/49-drivemonitor.rules
rm -f "$tmp_rule"

mkdir -p "$USER_HOME/.config/autostart"
cat > "$USER_HOME/.config/autostart/drivemonitor.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=DriveMonitor
Comment=Überwacht Temperaturen und SMART-Zustand der Laufwerke
Exec=sh -c 'sleep 8; /usr/bin/pkexec /usr/local/bin/drivemonitor-launch "$DISPLAY" "$XAUTHORITY"'
Terminal=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF

chown "$USER_NAME:$USER_NAME" \
    "$USER_HOME/.config/autostart/drivemonitor.desktop"

echo
echo "Fertig."
echo "DriveMonitor startet künftig etwa 8 Sekunden nach der Anmeldung."
echo "Dabei sollte keine Passwortabfrage mehr erscheinen."
echo
echo "Zum sofortigen Testen:"
echo '  pkexec /usr/local/bin/drivemonitor-launch "$DISPLAY" "$XAUTHORITY"'
