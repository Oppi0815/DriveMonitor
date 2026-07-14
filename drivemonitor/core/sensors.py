from __future__ import annotations

import json
import re
from typing import Any

from .command import run
from .models import SensorInfo


def _find(values: dict[str, Any]) -> float | None:
    """Return the first plausible temperature input from a sensors feature."""
    for key, value in values.items():
        if key.lower().endswith("_input") and isinstance(value, (int, float)):
            temperature = float(value)
            if 5 <= temperature <= 150:
                return temperature
    return None


def _friendly_sensor(chip: str, feature: str, adapter: str, ram_index: int) -> SensorInfo | None:
    chip_lower = chip.lower()
    feature_lower = feature.lower()

    # NVMe temperatures are already shown in the drive area.
    if chip_lower.startswith("nvme"):
        return None

    if chip_lower.startswith("k10temp"):
        return SensorInfo("cpu", "CPU", "AMD Ryzen CPU", 0.0, adapter)
    if chip_lower.startswith("amdgpu"):
        return SensorInfo("gpu", "GPU", "Radeon-Grafik", 0.0, adapter)
    if chip_lower.startswith(("spd5118", "jc42")):
        return SensorInfo(f"ram{ram_index}", "RAM", f"RAM-Modul {ram_index}", 0.0, chip)

    # Common network chip drivers exposed through hwmon.
    if chip_lower.startswith(("r8169", "r8125", "igc", "e1000")):
        return SensorInfo(chip_lower, "LAN", "Ethernet-Controller", 0.0, chip)
    if any(token in chip_lower for token in ("mt79", "iwlwifi", "ath", "rtw", "phy")):
        return SensorInfo(chip_lower, "WLAN", "WLAN-Controller", 0.0, chip)

    if chip_lower.startswith(("nct", "it87", "asus", "acpitz")):
        return SensorInfo(chip_lower, "Mainboard", feature.replace("_", " ").title(), 0.0, chip)

    clean = re.sub(r"[-_]", " ", chip).strip()
    return SensorInfo(chip_lower, "Sensor", clean or feature, 0.0, adapter)


def _sort_key(sensor: SensorInfo) -> tuple[int, str]:
    order = {"CPU": 0, "GPU": 1, "RAM": 2, "Mainboard": 3, "LAN": 4, "WLAN": 5, "Sensor": 6}
    return order.get(sensor.group, 99), sensor.name.lower()


def load_sensors() -> list[SensorInfo]:
    result = run(["sensors", "-j"], timeout=8)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    sensors: list[SensorInfo] = []
    ram_count = 0
    for chip, content in payload.items():
        if not isinstance(content, dict):
            continue
        adapter = str(content.get("Adapter") or "")
        for feature, values in content.items():
            if not isinstance(values, dict):
                continue
            value = _find(values)
            if value is None:
                continue
            if chip.lower().startswith(("spd5118", "jc42")):
                ram_count += 1
            sensor = _friendly_sensor(chip, feature, adapter, ram_count)
            if sensor is not None:
                sensor.temperature = value
                sensors.append(sensor)
            # One representative temperature per chip keeps the dashboard compact.
            break

    sensors.sort(key=_sort_key)
    return sensors
