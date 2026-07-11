#!/usr/bin/env bash
set -euo pipefail
rm -rf "$HOME/.local/share/drivemonitor"
rm -f "$HOME/.local/share/applications/drivemonitor.desktop"
rm -f "$HOME/.config/autostart/drivemonitor.desktop"
echo "Zum Entfernen des geschützten SMART-Helfers ist einmal das Administratorpasswort nötig."
sudo rm -f /usr/local/libexec/drivemonitor-smartctl /etc/polkit-1/rules.d/49-drivemonitor.rules
echo "DriveMonitor wurde vollständig entfernt."
