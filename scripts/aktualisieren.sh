#!/usr/bin/env bash
set -e

SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$HOME/.local/share/drivemonitor"
TARGET="$TARGET_DIR/drivemonitor.py"

if [ ! -d "$TARGET_DIR" ]; then
    echo "DriveMonitor ist noch nicht installiert."
    echo "Der erwartete Ordner fehlt: $TARGET_DIR"
    exit 1
fi

cp "$SOURCE_DIR/drivemonitor.py" "$TARGET"
chmod +x "$TARGET"

echo
echo "DriveMonitor wurde auf Version 4.3.2 aktualisiert."
echo "Bitte das laufende Fenster schließen und über das Mint-Menü neu starten."
echo
echo "Wichtig bei aktiviertem Autostart:"
echo "Danach bitte autostart-einrichten.sh aus dem Autostart-v2-Paket"
echo "noch einmal ausführen, damit auch die geschützte Kopie unter /opt"
echo "auf Version 4.3.2 aktualisiert wird."
