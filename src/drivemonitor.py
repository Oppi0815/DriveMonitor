#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import tkinter as tk
from pathlib import Path
from typing import Any

APP_NAME = "DriveMonitor"
APP_VERSION = "4.3.2"
REFRESH_MS = 10_000
MAX_HISTORY = 60
TEMP_WARNING = 50
TEMP_CRITICAL = 60
NOTIFY_COOLDOWN = 300

BG = "#f3f6f8"
CARD = "#ffffff"
TEXT = "#1f2937"
MUTED = "#6b7280"
BORDER = "#dfe5ea"
GREEN = "#15803d"
YELLOW = "#b45309"
RED = "#b91c1c"
BLUE = "#2563eb"
BAR_BG = "#e7ecef"
SELECTED = "#eaf2ff"

MODEL_ALIASES = {
    "ST12000NM0127": "Seagate Exos 12 TB",
    "ST4000DM000-1F2168": "Seagate Desktop HDD 4 TB",
    "WDC WDS500G2B0A": "WD Blue SSD 500 GB",
    "WD_BLACK SN850X 8000GB": "WD Black SN850X 8 TB",
    "WD_BLACK SN850X 2000GB": "WD Black SN850X 2 TB",
    "SanDisk Ultra 3D NVMe": "SanDisk Ultra 3D NVMe",
}


def run(cmd: list[str], timeout: int = 12) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True,
                           timeout=timeout, check=False)
        return p.returncode, p.stdout, p.stderr
    except Exception as exc:
        return 999, "", str(exc)


def ensure_root() -> None:
    if os.geteuid() == 0:
        return
    script = str(Path(__file__).resolve())
    pkexec = "/usr/bin/pkexec"
    if Path(pkexec).exists():
        os.execv(pkexec, [pkexec, "/usr/bin/python3", script])
    raise SystemExit("Bitte mit sudo oder über den Menüeintrag starten.")


def temp_color(value: float | None) -> str:
    if value is None:
        return MUTED
    if value < 45:
        return GREEN
    if value < 55:
        return YELLOW
    return RED


def clean_label(text: str) -> str:
    return re.sub(r"[-_]+", " ", text).strip()


def numeric_input(values: dict[str, Any], names: tuple[str, ...]) -> float | None:
    for name in names:
        for key, val in values.items():
            if key.lower() == name.lower() and isinstance(val, (int, float)):
                value = float(val)
                if -20 <= value <= 150:
                    return value
    return None


def human_bytes(num: int | float | None) -> str:
    if num is None:
        return "—"
    value = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if value < 1024 or unit == "PB":
            return f"{value:.1f} {unit}".replace(".0 ", " ")
        value /= 1024
    return "—"



