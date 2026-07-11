from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
from typing import Any
from .config import APP_NAME, GREEN, YELLOW, ORANGE, RED, MUTED


def run(cmd: list[str], timeout: int = 12) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True,
                           timeout=timeout, check=False)
        return p.returncode, p.stdout, p.stderr
    except Exception as exc:
        return 999, "", str(exc)


def ensure_normal_user() -> None:
    if os.geteuid() == 0:
        raise SystemExit("DriveMonitor darf nicht als root gestartet werden.")


def temp_color(value: float | None) -> str:
    """Four-step temperature color scale for easier interpretation."""
    if value is None:
        return MUTED
    if value < 45:
        return GREEN
    if value < 55:
        return YELLOW
    if value < 60:
        return ORANGE
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


def notify_desktop(title: str, message: str, urgency: str = "normal") -> None:
    if not shutil.which("notify-send"):
        return
    run(["notify-send", "-u", urgency, "-a", APP_NAME, title, message], timeout=4)


def primary_monitor_geometry(default_width: int, default_height: int) -> tuple[int, int, int, int]:
    """Return x, y, width, height of the primary X11 monitor."""
    code, out, _ = run(["xrandr", "--query"], timeout=5)
    if code == 0:
        pattern = re.compile(r"^\S+ connected primary (\d+)x(\d+)\+(-?\d+)\+(-?\d+)", re.M)
        match = pattern.search(out)
        if match:
            width, height, x, y = map(int, match.groups())
            return x, y, width, height
    return 0, 0, default_width, default_height
