from __future__ import annotations
import json
import shutil
from pathlib import Path
from typing import Any
from .config import MODEL_ALIASES
from .utils import run, human_bytes

def extract_smart_details(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Wichtige SMART-Werte als (Bezeichnung, Wert, Status) liefern."""
    details: list[tuple[str, str, str]] = []

    ata = data.get("ata_smart_attributes")
    table = ata.get("table", []) if isinstance(ata, dict) else []
    wanted = {
        5: "Wiederzugewiesene Sektoren",
        187: "Gemeldete unkorrigierbare Fehler",
        188: "Befehls-Timeouts",
        197: "Ausstehende Sektoren",
        198: "Unkorrigierbare Sektoren",
        199: "Schnittstellenfehler (CRC)",
    }

    for attr in table:
        attr_id = attr.get("id")
        if attr_id not in wanted:
            continue
        raw = attr.get("raw", {})
        value = raw.get("value") if isinstance(raw, dict) else None
        value_i = int(value) if isinstance(value, (int, float)) else 0

        if attr_id == 188:
            raw_string = raw.get("string") if isinstance(raw, dict) else None
            if value_i == 0:
                details.append((wanted[attr_id], "Keine erkannt", "ok"))
            else:
                display = "Herstellerspezifischer Rohwert"
                if isinstance(raw_string, str) and raw_string.strip():
                    display = "Herstellerspezifischer Rohwert"
                details.append((wanted[attr_id], display, "neutral"))
        else:
            state = "ok" if value_i == 0 else "warn"
            display = "Keine" if value_i == 0 else str(value_i)
            details.append((wanted[attr_id], display, state))

    nvme = data.get("nvme_smart_health_information_log")
    if isinstance(nvme, dict):
        nvme_values = [
            ("Kritische Warnungen", nvme.get("critical_warning", 0)),
            ("Medien-/Datenfehler", nvme.get("media_errors", 0)),
            ("Fehlerprotokolleinträge", nvme.get("num_err_log_entries", 0)),
            ("Verfügbare Reserve", nvme.get("available_spare")),
        ]
        for label, value in nvme_values:
            if value is None:
                continue
            value_i = int(value)
            if label == "Verfügbare Reserve":
                details.append((label, f"{value_i} %", "ok" if value_i >= 10 else "warn"))
            else:
                details.append((label, str(value_i), "ok" if value_i == 0 else "warn"))

    if not details:
        details.append(("SMART-Selbstbewertung", "Keine Einzelwerte verfügbar", "neutral"))
    return details


def list_block_devices() -> list[dict[str, str]]:
    code, out, _ = run(["lsblk", "-J", "-b", "-d",
                        "-o", "NAME,MODEL,SIZE,TRAN,TYPE"], timeout=8)
    if code != 0:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []

    devices = []
    for dev in data.get("blockdevices", []):
        if dev.get("type") != "disk":
            continue
        name = dev.get("name", "")
        if not (name.startswith("sd") or name.startswith("nvme")):
            continue
        devices.append({
            "name": name,
            "model": (dev.get("model") or "").strip(),
            "size_bytes": int(dev.get("size") or 0),
            "tran": (dev.get("tran") or "").strip(),
        })
    return devices


def smartctl_json(device: str, extra: list[str] | None = None) -> dict[str, Any] | None:
    def parse_result(args: list[str]) -> dict[str, Any] | None:
        cmd = ["pkexec", "/usr/local/libexec/drivemonitor-smartctl", "-a", "-j"]
        cmd += args
        cmd.append(device)
        _, out, _ = run(cmd, timeout=22)
        if not out.strip():
            return None
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def score(data: dict[str, Any] | None) -> int:
        if not data:
            return -1
        points = 0
        for key in ("smart_status", "temperature", "ata_smart_attributes",
                    "nvme_smart_health_information_log", "scsi_temperature",
                    "power_on_time", "model_name", "device_model", "product"):
            if data.get(key) not in (None, {}, [], ""):
                points += 2
        messages = data.get("smartctl", {}).get("messages", [])
        if messages:
            points -= len(messages)
        return points

    if extra:
        return parse_result(extra)

    candidates = [[], ["-d", "sat"], ["-d", "sat,12"], ["-d", "sat,16"],
                  ["-d", "scsi"], ["-d", "usbjmicron"],
                  ["-d", "usbjmicron,x"], ["-d", "usbsunplus"],
                  ["-d", "sntjmicron"], ["-d", "sntrealtek"]]
    best = None
    best_score = -1
    for candidate in candidates:
        data = parse_result(candidate)
        current = score(data)
        if current > best_score:
            best = data
            best_score = current
        if current >= 5:
            break
    return best

def extract_smart_temperature(data: dict[str, Any]) -> float | None:
    temp = data.get("temperature")
    if isinstance(temp, dict) and isinstance(temp.get("current"), (int, float)):
        return float(temp["current"])

    nvme = data.get("nvme_smart_health_information_log")
    if isinstance(nvme, dict) and isinstance(nvme.get("temperature"), (int, float)):
        return float(nvme["temperature"])

    scsi = data.get("scsi_temperature")
    if isinstance(scsi, dict) and isinstance(scsi.get("current"), (int, float)):
        return float(scsi["current"])

    ata = data.get("ata_smart_attributes")
    table = ata.get("table", []) if isinstance(ata, dict) else []
    for attr in table:
        if attr.get("id") in (190, 194):
            raw = attr.get("raw", {})
            val = raw.get("value") if isinstance(raw, dict) else None
            if isinstance(val, (int, float)) and -20 <= float(val) <= 150:
                return float(val)
    return None


def extract_model(data: dict[str, Any], fallback: str) -> str:
    for key in ("model_name", "product", "device_model"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return fallback or "Unbekanntes Laufwerk"


def extract_serial(data: dict[str, Any]) -> str:
    for key in ("serial_number", "serial"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return "—"


def extract_firmware(data: dict[str, Any]) -> str:
    for key in ("firmware_version", "revision"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return "—"


def extract_hours_cycles(data: dict[str, Any]) -> tuple[int | None, int | None]:
    hours = None
    cycles = None
    power = data.get("power_on_time")
    if isinstance(power, dict) and isinstance(power.get("hours"), (int, float)):
        hours = int(power["hours"])
    if isinstance(data.get("power_cycle_count"), (int, float)):
        cycles = int(data["power_cycle_count"])

    ata = data.get("ata_smart_attributes")
    table = ata.get("table", []) if isinstance(ata, dict) else []
    for attr in table:
        raw = attr.get("raw", {})
        val = raw.get("value") if isinstance(raw, dict) else None
        if attr.get("id") == 9 and hours is None and isinstance(val, (int, float)):
            hours = int(val)
        if attr.get("id") == 12 and cycles is None and isinstance(val, (int, float)):
            cycles = int(val)

    nvme = data.get("nvme_smart_health_information_log")
    if isinstance(nvme, dict):
        if hours is None and isinstance(nvme.get("power_on_hours"), (int, float)):
            hours = int(nvme["power_on_hours"])
        if cycles is None and isinstance(nvme.get("power_cycles"), (int, float)):
            cycles = int(nvme["power_cycles"])
    return hours, cycles


def extract_ssd_life(data: dict[str, Any]) -> int | None:
    nvme = data.get("nvme_smart_health_information_log")
    if isinstance(nvme, dict) and isinstance(nvme.get("percentage_used"), (int, float)):
        return max(0, min(100, 100 - int(nvme["percentage_used"])))
    ata = data.get("ata_smart_attributes")
    table = ata.get("table", []) if isinstance(ata, dict) else []
    for attr in table:
        name = str(attr.get("name", "")).lower()
        if "remaining" in name or "life_left" in name:
            val = attr.get("value")
            if isinstance(val, (int, float)):
                return max(0, min(100, int(val)))
    return None


def filesystem_usage(device: str) -> dict[str, Any] | None:
    """Collect mounted partitions, filesystems and aggregate disk usage."""
    code, out, _ = run(["lsblk", "-J", "-b", "-o",
                        "NAME,PKNAME,FSTYPE,MOUNTPOINTS,SIZE"], timeout=8)
    if code != 0:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None

    devname = Path(device).name
    partitions: list[dict[str, Any]] = []

    def walk(nodes: list[dict[str, Any]], belongs: bool = False) -> None:
        for node in nodes:
            name = str(node.get("name") or "")
            is_member = belongs or name == devname or node.get("pkname") == devname
            if is_member and name != devname:
                mounts = [m for m in (node.get("mountpoints") or []) if m]
                partitions.append({
                    "device": f"/dev/{name}",
                    "filesystem": str(node.get("fstype") or "—"),
                    "mountpoints": mounts,
                    "size": int(node.get("size") or 0),
                })
            walk(node.get("children") or [], is_member)

    walk(data.get("blockdevices", []))

    total = used = free = 0
    mounted: list[str] = []
    for part in partitions:
        for mount in part["mountpoints"]:
            if mount in mounted:
                continue
            try:
                usage = shutil.disk_usage(mount)
            except OSError:
                continue
            mounted.append(mount)
            total += usage.total
            used += usage.used
            free += usage.free

    if not partitions and not mounted:
        return None
    return {
        "total": total,
        "used": used,
        "free": free,
        "percent": round(used / total * 100) if total else 0,
        "partitions": partitions,
        "mounted": bool(mounted),
    }


def evaluate_condition(health: str, details: list[tuple[str, str, str]]) -> tuple[str, str]:
    """Return a friendly overall condition and its severity."""
    if health == "WARNUNG":
        return "Kritisch", "critical"
    if health in ("Keine Daten", "Unbekannt"):
        return "Nicht beurteilbar", "neutral"
    warning_labels = [label for label, _, state in details if state == "warn"]
    serious = [label for label in warning_labels if "CRC" not in label]
    if serious:
        return "Beobachten", "warn"
    if warning_labels:
        return "Verbindung prüfen", "warn"
    return "Sehr gut", "ok"


def load_drives() -> list[dict[str, Any]]:
    rows = []
    for dev in list_block_devices():
        path = f"/dev/{dev['name']}"
        data = smartctl_json(path)
        if (not data or extract_smart_temperature(data) is None) and dev["tran"].lower() == "usb":
            sat_data = smartctl_json(path, ["-d", "sat"])
            if sat_data:
                data = sat_data

        if data:
            raw_model = extract_model(data, dev["model"])
            temp = extract_smart_temperature(data)
            passed = data.get("smart_status", {}).get("passed")
            health = "OK" if passed is True else ("WARNUNG" if passed is False else "Unbekannt")
            hours, cycles = extract_hours_cycles(data)
            life = extract_ssd_life(data)
            serial = extract_serial(data)
            firmware = extract_firmware(data)
            smart_details = extract_smart_details(data)
        else:
            raw_model = dev["model"] or "Unbekanntes Laufwerk"
            temp = None
            health = "Keine Daten"
            hours = cycles = life = None
            serial = firmware = "—"
            smart_details = [("SMART-Selbstbewertung", "Keine Daten", "neutral")]

        model = MODEL_ALIASES.get(raw_model, raw_model)
        transport = dev["tran"].upper() if dev["tran"] else ""
        if dev["name"].startswith("nvme"):
            icon = "NVMe"
        elif transport == "USB":
            icon = "USB"
        elif "SSD" in model.upper() or "WDS" in raw_model.upper():
            icon = "SSD"
        else:
            icon = "HDD"

        condition, condition_state = evaluate_condition(health, smart_details)
        rows.append({
            "name": model, "raw_model": raw_model, "temp": temp,
            "device": path, "size": human_bytes(dev["size_bytes"]),
            "transport": transport, "health": health, "hours": hours,
            "cycles": cycles, "life": life, "usage": filesystem_usage(path),
            "serial": serial, "firmware": firmware, "smart_details": smart_details,
            "condition": condition, "condition_state": condition_state,
            "key": path, "icon": icon,
        })
    return rows