def extract_smart_details(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return important SMART values as (label, value, state)."""
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
    found_ids: set[int] = set()
    for attr in table:
        attr_id = attr.get("id")
        if attr_id not in wanted:
            continue
        raw = attr.get("raw", {})
        value = raw.get("value") if isinstance(raw, dict) else None
        if not isinstance(value, (int, float)):
            value = 0
        value_i = int(value)

        # SMART 188 (Command Timeout) ist besonders bei Seagate-Laufwerken
        # häufig als zusammengesetzter, herstellerspezifischer 48-Bit-Rohwert
        # codiert. Der komplette Dezimalwert darf deshalb nicht als einfache
        # Anzahl von Timeouts bewertet werden.
        if attr_id == 188:
            raw_string = raw.get("string") if isinstance(raw, dict) else None
            if value_i == 0:
                details.append((wanted[attr_id], "Keine erkannt", "ok"))
            else:
                display = "Herstellerspezifischer Rohwert"
                if isinstance(raw_string, str) and raw_string.strip():
                    display = f"Nicht eindeutig auswertbar ({raw_string.strip()})"
                details.append((wanted[attr_id], display, "neutral"))
        else:
            state = "ok" if value_i == 0 else "warn"
            display = "Keine" if value_i == 0 else str(value_i)
            details.append((wanted[attr_id], display, state))

        found_ids.add(attr_id)

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
            if label == "Verfügbare Reserve":
                value_i = int(value)
                state = "ok" if value_i >= 10 else "warn"
                details.append((label, f"{value_i} %", state))
            else:
                value_i = int(value)
                state = "ok" if value_i == 0 else "warn"
                details.append((label, str(value_i), state))

    if not details:
        details.append(("SMART-Selbstbewertung", "Keine Einzelwerte verfügbar", "neutral"))
    return details


def notify_desktop(title: str, message: str, urgency: str = "normal") -> None:
    """Send a Linux desktop notification when notify-send is available."""
    if not shutil.which("notify-send"):
        return
    run(["notify-send", "-u", urgency, "-a", APP_NAME, title, message], timeout=4)


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

        if chip_l.startswith("k10temp"):
            for _, values in chip_data.items():
                if isinstance(values, dict):
                    value = numeric_input(values, ("Tctl_input", "temp1_input"))
                    if value is not None:
                        rows.append({"group": "CPU", "name": "AMD Ryzen CPU",
                                     "temp": value, "details": adapter,
                                     "key": "cpu", "icon": "CPU"})
                        break
            continue

        if chip_l.startswith("amdgpu"):
            values = chip_data.get("edge")
            if isinstance(values, dict):
                value = numeric_input(values, ("edge_input", "temp1_input"))
                if value is not None:
                    rows.append({"group": "GPU", "name": "Radeon-Grafik",
                                 "temp": value, "details": adapter,
                                 "key": "gpu", "icon": "GPU"})
            continue

        if chip_l.startswith("spd5118"):
            ram_index += 1
            for _, values in chip_data.items():
                if isinstance(values, dict):
                    value = numeric_input(values, ("temp1_input",))
                    if value is not None:
                        rows.append({"group": "RAM", "name": f"RAM-Modul {ram_index}",
                                     "temp": value, "details": clean_label(chip),
                                     "key": f"ram{ram_index}", "icon": "RAM"})
                        break
            continue

        if chip_l.startswith("nvme"):
            continue

        if "mt79" in chip_l or "phy" in chip_l:
            label, keyname = "WLAN-Karte", "wifi"
        elif "r8169" in chip_l:
            label, keyname = "Netzwerkkarte", "network"
        else:
            label, keyname = clean_label(chip), chip_l

        found = False
        for feature, values in chip_data.items():
            if not isinstance(values, dict):
                continue
            for key, val in values.items():
                if (isinstance(val, (int, float))
                        and key.lower().endswith("_input")
                        and ("temp" in key.lower() or feature.lower().startswith("temp"))):
                    value = float(val)
                    if -20 <= value <= 150:
                        rows.append({"group": "Weitere", "name": label,
                                     "temp": value, "details": adapter,
                                     "key": keyname, "icon": "SENSOR"})
                        found = True
                        break
            if found:
                break
    return rows


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
    cmd = ["smartctl", "-a", "-j"]
    if extra:
        cmd += extra
    cmd.append(device)
    _, out, _ = run(cmd, timeout=18)
    if not out.strip():
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


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
    code, out, _ = run(["lsblk", "-J", "-b", "-o",
                        "NAME,PKNAME,FSTYPE,MOUNTPOINTS,SIZE"], timeout=8)
    if code != 0:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None

    devname = Path(device).name
    mounts: list[str] = []

    def walk(nodes: list[dict[str, Any]]) -> None:
        for node in nodes:
            if node.get("name") == devname or node.get("pkname") == devname:
                for mount in node.get("mountpoints") or []:
                    if mount:
                        mounts.append(mount)
            walk(node.get("children") or [])
    walk(data.get("blockdevices", []))

    total = used = free = 0
    found = False
    for mount in sorted(set(mounts)):
        try:
            u = shutil.disk_usage(mount)
            total += u.total
            used += u.used
            free += u.free
            found = True
        except OSError:
            pass
    if not found:
        return None
    return {"total": total, "used": used, "free": free,
            "percent": round(used / total * 100) if total else 0}


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

        rows.append({
            "name": model, "raw_model": raw_model, "temp": temp,
            "device": path, "size": human_bytes(dev["size_bytes"]),
            "transport": transport, "health": health, "hours": hours,
            "cycles": cycles, "life": life, "usage": filesystem_usage(path),
            "serial": serial, "firmware": firmware, "smart_details": smart_details,
            "key": path, "icon": icon,
        })
    return rows


class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION} – B650")
        self.configure(bg=BG)

        # Fenster automatisch an den Bildschirm anpassen:
        # etwas höher als bisher und rechts am Bildschirmrand positioniert.
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        window_w = min(1040, max(900, screen_w - 40))
        window_h = min(940, max(680, screen_h - 80))

        pos_x = max(0, screen_w - window_w - 10)
        pos_y = max(0, (screen_h - window_h) // 2)

        self.geometry(f"{window_w}x{window_h}+{pos_x}+{pos_y}")
        self.minsize(900, 620)
        self.drives: list[dict[str, Any]] = []
        self.sensors: list[dict[str, Any]] = []
        self.selected_device: str | None = None
        self.history: dict[str, list[float]] = {}
        self.drive_buttons: list[tuple[tk.Frame, dict[str, Any]]] = []
        self.after_id = None
        self.previous_snapshot: dict[str, dict[str, Any]] = {}
        self.events: list[str] = []
        self.last_notifications: dict[str, float] = {}

        self.build_header()
        self.build_summary()
        self.build_main()
        self.build_sensors()
        self.after(250, self.refresh)

    def build_header(self) -> None:
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=18, pady=(10, 6))

        tk.Label(header, text="DriveMonitor", font=("Sans", 20, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(header, text=APP_VERSION, font=("Sans", 9, "bold"),
                 bg=BG, fg=BLUE).pack(side="left", padx=(7, 0), pady=(5, 0))

        self.refresh_btn = tk.Button(
            header, text="Aktualisieren", command=self.refresh,
            relief="flat", padx=12, pady=5, cursor="hand2",
            bg="#e7ecef", fg=TEXT, activebackground="#d9e1e5"
        )
        self.refresh_btn.pack(side="right")
        self.status = tk.Label(header, text="", font=("Sans", 9),
                               bg=BG, fg=MUTED)
        self.status.pack(side="right", padx=(0, 14))

    def build_summary(self) -> None:
        self.summary = tk.Frame(self, bg=BG)
        self.summary.pack(fill="x", padx=18, pady=(0, 7))

    def build_main(self) -> None:
        self.main = tk.Frame(self, bg=BG)
        self.main.pack(fill="both", expand=True, padx=18, pady=(0, 7))
        self.main.grid_columnconfigure(0, weight=0, minsize=320)
        self.main.grid_columnconfigure(1, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

        left = tk.Frame(self.main, bg=CARD, highlightthickness=1,
                        highlightbackground=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        tk.Label(left, text="Laufwerke", font=("Sans", 11, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w", padx=10, pady=(9, 5))
        self.drive_list = tk.Frame(left, bg=CARD)
        self.drive_list.pack(fill="both", expand=True, padx=7, pady=(0, 7))

        self.detail = tk.Frame(self.main, bg=CARD, highlightthickness=1,
                               highlightbackground=BORDER)
        self.detail.grid(row=0, column=1, sticky="nsew")

    def build_sensors(self) -> None:
        self.bottom_area = tk.Frame(self, bg=BG)
        self.bottom_area.pack(fill="x", padx=18, pady=(0, 10))
        self.bottom_area.grid_columnconfigure(0, weight=3)
        self.bottom_area.grid_columnconfigure(1, weight=2)

        self.sensor_area = tk.Frame(self.bottom_area, bg=BG)
        self.sensor_area.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.event_area = tk.Frame(self.bottom_area, bg=BG)
        self.event_area.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    def update_history(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            key = row.get("key")
            temp = row.get("temp")
            if key and isinstance(temp, (int, float)):
                vals = self.history.setdefault(key, [])
                vals.append(float(temp))
                if len(vals) > MAX_HISTORY:
                    del vals[:-MAX_HISTORY]

    def add_event(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        entry = f"{stamp}  {message}"
        if not self.events or self.events[0] != entry:
            self.events.insert(0, entry)
        del self.events[8:]

    def maybe_notify(self, key: str, title: str, message: str,
                     urgency: str = "normal") -> None:
        now = time.time()
        if now - self.last_notifications.get(key, 0) < NOTIFY_COOLDOWN:
            return
        self.last_notifications[key] = now
        notify_desktop(title, message, urgency)

    def process_events(self) -> None:
        current = {d["device"]: d for d in self.drives}

        if not self.previous_snapshot:
            self.add_event(f"{len(self.drives)} Laufwerke erkannt")
        else:
            for device, drive in current.items():
                old = self.previous_snapshot.get(device)
                if old is None:
                    self.add_event(f"{drive['name']} wurde angeschlossen")
                    self.maybe_notify(device + ":added", "Laufwerk angeschlossen",
                                      drive["name"])
                    continue

                old_health = old.get("health")
                new_health = drive.get("health")
                if old_health != new_health:
                    self.add_event(
                        f"{drive['name']}: SMART {old_health} → {new_health}")
                    if new_health == "WARNUNG":
                        self.maybe_notify(device + ":smart", "SMART-Warnung",
                                          drive["name"], "critical")

                old_temp = old.get("temp")
                new_temp = drive.get("temp")
                if isinstance(new_temp, (int, float)):
                    if new_temp >= TEMP_CRITICAL and (
                            not isinstance(old_temp, (int, float))
                            or old_temp < TEMP_CRITICAL):
                        self.add_event(
                            f"{drive['name']}: kritische Temperatur {new_temp:.1f} °C")
                        self.maybe_notify(device + ":critical",
                                          "Kritische Laufwerkstemperatur",
                                          f"{drive['name']}: {new_temp:.1f} °C",
                                          "critical")
                    elif new_temp >= TEMP_WARNING and (
                            not isinstance(old_temp, (int, float))
                            or old_temp < TEMP_WARNING):
                        self.add_event(
                            f"{drive['name']}: Temperaturwarnung {new_temp:.1f} °C")
                        self.maybe_notify(device + ":warm",
                                          "Laufwerk wird warm",
                                          f"{drive['name']}: {new_temp:.1f} °C")

            for device, old in self.previous_snapshot.items():
                if device not in current:
                    self.add_event(f"{old['name']} wurde entfernt")

        self.previous_snapshot = {
            device: {
                "name": drive["name"],
                "health": drive.get("health"),
                "temp": drive.get("temp"),
            }
            for device, drive in current.items()
        }

    def refresh(self) -> None:
        if self.after_id:
            self.after_cancel(self.after_id)
        self.refresh_btn.config(state="disabled")
        self.status.config(text="Wird aktualisiert …")
        self.update_idletasks()

        try:
            self.sensors = load_sensors()
            self.drives = load_drives()
            self.update_history(self.sensors + self.drives)
            self.process_events()
            if not self.selected_device and self.drives:
                self.selected_device = self.drives[0]["device"]
            if self.selected_device and not any(d["device"] == self.selected_device for d in self.drives):
                self.selected_device = self.drives[0]["device"] if self.drives else None
            self.render_summary()
            self.render_drive_list()
            self.render_detail()
            self.render_sensors()
            self.render_events()
            self.status.config(text=time.strftime("Aktualisiert: %H:%M:%S"))
        except Exception as exc:
            self.status.config(text=f"Fehler: {exc}")
        finally:
            self.refresh_btn.config(state="normal")
            self.after_id = self.after(REFRESH_MS, self.refresh)

    def render_summary(self) -> None:
        for w in self.summary.winfo_children():
            w.destroy()

        temps = [d["temp"] for d in self.drives if isinstance(d.get("temp"), (int, float))]
        hottest = max(temps) if temps else None
        smart_ok = sum(1 for d in self.drives if d.get("health") == "OK")
        cpu = next((s for s in self.sensors if s.get("group") == "CPU"), None)
        gpu = next((s for s in self.sensors if s.get("group") == "GPU"), None)

        items = [
            ("Laufwerke", str(len(self.drives)), "erkannt", BLUE),
            ("SMART", f"{smart_ok}/{len(self.drives)} OK" if self.drives else "—",
             "Gesundheitsstatus", GREEN if smart_ok == len(self.drives) and self.drives else YELLOW),
            ("Höchste Temperatur", "—" if hottest is None else f"{hottest:.1f} °C",
             "aller Laufwerke", temp_color(hottest)),
            ("CPU / GPU",
             f"{cpu['temp']:.0f}° / {gpu['temp']:.0f}°" if cpu and gpu else "—",
             "Systemsensoren", GREEN),
        ]

        for i, (title, value, sub, color) in enumerate(items):
            box = tk.Frame(self.summary, bg=CARD, highlightthickness=1,
                           highlightbackground=BORDER)
            box.grid(row=0, column=i, sticky="nsew",
                     padx=(0 if i == 0 else 3, 0 if i == len(items)-1 else 3))
            self.summary.grid_columnconfigure(i, weight=1)
            tk.Label(box, text=title, font=("Sans", 8, "bold"),
                     bg=CARD, fg=MUTED).pack(anchor="w", padx=9, pady=(5, 0))
            tk.Label(box, text=value, font=("Sans", 14, "bold"),
                     bg=CARD, fg=color).pack(anchor="w", padx=9)
            tk.Label(box, text=sub, font=("Sans", 7),
                     bg=CARD, fg=MUTED).pack(anchor="w", padx=9, pady=(0, 5))

    def select_drive(self, device: str) -> None:
        self.selected_device = device
        self.render_drive_list()
        self.render_detail()

    def render_drive_list(self) -> None:
        for w in self.drive_list.winfo_children():
            w.destroy()
        self.drive_buttons.clear()

        for drive in self.drives:
            selected = drive["device"] == self.selected_device
            bg = SELECTED if selected else CARD
            frame = tk.Frame(self.drive_list, bg=bg, cursor="hand2",
                             highlightthickness=1,
                             highlightbackground=BLUE if selected else BORDER)
            frame.pack(fill="x", pady=2)

            icon = tk.Label(frame, text=drive["icon"], width=5,
                            font=("Sans", 8, "bold"), bg=bg,
                            fg=BLUE)
            icon.pack(side="left", padx=(5, 4), pady=7)

            info = tk.Frame(frame, bg=bg)
            info.pack(side="left", fill="x", expand=True, pady=5)
            tk.Label(info, text=drive["name"], font=("Sans", 9, "bold"),
                     bg=bg, fg=TEXT, anchor="w").pack(fill="x")
            tk.Label(info, text=f"{drive['device']} · {drive['size']}",
                     font=("Sans", 7), bg=bg, fg=MUTED,
                     anchor="w").pack(fill="x")

            temp = drive.get("temp")
            temp_label = tk.Label(frame,
                                  text="—" if temp is None else f"{temp:.0f}°",
                                  font=("Sans", 11, "bold"), bg=bg,
                                  fg=temp_color(temp))
            temp_label.pack(side="right", padx=8)

            for widget in (frame, icon, info, temp_label):
                widget.bind("<Button-1>",
                            lambda e, dev=drive["device"]: self.select_drive(dev))
            for child in info.winfo_children():
                child.bind("<Button-1>",
                           lambda e, dev=drive["device"]: self.select_drive(dev))

    def selected(self) -> dict[str, Any] | None:
        return next((d for d in self.drives if d["device"] == self.selected_device), None)

    def render_detail(self) -> None:
        for w in self.detail.winfo_children():
            w.destroy()
        d = self.selected()
        if not d:
            tk.Label(self.detail, text="Kein Laufwerk erkannt.",
                     bg=CARD, fg=MUTED).pack(pady=40)
            return

        head = tk.Frame(self.detail, bg=CARD)
        head.pack(fill="x", padx=14, pady=(11, 4))
        tk.Label(head, text=d["name"], font=("Sans", 15, "bold"),
                 bg=CARD, fg=TEXT).pack(side="left")
        tk.Label(head, text="—" if d["temp"] is None else f"{d['temp']:.1f} °C",
                 font=("Sans", 20, "bold"), bg=CARD,
                 fg=temp_color(d["temp"])).pack(side="right")

        status_bg = "#ecfdf5" if d["health"] == "OK" else "#fff7ed"
        status_fg = GREEN if d["health"] == "OK" else YELLOW
        status = tk.Frame(self.detail, bg=status_bg)
        status.pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(status, text=f"SMART-Zustand: {d['health']}",
                 font=("Sans", 9, "bold"), bg=status_bg,
                 fg=status_fg).pack(anchor="w", padx=9, pady=5)

        facts = tk.Frame(self.detail, bg=CARD)
        facts.pack(fill="x", padx=14)
        fields = [
            ("Gerät", d["device"]),
            ("Kapazität", d["size"]),
            ("Schnittstelle", d["transport"] or "—"),
            ("Firmware", d["firmware"]),
            ("Seriennummer", d["serial"]),
            ("Betriebsstunden", "—" if d["hours"] is None else f"{d['hours']:,}".replace(",", ".")),
            ("Einschaltungen", "—" if d["cycles"] is None else f"{d['cycles']:,}".replace(",", ".")),
            ("SSD-Lebensdauer", "—" if d["life"] is None else f"{d['life']} %"),
        ]
        for i, (label, value) in enumerate(fields):
            r, c = divmod(i, 2)
            cell = tk.Frame(facts, bg=CARD)
            cell.grid(row=r, column=c, sticky="ew", padx=(0, 12), pady=3)
            facts.grid_columnconfigure(c, weight=1)
            tk.Label(cell, text=label, font=("Sans", 7, "bold"),
                     bg=CARD, fg=MUTED).pack(anchor="w")
            tk.Label(cell, text=value, font=("Sans", 9),
                     bg=CARD, fg=TEXT).pack(anchor="w")

        tk.Label(self.detail, text="Wichtige SMART-Werte",
                 font=("Sans", 9, "bold"), bg=CARD, fg=TEXT).pack(
                     anchor="w", padx=14, pady=(7, 2))
        smart_grid = tk.Frame(self.detail, bg=CARD)
        smart_grid.pack(fill="x", padx=14)
        for i, (label, value, state) in enumerate(d.get("smart_details", [])[:4]):
            r, c = divmod(i, 2)
            cell = tk.Frame(smart_grid, bg="#fafbfc",
                            highlightthickness=1, highlightbackground=BORDER)
            cell.grid(row=r, column=c, sticky="ew", padx=(0, 5), pady=2)
            smart_grid.grid_columnconfigure(c, weight=1)
            indicator = "✓" if state == "ok" else ("!" if state == "warn" else "•")
            color = GREEN if state == "ok" else (RED if state == "warn" else MUTED)
            tk.Label(cell, text=f"{indicator}  {label}", font=("Sans", 7),
                     bg="#fafbfc", fg=MUTED).pack(
                         side="left", padx=6, pady=3)
            tk.Label(cell, text=value, font=("Sans", 7, "bold"),
                     bg="#fafbfc", fg=color).pack(
                         side="right", padx=6, pady=3)

        usage = d.get("usage")
        tk.Label(self.detail, text="Laufwerksbelegung", font=("Sans", 9, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w", padx=14, pady=(8, 3))
        bar = tk.Canvas(self.detail, height=14, bg=BAR_BG, highlightthickness=0)
        bar.pack(fill="x", padx=14)
        percent = usage["percent"] if usage else 0
        bar.bind("<Configure>", lambda e, c=bar, p=percent: self.draw_usage(c, p))
        usage_text = ("Keine eingehängte Partition erkannt" if not usage else
                      f"Belegt {human_bytes(usage['used'])} · Frei {human_bytes(usage['free'])} · {usage['percent']} %")
        tk.Label(self.detail, text=usage_text, font=("Sans", 8),
                 bg=CARD, fg=MUTED).pack(anchor="w", padx=14, pady=(3, 7))

        tk.Label(self.detail, text="Temperaturverlauf", font=("Sans", 9, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w", padx=14)
        chart = tk.Canvas(self.detail, height=46, bg="#fafbfc",
                          highlightthickness=1, highlightbackground=BORDER)
        chart.pack(fill="x", padx=14, pady=(3, 12))
        vals = list(self.history.get(d["key"], []))
        chart.bind("<Configure>",
                   lambda e, c=chart, v=vals: self.draw_chart(c, v))

    def draw_usage(self, canvas: tk.Canvas, percent: int) -> None:
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        canvas.create_rectangle(0, 0, w, h, fill=BAR_BG, outline="")
        canvas.create_rectangle(0, 0, w * max(0, min(100, percent)) / 100, h,
                                fill=GREEN if percent < 85 else YELLOW, outline="")

    def draw_chart(self, canvas: tk.Canvas, values: list[float]) -> None:
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if len(values) < 2:
            canvas.create_text(w/2, h/2, text="Der Verlauf wird nach einigen Aktualisierungen sichtbar.",
                               fill=MUTED, font=("Sans", 8))
            return
        low, high = min(values), max(values)
        if high - low < 1:
            high = low + 1
        points = []
        for i, val in enumerate(values):
            x = 5 + i * (w - 10) / max(1, len(values)-1)
            y = h - 5 - (val - low) / (high - low) * (h - 10)
            points.extend([x, y])
        canvas.create_line(*points, fill=temp_color(values[-1]),
                           width=2, smooth=True)
        canvas.create_text(7, 6, text=f"{high:.0f}°", anchor="nw",
                           fill=MUTED, font=("Sans", 7))
        canvas.create_text(7, h-6, text=f"{low:.0f}°", anchor="sw",
                           fill=MUTED, font=("Sans", 7))

    def render_sensors(self) -> None:
        for w in self.sensor_area.winfo_children():
            w.destroy()
        tk.Label(self.sensor_area, text="Systemsensoren", font=("Sans", 10, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 3))
        row = tk.Frame(self.sensor_area, bg=BG)
        row.pack(fill="x")
        if not self.sensors:
            tk.Label(row, text="Keine zusätzlichen Sensoren erkannt.",
                     bg=BG, fg=MUTED).pack(anchor="w")
            return
        for i, s in enumerate(self.sensors[:6]):
            card = tk.Frame(row, bg=CARD, highlightthickness=1,
                            highlightbackground=BORDER)
            card.grid(row=0, column=i, sticky="nsew",
                      padx=(0 if i == 0 else 2, 0 if i == len(self.sensors[:6])-1 else 2))
            row.grid_columnconfigure(i, weight=1)
            tk.Label(card, text=s["name"], font=("Sans", 7, "bold"),
                     bg=CARD, fg=MUTED).pack(anchor="w", padx=7, pady=(4, 0))
            tk.Label(card, text=f"{s['temp']:.1f} °C",
                     font=("Sans", 11, "bold"), bg=CARD,
                     fg=temp_color(s["temp"])).pack(anchor="w", padx=7, pady=(0, 4))


    def render_events(self) -> None:
        for w in self.event_area.winfo_children():
            w.destroy()

        tk.Label(self.event_area, text="Ereignisse",
                 font=("Sans", 10, "bold"), bg=BG, fg=TEXT).pack(
                     anchor="w", pady=(0, 3))
        box = tk.Frame(self.event_area, bg=CARD, highlightthickness=1,
                       highlightbackground=BORDER)
        box.pack(fill="both", expand=True)

        if not self.events:
            tk.Label(box, text="Noch keine Ereignisse.",
                     font=("Sans", 8), bg=CARD, fg=MUTED).pack(
                         anchor="w", padx=8, pady=8)
            return

        for entry in self.events[:4]:
            tk.Label(box, text=entry, font=("Sans", 7),
                     bg=CARD, fg=TEXT, anchor="w").pack(
                         fill="x", padx=8, pady=1)


if __name__ == "__main__":
    ensure_root()
    Dashboard().mainloop()
