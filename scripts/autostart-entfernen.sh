#!/usr/bin/env bash
set -euo pipefail

USER_NAME="${SUDO_USER:-$USER}"
USER_HOME="$(getent passwd "$USER_NAME" | cut -d: -f6)"

rm -f "$USER_HOME/.config/autostart/drivemonitor.desktop"

echo "Zum Entfernen der Systemdateien wird einmal das Administratorpasswort benötigt."
sudo rm -f /etc/polkit-1/rules.d/49-drivemonitor.rules
sudo rm -f /usr/local/bin/drivemonitor-launch
sudo rm -rf /opt/drivemonitor

echo
echo "Der automatische Start und die passwortfreie Freigabe wurden entfernt."
