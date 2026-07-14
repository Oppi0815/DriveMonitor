from __future__ import annotations

from dataclasses import dataclass, field


LEVEL_ORDER = {"ok": 0, "info": 1, "warning": 2, "critical": 3}


@dataclass(slots=True)
class Event:
    level: str
    category: str
    title: str
    message: str
    recommendation: str = ""
    device: str | None = None
    source: str = "analysis"

    @property
    def rank(self) -> int:
        return LEVEL_ORDER.get(self.level, 0)


@dataclass(slots=True)
class EventSummary:
    level: str
    title: str
    message: str
    events: list[Event] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len([event for event in self.events if event.level != "ok"])


def summarize_events(events: list[Event]) -> EventSummary:
    visible = sorted(
        [event for event in events if event.level != "ok"],
        key=lambda event: event.rank,
        reverse=True,
    )
    if not visible:
        return EventSummary("ok", "Gesund", "Heute keine Auffälligkeiten", events)

    highest = visible[0]
    same_or_lower = max(0, len(visible) - 1)
    if highest.level == "critical":
        title = "Handlungsbedarf"
    elif highest.level == "warning":
        title = "Beobachten"
    else:
        title = "Information"

    message = highest.message
    if same_or_lower:
        message = f"{message} · {same_or_lower} weitere Ereignisse"
    return EventSummary(highest.level, title, message, visible)
