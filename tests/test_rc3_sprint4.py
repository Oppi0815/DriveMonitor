from __future__ import annotations

from pathlib import Path

from drivemonitor.core import history
from drivemonitor.core.models import DriveInfo, SensorInfo


def _drive(temperature: float) -> DriveInfo:
    return DriveInfo(
        "/dev/sda",
        "Testlaufwerk",
        "1 TB",
        "SATA",
        "HDD",
        temperature=temperature,
        health="OK",
    )


def _sensor(temperature: float) -> SensorInfo:
    return SensorInfo("cpu", "CPU", "Test-CPU", temperature)


def _use_temp_history(tmp_path: Path) -> tuple[Path, Path]:
    old_dir = history.HISTORY_DIR
    old_db = history.HISTORY_DB
    history.HISTORY_DIR = tmp_path
    history.HISTORY_DB = tmp_path / "history.db"
    history._reset_pending_peaks_for_tests()
    return old_dir, old_db


def _restore_history(old_dir: Path, old_db: Path) -> None:
    history._reset_pending_peaks_for_tests()
    history.HISTORY_DIR = old_dir
    history.HISTORY_DB = old_db


def test_pending_cpu_peak_is_immediately_visible(tmp_path: Path) -> None:
    old_dir, old_db = _use_temp_history(tmp_path)
    try:
        assert history.store_snapshot([_drive(35.0)], [_sensor(35.0)], now=1000) is True
        assert history.store_snapshot([_drive(36.0)], [_sensor(50.0)], now=1100) is False
        assert history.store_snapshot([_drive(35.0)], [_sensor(37.0)], now=1110) is False

        values = [point.temperature for point in history.load_sensor_temperature_history("cpu")]
        assert values[-1] == 50.0
    finally:
        _restore_history(old_dir, old_db)


def test_interval_peak_is_persisted_instead_of_last_value(tmp_path: Path) -> None:
    old_dir, old_db = _use_temp_history(tmp_path)
    try:
        history.store_snapshot([_drive(35.0)], [_sensor(35.0)], now=1000)
        history.store_snapshot([_drive(50.0)], [_sensor(50.0)], now=1100)
        history.store_snapshot([_drive(37.0)], [_sensor(37.0)], now=1150)
        assert history.store_snapshot([_drive(36.0)], [_sensor(36.0)], now=1301) is True

        drive_values = [point.temperature for point in history.load_drive_temperature_history("/dev/sda")]
        sensor_values = [point.temperature for point in history.load_sensor_temperature_history("cpu")]
        assert drive_values[-1] == 50.0
        assert sensor_values[-1] == 50.0
    finally:
        _restore_history(old_dir, old_db)


def test_rc3_sprint4_version_is_consistent() -> None:
    root = Path(__file__).parents[1]
    assert 'APP_VERSION = "5.0.0"' in (root / "drivemonitor/config.py").read_text(encoding="utf-8")
    assert "DriveMonitor Professional 5.0.0 wurde" in (root / "install.sh").read_text(encoding="utf-8")
    assert "DriveMonitor Professional 5.0.0" in (root / "README.md").read_text(encoding="utf-8")
