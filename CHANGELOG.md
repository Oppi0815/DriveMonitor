# Änderungsprotokoll

## 5.0.0 – Final

- Erste offizielle stabile Veröffentlichung von DriveMonitor Professional 5.0.0.
- Versions-, Installations- und Dokumentationsangaben auf die Final-Version vereinheitlicht.
- Deutsches und englisches README für Installation, Bedienung, Sicherheit und Datenschutz ergänzt.
- Funktionsumfang aus RC3 übernommen: Rechnerzustand, SMART-Analyse, Ereigniszentrale, Temperaturverläufe, Systemupdates, Diagnosebericht und Über-Dialog.
- Kurze Temperaturspitzen werden zwischen Historienpunkten berücksichtigt.
- Keine neuen Funktionen gegenüber dem letzten Release Candidate; dieser Stand ist der freigegebene 5.0-Code.

## 5.0.0 RC3 – Sprint 4

- Kurzzeitige Temperaturspitzen werden zwischen zwei SQLite-Historienpunkten im Arbeitsspeicher gesammelt.
- Laufwerks- und Systemsensor-Diagramme zeigen den höchsten noch nicht dauerhaft gespeicherten Wert sofort an.
- Beim nächsten Historienintervall wird statt des letzten Messwerts der höchste Wert des gesamten Intervalls gespeichert.
- Alarmbewertung und Verlauf basieren dadurch auf derselben Folge regulärer Messungen.
- Isolierte Tests für Peak-Akkumulation, unmittelbare Diagrammanzeige und dauerhafte Speicherung ergänzt.

## 5.0.0 RC3 – Sprint 3

- Überflüssige Menüzeile am oberen Fensterrand entfernt.
- Kopfzeilenknopf von „Hilfe“ in „Über“ umbenannt.
- Dialogtitel auf „Über DriveMonitor Professional“ geändert.
- Über-Dialog übersichtlicher gegliedert und mit strukturierten System- und Lizenzinformationen verfeinert.
- F1-Zugriff, Programm-Icon, Copyright und GitHub-Link beibehalten.

## 5.0.0 RC3 – Sprint 2.1

- Doppelte Tooltip-Fenster bei Statuskarten behoben.
- Sichtbarer Hilfe-Knopf in der Kopfzeile ergänzt.
- Über-Dialog zusätzlich über F1 erreichbar.
- Hilfemenü klarer gegliedert und mit Tastenkürzeln versehen.
- Mausrad-Scrollschritt korrigiert.

## 5.0.0 RC3 – Sprint 2 (UX & Professional Finish)

- Hilfe-Menü mit Über-Dialog und direktem Zugang zum Debug-Bericht ergänzt.
- Über-Dialog zeigt Icon, Version, Betriebssystem, Kernel, Python-Version, Lizenz und GitHub-Projekt.
- Dynamische Fußzeile zeigt den relativen Zeitpunkt der letzten SMART-Prüfung.
- Tooltips erklären Statuskarten und zentrale SMART-Werte.
- Ereigniskarten verwenden eindeutige Symbole und die Bezeichnungen Information, Beobachten und Kritisch.
- Versions- und Installationsangaben auf RC3 Sprint 2 aktualisiert.

## 5.0.0 RC3 – Sprint 1 (Stabilität)

- Aktualisieren-Button gegen Doppelklick und parallele Hintergrundprüfungen abgesichert.
- Manuelle und automatische Aktualisierung verwenden jetzt denselben zentralen Ablauf.
- Hintergrund-Threads übergeben Ergebnisse über eine threadsichere Queue; Tkinter wird nur noch im GUI-Thread verändert.
- Zeitgeber für automatische Aktualisierung werden zentral verwaltet und beim Beenden sauber abgebrochen.
- Systemupdates, Neustartstatus, SMART, Sensoren, Dashboard und Ereignisse bleiben synchron.
- Versions- und Installationsangaben auf RC3 Sprint 1 aktualisiert.

## 5.0.0 Release Candidate 2

- Systemupdate-Anzeige wird bei jedem manuellen und automatischen Aktualisieren vollständig neu geprüft.
- Unter Linux Mint wird bevorzugt `mintupdate-cli list` verwendet, damit DriveMonitor dieselben verfügbaren Aktualisierungen wie die Aktualisierungsverwaltung anzeigt.
- Portabler APT-Fallback für kompatible Ubuntu-Systeme ohne `mintupdate-cli`.
- Dashboard, Ereignisanalyse und Rechnerzustand werden gemeinsam mit dem frisch gelesenen Update-Status aufgebaut.
- Neustartstatus wird bei jeder Prüfung erneut ermittelt.
- Veraltete Ergebnisse parallel laufender Prüfungen können die aktuelle Anzeige nicht mehr überschreiben.
- Versions- und Installationsangaben auf RC2 aktualisiert.

