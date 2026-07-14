#!/usr/bin/env bash
set -euo pipefail
rm -rf "$HOME/.local/share/drivemonitor"
rm -f "$HOME/.local/bin/drivemonitor" "$HOME/.local/share/applications/drivemonitor.desktop"
echo "Benutzerinstallation entfernt."
echo "Optional können Administratoren /usr/local/libexec/drivemonitor-smartctl und /etc/sudoers.d/drivemonitor-smartctl entfernen."
