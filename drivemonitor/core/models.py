from __future__ import annotations

from dataclasses import dataclass, field

@dataclass(slots=True)
class SmartItem:
    label: str
    value: str
    state: str = "neutral"

@dataclass(slots=True)
class DriveInfo:
    device: str
    name: str
    size: str
    transport: str
    kind: str
    temperature: float | None = None
    health: str = "Unbekannt"
    serial: str = "—"
    firmware: str = "—"
    power_on_hours: int | None = None
    power_cycles: int | None = None
    life_remaining: int | None = None
    smart_items: list[SmartItem] = field(default_factory=list)
    error: str | None = None

@dataclass(slots=True)
class SensorInfo:
    key: str
    group: str
    name: str
    temperature: float
    details: str = ""

@dataclass(slots=True)
class SystemInfo:
    hostname: str
    operating_system: str
    kernel: str
    desktop: str
