from __future__ import annotations

from .events import Event
from .models import DriveInfo, SensorInfo


def build_debug_report(drives: list[DriveInfo], sensors: list[SensorInfo], events: list[Event]) -> str:
    lines = ["DriveMonitor Debug-Bericht", "", "Laufwerke:"]
    for drive in drives:
        lines.append(f"- {drive.device} | {drive.name} | {drive.kind} | SMART={drive.health} | Temp={drive.temperature}")
        for item in drive.smart_items:
            lines.append(f"    {item.label}: {item.value} ({item.state})")
    lines.append("")
    lines.append("Sensoren:")
    for sensor in sensors:
        lines.append(f"- {sensor.key} | {sensor.group} | {sensor.name} | {sensor.temperature:.1f} °C")
    lines.append("")
    lines.append("Analyse-Ereignisse:")
    if not events:
        lines.append("- keine")
    for event in events:
        lines.append(f"- [{event.level}] {event.category}: {event.message}")
        if event.recommendation:
            lines.append(f"    Empfehlung: {event.recommendation}")
    return "\n".join(lines)
