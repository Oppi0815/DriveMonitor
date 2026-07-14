from drivemonitor.core.health import evaluate_drive, evaluate_health
from drivemonitor.core.models import DriveInfo, SensorInfo, SmartItem


def _drive(items=None, health="OK", temperature=35.0):
    return DriveInfo(
        "/dev/sda", "Testlaufwerk", "1 TB", "SATA", "SSD",
        temperature=temperature, health=health, smart_items=items or []
    )


def test_crc_is_warning_not_critical():
    issues = evaluate_drive(_drive([SmartItem("CRC-Fehler", "1", "warning")]))
    assert len(issues) == 1
    assert issues[0].level == "warning"


def test_reallocated_sector_is_critical():
    result = evaluate_health(
        [_drive([SmartItem("Wiederzugewiesene Sektoren", "1", "critical")])],
        [], False, 0,
    )
    assert result.level == "critical"
    assert "Wiederzugewiesene" in result.message


def test_nvme_log_counter_info_is_not_warning():
    result = evaluate_health(
        [_drive([SmartItem("Fehlerprotokolleinträge", "7575", "info")])],
        [SensorInfo("cpu", "CPU", "CPU", 40.0)], False, 0,
    )
    assert result.level == "ok"


def test_component_states_are_available():
    result = evaluate_health([_drive()], [], True, 4)
    states = {component.label: component.level for component in result.components}
    assert states["SMART"] == "ok"
    assert states["Systemupdates"] == "warning"
