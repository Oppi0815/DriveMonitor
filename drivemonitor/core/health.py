from __future__ import annotations

from dataclasses import dataclass, field

from drivemonitor.config import TEMP_CRITICAL, TEMP_WARNING
from .models import DriveInfo, SensorInfo, SmartItem


@dataclass(slots=True)
class HealthIssue:
    level: str
    category: str
    message: str
    device: str | None = None


@dataclass(slots=True)
class ComponentStatus:
    label: str
    level: str
    message: str


@dataclass(slots=True)
class HealthSummary:
    level: str
    title: str
    message: str
    issues: list[HealthIssue] = field(default_factory=list)
    components: list[ComponentStatus] = field(default_factory=list)


def _temperature_issue(label: str, value: float, device: str | None = None) -> HealthIssue | None:
    if value >= TEMP_CRITICAL:
        return HealthIssue("critical", "Temperatur", f"{label}: {value:.1f} °C ist kritisch", device)
    if value >= TEMP_WARNING:
        return HealthIssue("warning", "Temperatur", f"{label}: {value:.1f} °C ist erhöht", device)
    return None


def _smart_item_issue(drive: DriveInfo, item: SmartItem) -> HealthIssue | None:
    if item.state not in {"warning", "critical", "warn"}:
        return None
    level = "critical" if item.state == "critical" else "warning"
    return HealthIssue(level, "SMART", f"{drive.name}: {item.label} = {item.value}", drive.device)


def evaluate_drive(drive: DriveInfo) -> list[HealthIssue]:
    issues: list[HealthIssue] = []
    if drive.health == "WARNUNG":
        issues.append(HealthIssue("critical", "SMART", f"{drive.name}: SMART-Gesamtstatus meldet einen Fehler", drive.device))
    elif drive.health != "OK":
        issues.append(HealthIssue("warning", "SMART", f"{drive.name}: SMART-Daten sind nicht vollständig verfügbar", drive.device))

    if drive.temperature is not None:
        issue = _temperature_issue(drive.name, drive.temperature, drive.device)
        if issue:
            issues.append(issue)

    for item in drive.smart_items:
        issue = _smart_item_issue(drive, item)
        if issue:
            issues.append(issue)
    return issues


def evaluate_health(
    drives: list[DriveInfo],
    sensors: list[SensorInfo],
    reboot_required: bool,
    updates_available: int | None = None,
) -> HealthSummary:
    issues: list[HealthIssue] = []
    for drive in drives:
        issues.extend(evaluate_drive(drive))

    if not drives:
        issues.append(HealthIssue("warning", "SMART", "Keine Laufwerke erkannt"))

    for sensor in sensors:
        issue = _temperature_issue(sensor.group or sensor.name, sensor.temperature)
        if issue:
            issues.append(issue)

    if reboot_required:
        issues.append(HealthIssue("warning", "Systemupdates", "Ein Neustart wird empfohlen"))

    critical = [issue for issue in issues if issue.level == "critical"]
    warnings = [issue for issue in issues if issue.level == "warning"]

    if critical:
        level, title, message = "critical", "Handlungsbedarf", critical[0].message
    elif warnings:
        level, title, message = "warning", "Beobachten", warnings[0].message
    else:
        level, title, message = "ok", "Gesund", "Heute keine Auffälligkeiten"

    smart_issues = [issue for issue in issues if issue.category == "SMART"]
    temp_issues = [issue for issue in issues if issue.category == "Temperatur"]
    update_issues = [issue for issue in issues if issue.category == "Systemupdates"]

    def component(label: str, component_issues: list[HealthIssue], ok_message: str) -> ComponentStatus:
        if any(issue.level == "critical" for issue in component_issues):
            return ComponentStatus(label, "critical", component_issues[0].message)
        if component_issues:
            return ComponentStatus(label, "warning", component_issues[0].message)
        return ComponentStatus(label, "ok", ok_message)

    components = [
        component("SMART", smart_issues, f"{len(drives)} Laufwerke ohne kritische SMART-Warnung"),
        component("Sensoren", temp_issues, "Temperaturen im Normalbereich" if sensors or drives else "Keine Messwerte"),
        component("Systemupdates", update_issues, "Kein Neustart erforderlich"),
    ]
    if updates_available is not None and updates_available > 0 and not reboot_required:
        components[2].message = f"{updates_available} Aktualisierungen verfügbar"

    return HealthSummary(level, title, message, issues, components)
