#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="/opt/drivemonitor-backup-$STAMP"
echo "Die funktionierende Installation wird gesichert nach: $BACKUP"
sudo cp -a /opt/drivemonitor "$BACKUP"
sudo install -m 755 "$DIR/drivemonitor.py" /opt/drivemonitor/drivemonitor.py
echo "DriveMonitor 4.6 Professional wurde installiert."
echo "Rückweg: sudo rm -rf /opt/drivemonitor && sudo cp -a $BACKUP /opt/drivemonitor"
