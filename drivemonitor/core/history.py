from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .models import DriveInfo, SensorInfo

HISTORY_DIR = Path.home() / ".local" / "share" / "drivemonitor"
HISTORY_DB = HISTORY_DIR / "history.db"
MIN_INTERVAL_SECONDS = 300


@dataclass(slots=True)
class PreviousSmartValue:
    value: int
    recorded_at: int


@dataclass(slots=True)
class TemperaturePoint:
    recorded_at: int
    temperature: float


@dataclass(slots=True)
class _PendingPeak:
    recorded_at: int
    temperature: float


_pending_lock = threading.Lock()
_pending_drive_peaks: dict[str, _PendingPeak] = {}
_pending_sensor_peaks: dict[str, _PendingPeak] = {}


def _connect() -> sqlite3.Connection:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(HISTORY_DB, timeout=5)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS drive_history (
            recorded_at INTEGER NOT NULL,
            device TEXT NOT NULL,
            model TEXT NOT NULL,
            temperature REAL,
            health TEXT NOT NULL,
            life_remaining INTEGER,
            power_on_hours INTEGER
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sensor_history (
            recorded_at INTEGER NOT NULL,
            sensor_key TEXT NOT NULL,
            sensor_name TEXT NOT NULL,
            temperature REAL NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS smart_history (
            recorded_at INTEGER NOT NULL,
            device TEXT NOT NULL,
            metric TEXT NOT NULL,
            value INTEGER NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_drive_history_device_time ON drive_history(device, recorded_at)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_sensor_history_key_time ON sensor_history(sensor_key, recorded_at)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_smart_history_device_metric_time ON smart_history(device, metric, recorded_at)")
    return connection


def _last_timestamp(connection: sqlite3.Connection, table: str) -> int | None:
    row = connection.execute(f"SELECT MAX(recorded_at) FROM {table}").fetchone()
    return int(row[0]) if row and row[0] is not None else None


def _remember_peak(storage: dict[str, _PendingPeak], key: str, temperature: float, timestamp: int) -> None:
    previous = storage.get(key)
    if previous is None or temperature >= previous.temperature:
        storage[key] = _PendingPeak(timestamp, temperature)


def _accumulate_temperature_peaks(
    drives: list[DriveInfo], sensors: list[SensorInfo], timestamp: int
) -> None:
    """Remember every measured peak until the next persistent history point."""
    with _pending_lock:
        for drive in drives:
            if drive.temperature is not None:
                _remember_peak(_pending_drive_peaks, drive.device, float(drive.temperature), timestamp)
        for sensor in sensors:
            _remember_peak(_pending_sensor_peaks, sensor.key, float(sensor.temperature), timestamp)


def _pending_drive_point(device: str) -> TemperaturePoint | None:
    with _pending_lock:
        point = _pending_drive_peaks.get(device)
        if point is None:
            return None
        return TemperaturePoint(point.recorded_at, point.temperature)


def _pending_sensor_point(sensor_key: str) -> TemperaturePoint | None:
    with _pending_lock:
        point = _pending_sensor_peaks.get(sensor_key)
        if point is None:
            return None
        return TemperaturePoint(point.recorded_at, point.temperature)


def _append_pending(points: list[TemperaturePoint], pending: TemperaturePoint | None) -> list[TemperaturePoint]:
    if pending is None:
        return points
    if points and points[-1].recorded_at == pending.recorded_at:
        points[-1] = pending
    else:
        points.append(pending)
    return points


def load_previous_smart_values() -> dict[tuple[str, str], PreviousSmartValue]:
    """Return the most recent stored value for each SMART metric."""
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT h.device, h.metric, h.value, h.recorded_at
            FROM smart_history AS h
            JOIN (
                SELECT device, metric, MAX(recorded_at) AS latest
                FROM smart_history
                GROUP BY device, metric
            ) AS latest
              ON latest.device = h.device
             AND latest.metric = h.metric
             AND latest.latest = h.recorded_at
            """
        ).fetchall()
    return {
        (str(device), str(metric)): PreviousSmartValue(int(value), int(recorded_at))
        for device, metric, value, recorded_at in rows
    }


def load_drive_temperature_history(device: str, limit: int = 24) -> list[TemperaturePoint]:
    """Load persisted points plus the highest not-yet-persisted measurement."""
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT recorded_at, temperature
            FROM drive_history
            WHERE device = ? AND temperature IS NOT NULL
            ORDER BY recorded_at DESC
            LIMIT ?
            """,
            (device, max(1, int(limit))),
        ).fetchall()
    points = [TemperaturePoint(int(recorded_at), float(temperature)) for recorded_at, temperature in reversed(rows)]
    return _append_pending(points, _pending_drive_point(device))[-max(1, int(limit)):]


def load_sensor_temperature_history(sensor_key: str, limit: int = 18) -> list[TemperaturePoint]:
    """Load persisted points plus the highest not-yet-persisted measurement."""
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT recorded_at, temperature
            FROM sensor_history
            WHERE sensor_key = ?
            ORDER BY recorded_at DESC
            LIMIT ?
            """,
            (sensor_key, max(1, int(limit))),
        ).fetchall()
    points = [TemperaturePoint(int(recorded_at), float(temperature)) for recorded_at, temperature in reversed(rows)]
    return _append_pending(points, _pending_sensor_point(sensor_key))[-max(1, int(limit)):]


def _smart_rows(drives: list[DriveInfo], timestamp: int) -> list[tuple[int, str, str, int]]:
    rows: list[tuple[int, str, str, int]] = []
    for drive in drives:
        for item in drive.smart_items:
            try:
                value = int(str(item.value).strip())
            except (TypeError, ValueError):
                continue
            rows.append((timestamp, drive.device, item.label, value))
    return rows


def store_snapshot(drives: list[DriveInfo], sensors: list[SensorInfo], now: int | None = None) -> bool:
    """Accumulate every measurement and persist interval maxima every five minutes."""
    timestamp = int(time.time() if now is None else now)
    _accumulate_temperature_peaks(drives, sensors, timestamp)

    with _connect() as connection:
        last = max(
            _last_timestamp(connection, "drive_history") or 0,
            _last_timestamp(connection, "sensor_history") or 0,
            _last_timestamp(connection, "smart_history") or 0,
        )
        if timestamp - last < MIN_INTERVAL_SECONDS:
            return False

        with _pending_lock:
            drive_peaks = dict(_pending_drive_peaks)
            sensor_peaks = dict(_pending_sensor_peaks)

        connection.executemany(
            "INSERT INTO drive_history VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    timestamp,
                    drive.device,
                    drive.name,
                    drive_peaks.get(drive.device).temperature
                    if drive.device in drive_peaks
                    else drive.temperature,
                    drive.health,
                    drive.life_remaining,
                    drive.power_on_hours,
                )
                for drive in drives
            ],
        )
        connection.executemany(
            "INSERT INTO sensor_history VALUES (?, ?, ?, ?)",
            [
                (
                    timestamp,
                    sensor.key,
                    sensor.name,
                    sensor_peaks.get(sensor.key).temperature
                    if sensor.key in sensor_peaks
                    else sensor.temperature,
                )
                for sensor in sensors
            ],
        )
        connection.executemany(
            "INSERT INTO smart_history VALUES (?, ?, ?, ?)",
            _smart_rows(drives, timestamp),
        )

    with _pending_lock:
        _pending_drive_peaks.clear()
        _pending_sensor_peaks.clear()
    return True


def _reset_pending_peaks_for_tests() -> None:
    """Clear in-memory state. Intended only for isolated automated tests."""
    with _pending_lock:
        _pending_drive_peaks.clear()
        _pending_sensor_peaks.clear()
