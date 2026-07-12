# DriveMonitor 4.6 Professional – B650 Standalone

Diese Ausgabe basiert auf DriveMonitor 4.4 und wurde auf dem B650 um eine integrierte Systemwartung erweitert.

## Neu in Version 4.6

- Systemwartungsfenster
- Papierkorb prüfen und leeren
- Downloads und Benutzer-Cache prüfen
- Python-pip-Cache bereinigen
- APT-Cache und autoremove prüfen
- ungenutzte Flatpak-Komponenten prüfen
- Journal-Speicherverbrauch anzeigen
- Wartungsprotokoll
- Bestätigung vor jeder Löschaktion

## Installation

Die bestehende Installation muss sich unter `/opt/drivemonitor` befinden.

    chmod +x installieren.sh
    ./installieren.sh

Das Installationsskript sichert vor dem Austausch automatisch die bisherige Installation.

## Hinweis

Diese Standalone-Ausgabe wurde speziell auf dem B650 getestet. Die modulare DriveMonitor-Version im Hauptverzeichnis bleibt unverändert.