## 5.0.0 Release Candidate 1

- UI-Freeze: Die Benutzeroberfläche für DriveMonitor 5.0 ist abgeschlossen.
- Doppelte Anzeige von „Rechnerzustand“ und „Systemgesundheit“ entfernt.
- Statuskarten neu geordnet: Laufwerke, Temperaturen, Systemupdates und Letzte Prüfung.
- Relative Zeitangabe der letzten erfolgreichen Prüfung ergänzt.
- Ereigniszähler verwendet die verständlichere Bezeichnung „Meldungen“.
- Ereignisfenster verwendet einheitlich „Rechnerzustand“.
- Dezente Versionsfußzeile ergänzt.
- Versions- und Installationsangaben auf RC1 aktualisiert.

## 5.0.0 Beta 2

- Neue vereinfachte Startseite mit großem Rechnerzustand.
- Verständliche Kernaussage und Handlungsempfehlung direkt beim Start.
- Kompakte Prüfgruppe für SMART, Temperaturen und Linux Mint.
- Einmaliger Willkommensdialog erklärt den Aufbau der Temperatur- und SMART-Historie.
- Benutzereinstellungen werden sicher lokal in `preferences.json` gespeichert.
- Versions- und Installationsmeldung auf Beta 2 aktualisiert.

## 5.0.0 Beta 1.1

- Die obere Statuskarte heißt jetzt eindeutig **Systemupdates**.
- „Keine Updates“ wurde zu „Keine Updates verfügbar“ präzisiert.
- Ereignisse und Komponentenstatus verwenden ebenfalls die Bezeichnung **Systemupdates**.
- Versions- und Installationsmeldung auf Beta 1.1 aktualisiert.

## 5.0.0 Beta 1

- Erste konsolidierte Beta-Version von DriveMonitor 5.0 Professional.
- Versions- und Installationsbezeichnungen vereinheitlicht.
- Dashboard mit Gesundheitsindex stabilisiert.
- Ereignis-, Analyse- und Empfehlungslogik aus den Alpha-Sprints übernommen.
- Scrollbare Hauptansicht für kleine Fenster.
- Temperaturverläufe für Laufwerke und Systemsensoren.
- Lokale Historie für Temperaturen und wichtige SMART-Zähler.
- Debug-Bericht für Diagnose und Support.
- Dokumentation für die Beta-Phase überarbeitet.

## 5.0.0 Alpha 6 – Sprint 4

- Dashboard 2.0 mit transparentem Gesundheitsindex.
- Neue Systemgesundheitskarte mit Prozentwert und Bewertung.
- Systembewertung und Empfehlung im Ereignisfenster.
- Informationsereignisse ohne Punktabzug.
- Warnungen und kritische Ereignisse mit nachvollziehbarer Gewichtung.
- Erste CRC-Messung wird als Information statt Warnung behandelt.
- Verständlichere Formulierung für noch fehlende Vergleichsdaten.
- Neues, separat getestetes Dashboard-Modul.

## 5.0.0 Alpha 5 – Sprint 3

- Neue zentrale Analyse-Engine.
- Neue Ereignis-Engine für mehrere gleichzeitige Hinweise.
- Ereignisdialog mit Priorität, Beschreibung und Empfehlung.
- CRC-Trendanalyse anhand lokal gespeicherter SMART-Werte.
- SQLite-Historie um SMART-Einzelwerte erweitert.
- Advisor-Modul für verständliche Handlungsempfehlungen.
- Interner Debug-Bericht für erkannte Geräte, Sensoren und Regeln.
- Verständlichere Update-Karte.

## 5.0.0 Alpha 4

- Zentrale Zustandsbewertung für SMART, Temperaturen und Neustartstatus.
- Getrennte Komponentenanzeigen für SMART, Sensoren und Updates.
- NVMe-Fehlerprotokollzähler als kumulativer Informationswert behandelt.

## 5.0.0 Alpha 3

- Statusleiste und erste SQLite-Historie.
- Verbesserte Sensorbezeichnungen und Sortierung.

## 5.0.0 Alpha 2

- Laufwerksauswahl korrigiert.
- Unplausible Sensorwerte herausgefiltert.

## 5.0.0 Alpha 1

- Neues modulares Projektfundament.
