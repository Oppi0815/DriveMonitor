from drivemonitor.core.health import evaluate_health
from drivemonitor.core.models import DriveInfo, SensorInfo


def _drive(health: str = "OK", temperature: float = 35.0) -> DriveInfo:
    return DriveInfo("/dev/sda", "Test", "1 TB", "SATA", "SSD", temperature=temperature, health=health)


def test_health_ok():
    result = evaluate_health([_drive()], [SensorInfo("cpu", "CPU", "CPU", 40.0)], False)
    assert result.level == "ok"
    assert result.message == "Heute keine Auffälligkeiten"


def test_health_warns_on_missing_smart():
    result = evaluate_health([_drive("Unbekannt")], [], False)
    assert result.level == "warning"


def test_health_critical_temperature():
    result = evaluate_health([_drive(temperature=65.0)], [], False)
    assert result.level == "critical"
