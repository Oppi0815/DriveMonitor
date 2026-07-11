from __future__ import annotations
import json
from typing import Any
from .utils import run, numeric_input, clean_label


def _first_temperature(chip_data: dict[str, Any]) -> float | None:
    for feature, values in chip_data.items():
        if not isinstance(values, dict):
            continue
        for key, val in values.items():
            if (isinstance(val, (int, float)) and key.lower().endswith("_input")
                    and ("temp" in key.lower() or str(feature).lower().startswith("temp"))):
                value = float(val)
                if -20 <= value <= 150:
                    return value
    return None


def load_sensors() -> list[dict[str, Any]]:
    code, out, _ = run(["sensors", "-j"], timeout=8)
    if code != 0 or not out.strip():
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []

    rows: list[dict[str, Any]] = []
    ram_index = 0

    for chip, chip_data in data.items():
        if not isinstance(chip_data, dict):
            continue
        adapter = chip_data.get("Adapter", "")
        chip_l = chip.lower()

        if chip_l.startswith(("k10temp", "coretemp")):
            value = _first_temperature(chip_data)
            if value is not None:
                cpu_name = "AMD Ryzen CPU" if chip_l.startswith("k10temp") else "Intel CPU"
                rows.append({"group": "CPU", "name": cpu_name, "temp": value,
                             "details": adapter, "key": "cpu", "icon": "CPU"})
            continue

        if chip_l.startswith("amdgpu"):
            value = _first_temperature(chip_data)
            if value is not None:
                rows.append({"group": "GPU", "name": "Radeon-Grafik", "temp": value,
                             "details": adapter, "key": "gpu", "icon": "GPU"})
            continue

        if chip_l.startswith(("nouveau", "nvidia")):
            value = _first_temperature(chip_data)
            if value is not None:
                rows.append({"group": "GPU", "name": "NVIDIA-Grafik", "temp": value,
                             "details": adapter, "key": "gpu", "icon": "GPU"})
            continue

        if chip_l.startswith("spd5118"):
            ram_index += 1
            value = _first_temperature(chip_data)
            if value is not None:
                rows.append({"group": "RAM", "name": f"RAM-Modul {ram_index}", "temp": value,
                             "details": clean_label(chip), "key": f"ram{ram_index}", "icon": "RAM"})
            continue

        if chip_l.startswith("nvme"):
            continue

        value = _first_temperature(chip_data)
        if value is None:
            continue

        if any(token in chip_l for token in ("iwlwifi", "mt79", "ath", "wifi", "phy")):
            group, label, keyname, icon = "WLAN", "WLAN-Karte", "wifi", "WLAN"
        elif any(token in chip_l for token in ("r8169", "igc", "e1000", "enp", "eth")):
            group, label, keyname, icon = "LAN", "Netzwerkkarte", "network", "LAN"
        elif any(token in chip_l for token in ("acpitz", "pch", "thinkpad", "dell", "asus")):
            group, label, keyname, icon = "Mainboard", "Mainboard", chip_l, "SENSOR"
        else:
            group, label, keyname, icon = "Weitere", clean_label(chip), chip_l, "SENSOR"

        rows.append({"group": group, "name": label, "temp": value,
                     "details": adapter, "key": keyname, "icon": icon})

    order = {"CPU": 0, "GPU": 1, "RAM": 2, "WLAN": 3, "LAN": 4, "Mainboard": 5, "Weitere": 6}
    rows.sort(key=lambda item: (order.get(item["group"], 9), item["name"]))
    return rows
