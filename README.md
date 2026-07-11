# DriveMonitor 4.5.1 Professional

DriveMonitor zeigt SMART-Zustand, Temperaturen, Belegung und wichtige Laufwerkswerte für HDD, SSD, NVMe und unterstützte USB-Laufwerke unter Linux Mint an.

## Installation

```bash
chmod +x *.sh helpers/drivemonitor-smartctl
./installieren.sh
```

Benötigte Pakete:

```bash
sudo apt install smartmontools lm-sensors python3-tk
```

Die grafische Oberfläche läuft als normaler Benutzer. Nur der begrenzte SMART-Helfer wird über Polkit mit erhöhten Rechten ausgeführt.

## Start

Über das Linux-Mint-Menü oder:

```bash
python3 ~/.local/share/drivemonitor/drivemonitor.py
```

## Prüfung

```bash
./pruefen.sh
```

## Hinweise zur finalen Version

Für die Installation und den Betrieb sollten folgende Punkte geprüft werden:

- Über-Dialog und angezeigte Versionsinformationen
- Laufwerkserkennung und SMART-Werte
- Berichtserzeugung
- Einstellungen
- gespeicherte Fenstergröße und Fensterposition
- Autostart nach Neuanmeldung


## Korrektur in 4.5.1

Die Systemtemperaturen bleiben auch bei der kleinsten Fenstergröße sichtbar. Auf Systemen ohne separaten GPU-Temperatursensor zeigt die Übersicht beispielsweise `47° / —` an.
