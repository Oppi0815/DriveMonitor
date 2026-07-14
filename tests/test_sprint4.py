from drivemonitor.core.dashboard import build_dashboard_summary
from drivemonitor.core.events import Event


def test_clean_system_scores_100():
    result = build_dashboard_summary([])
    assert result.score == 100
    assert result.grade == "Ausgezeichnet"


def test_information_does_not_reduce_score():
    result = build_dashboard_summary([
        Event("info", "SMART", "CRC stabil", "CRC-Zähler unverändert")
    ])
    assert result.score == 100
    assert result.info_count == 1


def test_warning_reduces_score_transparently():
    result = build_dashboard_summary([
        Event("warning", "Sensoren", "Temperatur erhöht", "SSD: 55 °C")
    ])
    assert result.score == 92
    assert result.warning_count == 1
    assert any("−8 Punkte" in item for item in result.deductions)


def test_critical_event_has_strong_penalty():
    result = build_dashboard_summary([
        Event("critical", "SMART", "SMART-Fehler", "SMART meldet Fehler")
    ])
    assert result.score == 75
    assert result.grade == "Handlungsbedarf"
