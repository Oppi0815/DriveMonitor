from __future__ import annotations

from dataclasses import dataclass, field

from .events import Event


@dataclass(slots=True)
class DashboardSummary:
    score: int
    grade: str
    headline: str
    explanation: str
    recommendation: str
    critical_count: int
    warning_count: int
    info_count: int
    deductions: list[str] = field(default_factory=list)


def build_dashboard_summary(events: list[Event]) -> DashboardSummary:
    """Create a transparent, conservative health index from analysed events.

    Informational events do not reduce the score. This keeps stable historical
    counters, such as unchanged CRC values, from making a healthy system look
    defective. Warnings and critical events reduce the score with a cap so the
    result always remains understandable and bounded from 0 to 100.
    """
    critical = [event for event in events if event.level == "critical"]
    warnings = [event for event in events if event.level == "warning"]
    infos = [event for event in events if event.level == "info"]

    critical_penalty = min(70, len(critical) * 25)
    warning_penalty = min(30, len(warnings) * 8)
    score = max(0, 100 - critical_penalty - warning_penalty)

    deductions: list[str] = []
    if critical:
        deductions.append(f"−{critical_penalty} Punkte: {len(critical)} kritische Ereignisse")
    if warnings:
        deductions.append(f"−{warning_penalty} Punkte: {len(warnings)} Warnhinweise")
    if infos:
        deductions.append(f"{len(infos)} Informationen ohne Punktabzug")

    if critical:
        grade = "Handlungsbedarf"
        headline = "Kritische Ereignisse erkannt"
        explanation = "Mindestens ein Ereignis erfordert zeitnahe Aufmerksamkeit."
        recommendation = critical[0].recommendation or "Details prüfen und wichtige Daten sichern."
    elif warnings:
        grade = "Beobachten"
        headline = "Hinweise sollten beobachtet werden"
        explanation = "Das System arbeitet, aber mindestens ein Wert verdient Aufmerksamkeit."
        recommendation = warnings[0].recommendation or "Hinweise in der Ereignisliste prüfen."
    elif infos:
        grade = "Ausgezeichnet"
        headline = "Keine kritischen Ereignisse"
        explanation = "Es liegen nur Informationen ohne akuten Handlungsbedarf vor."
        recommendation = "Keine unmittelbare Maßnahme erforderlich."
    else:
        grade = "Ausgezeichnet"
        headline = "System in Ordnung"
        explanation = "SMART-Status und Temperaturen zeigen keine Auffälligkeiten."
        recommendation = "Keine Maßnahmen erforderlich."

    return DashboardSummary(
        score=score,
        grade=grade,
        headline=headline,
        explanation=explanation,
        recommendation=recommendation,
        critical_count=len(critical),
        warning_count=len(warnings),
        info_count=len(infos),
        deductions=deductions,
    )
