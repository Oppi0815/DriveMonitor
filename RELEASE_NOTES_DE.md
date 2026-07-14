# DriveMonitor Professional 5.0.0

Die erste offizielle stabile Version von DriveMonitor Professional ist ein Gesundheitsmonitor für Linux Mint mit Fokus auf Laufwerke, SMART-Daten und Temperaturen.

## Höhepunkte

- verständlicher Rechnerzustand statt reiner Rohdaten
- HDD-, SSD-, NVMe- und unterstützte USB-Erkennung
- sichere SMART-Abfrage als normaler Benutzer
- Ereigniszentrale mit Empfehlungen
- Temperaturdiagramme und lokale Historie
- Erkennung kurzer Temperaturspitzen
- Systemupdate- und Neustartstatus
- Diagnosebericht für Supportfälle

## Installation

ZIP entpacken und im Projektordner ausführen:

```bash
chmod +x install.sh smart-berechtigung-einrichten.sh uninstall.sh
./install.sh
```

Die SMART-Freigabe ist nur einmalig erforderlich:

```bash
./smart-berechtigung-einrichten.sh
```
