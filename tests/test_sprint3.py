from drivemonitor.core.analysis import analyse
from drivemonitor.core.events import summarize_events
from drivemonitor.core.history import PreviousSmartValue
from drivemonitor.core.models import DriveInfo, SmartItem


def _drive(value: int) -> DriveInfo:
    return DriveInfo(
        "/dev/sda", "Testlaufwerk", "1 TB", "SATA", "HDD",
        temperature=35.0,
        health="OK",
        smart_items=[SmartItem("CRC-Fehler", str(value), "warning" if value else "ok")],
    )


def test_crc_baseline_is_information():
    result = analyse([_drive(24)], [], {}, False, 0)
    assert result.events[0].level == "info"
    assert "Trend wird ab der nächsten Messung" in result.events[0].message


def test_stable_crc_is_information():
    previous = {("/dev/sda", "CRC-Fehler"): PreviousSmartValue(24, 100)}
    result = analyse([_drive(24)], [], previous, False, 0)
    assert result.events[0].level == "info"
    assert "unverändert" in result.events[0].message


def test_increased_crc_is_warning():
    previous = {("/dev/sda", "CRC-Fehler"): PreviousSmartValue(24, 100)}
    result = analyse([_drive(25)], [], previous, False, 0)
    assert result.events[0].level == "warning"
    assert "24 → 25" in result.events[0].message


def test_multiple_events_are_counted():
    first = _drive(24)
    second = DriveInfo(
        "/dev/sdb", "Zweites Laufwerk", "1 TB", "SATA", "HDD",
        temperature=35.0, health="OK",
        smart_items=[SmartItem("CRC-Fehler", "3", "warning")],
    )
    summary = summarize_events(analyse([first, second], [], {}, False, 0).events)
    assert summary.count == 2
    assert "1 weitere Ereignisse" in summary.message


def test_nvme_log_counter_does_not_warn():
    drive = DriveInfo(
        "/dev/nvme0n1", "NVMe", "1 TB", "NVME", "NVMe",
        temperature=35.0, health="OK",
        smart_items=[SmartItem("Fehlerprotokolleinträge", "7575", "info")],
    )
    result = analyse([drive], [], {}, False, 0)
    assert result.events == []
