from __future__ import annotations


def recommendation_for(metric: str, level: str) -> str:
    rules = {
        "crc": "SATA-Datenkabel und Steckverbindungen prüfen, falls der Zähler weiter steigt.",
        "reallocated": "Datensicherung prüfen und das Laufwerk zeitnah mit einem langen SMART-Selbsttest untersuchen.",
        "pending": "Datensicherung anlegen und das Laufwerk beobachten; bei Zunahme ersetzen.",
        "uncorrectable": "Datensicherung dringend prüfen und das Laufwerk genauer untersuchen.",
        "temperature": "Luftstrom, Kühlkörper und Staubbelastung kontrollieren.",
        "smart": "Wichtige Daten sichern und den vollständigen SMART-Bericht prüfen.",
        "reboot": "Den Rechner bei Gelegenheit neu starten, damit Aktualisierungen vollständig wirksam werden.",
    }
    text = rules.get(metric, "")
    if level == "info" and metric == "crc":
        return "Keine Aktion nötig, solange der Zähler unverändert bleibt."
    return text
