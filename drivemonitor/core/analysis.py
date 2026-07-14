from __future__ import annotations

from dataclasses import dataclass

from drivemonitor.config import TEMP_CRITICAL, TEMP_WARNING
from .advisor import recommendation_for
from .events import Event
from .history import PreviousSmartValue
from .models import DriveInfo, SensorInfo, SmartItem


@dataclass(slots=True)
class AnalysisResult:
    events: list[Event]


def _number(item: SmartItem) -> int | None:
    try:
        return int(str(item.value).strip())
    except (TypeError, ValueError):
        return None


def _metric_key(label: str) -> str:
    mapping = {
        "CRC-Fehler": "crc",
        "Wiederzugewiesene Sektoren": "reallocated",
        "Ausstehende Sektoren": "pending",
        "Unkorrigierbare Sektoren": "uncorrectable",
        "Unkorrigierbare Fehler": "uncorrectable",
        "Kritische Warnungen": "smart",
        "Medien-/Datenfehler": "uncorrectable",
        "Fehlerprotokolleinträge": "nvme_log",
    }
    return mapping.get(label, "smart")


def _analyse_smart_item(
    drive: DriveInfo,
    item: SmartItem,
    previous: PreviousSmartValue | None,
) -> Event | None:
    current = _number(item)
    if current is None:
        return None

    metric = _metric_key(item.label)
    if metric == "nvme_log":
        if previous and current > previous.value:
            return Event(
                "info", "SMART", f"{drive.name}: NVMe-Protokollzähler verändert",
                f"{drive.name}: Fehlerprotokolleinträge {previous.value} → {current}",
                "Der kumulative NVMe-Zähler ist allein kein Defektnachweis.", drive.device,
            )
        return None

    if current == 0:
        return None

    if previous is None:
        level = "info" if metric == "crc" else "critical"
        return Event(
            level, "SMART", f"{drive.name}: {item.label}",
            f"{drive.name}: {item.label} = {current}; Trend wird ab der nächsten Messung ermittelt",
            recommendation_for(metric, level), drive.device,
        )

    if current > previous.value:
        level = "warning" if metric == "crc" else "critical"
        return Event(
            level, "SMART", f"{drive.name}: {item.label} gestiegen",
            f"{drive.name}: {item.label} {previous.value} → {current}",
            recommendation_for(metric, level), drive.device,
        )

    if current < previous.value:
        return Event(
            "info", "SMART", f"{drive.name}: {item.label} zurückgesetzt",
            f"{drive.name}: {item.label} {previous.value} → {current}",
            "Möglicherweise wurde das Laufwerk oder der Controller zurückgesetzt.", drive.device,
        )

    if metric == "crc":
        return Event(
            "info", "SMART", f"{drive.name}: CRC-Zähler stabil",
            f"{drive.name}: {current} CRC-Fehler, seit letzter Messung unverändert",
            recommendation_for(metric, "info"), drive.device,
        )
    return Event(
        "warning", "SMART", f"{drive.name}: {item.label} vorhanden",
        f"{drive.name}: {item.label} = {current}, unverändert",
        recommendation_for(metric, "warning"), drive.device,
    )


def analyse(
    drives: list[DriveInfo],
    sensors: list[SensorInfo],
    previous_values: dict[tuple[str, str], PreviousSmartValue],
    reboot_required: bool,
    updates_available: int | None,
) -> AnalysisResult:
    events: list[Event] = []

    if not drives:
        events.append(Event("warning", "SMART", "Keine Laufwerke erkannt", "Es wurden keine Laufwerke erkannt."))

    for drive in drives:
        if drive.health == "WARNUNG":
            events.append(Event("critical", "SMART", f"{drive.name}: SMART-Fehler", f"{drive.name}: SMART-Gesamtstatus meldet einen Fehler", recommendation_for("smart", "critical"), drive.device))
        elif drive.health not in {"OK", "Unbekannt"}:
            events.append(Event("warning", "SMART", f"{drive.name}: SMART-Daten unvollständig", f"{drive.name}: SMART-Daten sind nicht vollständig verfügbar", device=drive.device))

        if drive.temperature is not None:
            if drive.temperature >= TEMP_CRITICAL:
                events.append(Event("critical", "Sensoren", f"{drive.name}: Temperatur kritisch", f"{drive.name}: {drive.temperature:.1f} °C", recommendation_for("temperature", "critical"), drive.device))
            elif drive.temperature >= TEMP_WARNING:
                events.append(Event("warning", "Sensoren", f"{drive.name}: Temperatur erhöht", f"{drive.name}: {drive.temperature:.1f} °C", recommendation_for("temperature", "warning"), drive.device))

        for item in drive.smart_items:
            event = _analyse_smart_item(drive, item, previous_values.get((drive.device, item.label)))
            if event:
                events.append(event)

    for sensor in sensors:
        if sensor.temperature >= TEMP_CRITICAL:
            events.append(Event("critical", "Sensoren", f"{sensor.group}: Temperatur kritisch", f"{sensor.group}: {sensor.temperature:.1f} °C", recommendation_for("temperature", "critical")))
        elif sensor.temperature >= TEMP_WARNING:
            events.append(Event("warning", "Sensoren", f"{sensor.group}: Temperatur erhöht", f"{sensor.group}: {sensor.temperature:.1f} °C", recommendation_for("temperature", "warning")))

    if reboot_required:
        events.append(Event("warning", "Systemupdates", "Neustart empfohlen", "Ein Neustart wird empfohlen.", recommendation_for("reboot", "warning")))
    elif updates_available is not None and updates_available > 0:
        events.append(Event("info", "Systemupdates", "Aktualisierungen verfügbar", f"{updates_available} Aktualisierungen sind verfügbar."))

    return AnalysisResult(events)
