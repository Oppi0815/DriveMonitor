# DriveMonitor Professional 5.0.0

DriveMonitor Professional ist ein modularer Gesundheitsmonitor für Laufwerke und Hardware unter Linux Mint. Die Anwendung bewertet SMART-Daten und Temperaturen verständlich, zeigt Veränderungen und Ereignisse an und läuft vollständig als normaler Benutzer.

## Highlights

- HDD-, SSD-, NVMe- und unterstützte USB-Laufwerke
- sichere SMART-Abfrage ohne Passwortabfrage im laufenden Betrieb
- übersichtlicher Rechnerzustand mit verständlichen Empfehlungen
- wichtige SMART-Werte und Trendanalyse
- Ereigniszentrale für mehrere gleichzeitige Meldungen
- Temperaturverläufe für Laufwerke und Systemsensoren
- Erkennung kurzer Temperaturspitzen zwischen Historienpunkten
- Linux-Mint-Systemupdates und Neustartstatus
- scrollbare Oberfläche für kleine und große Fenster
- Diagnose- und Debug-Bericht
- einmaliger Willkommensdialog
- Über-Dialog mit System-, Versions- und Lizenzinformationen

## Installation

```bash
chmod +x install.sh smart-berechtigung-einrichten.sh uninstall.sh
./install.sh
```

Nur bei der Erstinstallation oder wenn SMART-Daten nicht gelesen werden können:

```bash
./smart-berechtigung-einrichten.sh
```

Dieses Skript benötigt einmalig Administratorrechte. DriveMonitor selbst wird anschließend als normaler Benutzer gestartet.

## Start

DriveMonitor erscheint im Linux-Mint-Menü als **DriveMonitor Professional**. Alternativ:

```bash
drivemonitor
```

## Lokale Daten

Die Historie und Einstellungen werden ausschließlich lokal gespeichert:

```text
~/.local/share/drivemonitor/history.db
~/.local/share/drivemonitor/preferences.json
```

DriveMonitor überträgt keine persönlichen Daten ins Internet. Für die Prüfung verfügbarer Systemupdates werden ausschließlich lokale Linux-Mint- beziehungsweise APT-Werkzeuge verwendet.

## Voraussetzungen

- Linux Mint 22.x oder kompatibles Ubuntu-System
- Python 3 mit Tkinter
- `smartmontools`
- `lm-sensors`
- `lsblk`

## Deinstallation

```bash
./uninstall.sh
```

Die optionale systemweite SMART-Freigabe kann anschließend, wie vom Deinstallationsskript beschrieben, durch einen Administrator entfernt werden.

## Bedienung

- **Aktualisieren** liest Laufwerke, SMART-Daten, Temperaturen, Sensoren und Systemupdates vollständig neu ein.
- **Über** zeigt Version, Betriebssystem, Kernel, Python-Version, Lizenz und den GitHub-Link.
- Die Meldungsleiste öffnet die Ereigniszentrale.
- Der Debug-Bericht unterstützt Diagnose und Support.
- Temperaturdiagramme werden mit jeder Messung aussagekräftiger.

## Datenschutz und Sicherheit

- Die grafische Oberfläche läuft nicht als root.
- Der SMART-Helfer erlaubt ausschließlich lesende `smartctl -a -j`-Aufrufe für zulässige Gerätedateien.
- Alle Verlaufsdaten bleiben lokal auf dem Rechner.

## Lizenz

GNU General Public License v3. Siehe `LICENSE`.

## Projekt

GitHub: `https://github.com/Oppi0815/DriveMonitor`

Entwickelt für Linux Mint.
