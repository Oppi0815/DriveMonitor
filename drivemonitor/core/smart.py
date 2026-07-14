from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from drivemonitor.config import MODEL_ALIASES, SMART_HELPER
from .command import run
from .devices import list_block_devices
from .formatting import human_bytes
from .models import DriveInfo, SmartItem

def _parse(device: str, device_type: str | None = None) -> dict[str, Any] | None:
    helper = Path(SMART_HELPER)
    command = ["sudo", "-n", str(helper), "-a", "-j"] if helper.exists() else ["smartctl", "-a", "-j"]
    if device_type:
        command += ["-d", device_type]
    command.append(device)
    result = run(command, timeout=22)
    if not result.stdout.strip():
        return None
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None

def _score(data: dict[str, Any] | None) -> int:
    if not data:
        return -1
    return sum(1 for key in ("smart_status", "temperature", "ata_smart_attributes", "nvme_smart_health_information_log", "power_on_time", "model_name") if data.get(key) not in (None, {}, [], ""))

def read_smart(device: str, is_usb: bool) -> dict[str, Any] | None:
    candidates: list[str | None] = [None]
    if is_usb:
        candidates += ["sat", "sat,12", "sat,16", "scsi", "usbjmicron", "sntjmicron", "sntrealtek"]
    best = None
    best_score = -1
    for candidate in candidates:
        current = _parse(device, candidate)
        score = _score(current)
        if score > best_score:
            best, best_score = current, score
        if score >= 3:
            break
    return best

def _temperature(data: dict[str, Any]) -> float | None:
    temp = data.get("temperature")
    if isinstance(temp, dict) and isinstance(temp.get("current"), (int, float)):
        return float(temp["current"])
    nvme = data.get("nvme_smart_health_information_log")
    if isinstance(nvme, dict) and isinstance(nvme.get("temperature"), (int, float)):
        return float(nvme["temperature"])
    scsi = data.get("scsi_temperature")
    if isinstance(scsi, dict) and isinstance(scsi.get("current"), (int, float)):
        return float(scsi["current"])
    return None

def _hours_cycles(data: dict[str, Any]) -> tuple[int | None, int | None]:
    hours = None
    cycles = None
    power = data.get("power_on_time")
    if isinstance(power, dict) and isinstance(power.get("hours"), (int, float)):
        hours = int(power["hours"])
    if isinstance(data.get("power_cycle_count"), (int, float)):
        cycles = int(data["power_cycle_count"])
    nvme = data.get("nvme_smart_health_information_log")
    if isinstance(nvme, dict):
        if hours is None and isinstance(nvme.get("power_on_hours"), (int, float)):
            hours = int(nvme["power_on_hours"])
        if cycles is None and isinstance(nvme.get("power_cycles"), (int, float)):
            cycles = int(nvme["power_cycles"])
    return hours, cycles

def _life(data: dict[str, Any]) -> int | None:
    nvme = data.get("nvme_smart_health_information_log")
    if isinstance(nvme, dict) and isinstance(nvme.get("percentage_used"), (int, float)):
        return max(0, min(100, 100 - int(nvme["percentage_used"])))
    return None

def _important_values(data: dict[str, Any]) -> list[SmartItem]:
    output: list[SmartItem] = []
    ata = data.get("ata_smart_attributes")
    table = ata.get("table", []) if isinstance(ata, dict) else []
    wanted = {
        5: ("Wiederzugewiesene Sektoren", "critical"),
        187: ("Unkorrigierbare Fehler", "critical"),
        197: ("Ausstehende Sektoren", "critical"),
        198: ("Unkorrigierbare Sektoren", "critical"),
        199: ("CRC-Fehler", "warning"),
    }
    for item in table:
        attribute_id = item.get("id")
        if attribute_id not in wanted:
            continue
        raw = item.get("raw", {})
        try:
            value = int(raw.get("value") or 0) if isinstance(raw, dict) else 0
        except (TypeError, ValueError):
            value = 0
        label, nonzero_state = wanted[attribute_id]
        output.append(SmartItem(label, str(value), "ok" if value == 0 else nonzero_state))

    nvme = data.get("nvme_smart_health_information_log")
    if isinstance(nvme, dict):
        critical_warning = int(nvme.get("critical_warning") or 0)
        media_errors = int(nvme.get("media_errors") or 0)
        error_log_entries = int(nvme.get("num_err_log_entries") or 0)
        output.extend(
            [
                SmartItem("Kritische Warnungen", str(critical_warning), "ok" if critical_warning == 0 else "critical"),
                SmartItem("Medien-/Datenfehler", str(media_errors), "ok" if media_errors == 0 else "critical"),
                # NVMe-Fehlerprotokolleinträge sind ein kumulativer Zähler und allein kein Defektnachweis.
                SmartItem("Fehlerprotokolleinträge", str(error_log_entries), "ok" if error_log_entries == 0 else "info"),
            ]
        )
    return output or [SmartItem("SMART-Einzelwerte", "Nicht verfügbar")]

def load_drives() -> list[DriveInfo]:
    drives: list[DriveInfo] = []
    for item in list_block_devices():
        data = read_smart(item["device"], item["transport"] == "USB")
        kind = "NVMe" if item["name"].startswith("nvme") else ("USB" if item["transport"] == "USB" else ("HDD" if item["rotational"] else "SSD"))
        if not data:
            drives.append(DriveInfo(item["device"], MODEL_ALIASES.get(item["model"], item["model"] or "Unbekanntes Laufwerk"), human_bytes(item["size"]), item["transport"], kind, health="Keine Daten", error="SMART-Daten konnten nicht gelesen werden."))
            continue
        raw_name = next((str(data.get(key)).strip() for key in ("model_name", "device_model", "product") if data.get(key)), item["model"] or "Unbekanntes Laufwerk")
        passed = data.get("smart_status", {}).get("passed")
        health = "OK" if passed is True else ("WARNUNG" if passed is False else "Unbekannt")
        hours, cycles = _hours_cycles(data)
        drives.append(DriveInfo(
            device=item["device"], name=MODEL_ALIASES.get(raw_name, raw_name), size=human_bytes(item["size"]),
            transport=item["transport"], kind=kind, temperature=_temperature(data), health=health,
            serial=str(data.get("serial_number") or "—"), firmware=str(data.get("firmware_version") or data.get("revision") or "—"),
            power_on_hours=hours, power_cycles=cycles, life_remaining=_life(data), smart_items=_important_values(data)))
    return drives
