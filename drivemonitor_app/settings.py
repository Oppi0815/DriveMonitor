from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "drivemonitor"
CONFIG_FILE = CONFIG_DIR / "settings.json"
DEFAULTS: dict[str, Any] = {
    "refresh_seconds": 10,
    "notifications_enabled": True,
    "window_geometry": "",
}


def load_settings() -> dict[str, Any]:
    settings = dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return settings
    if not isinstance(data, dict):
        return settings

    refresh = data.get("refresh_seconds")
    if isinstance(refresh, int) and refresh in (5, 10, 30, 60):
        settings["refresh_seconds"] = refresh

    notifications = data.get("notifications_enabled")
    if isinstance(notifications, bool):
        settings["notifications_enabled"] = notifications

    geometry = data.get("window_geometry")
    if isinstance(geometry, str) and len(geometry) <= 80:
        settings["window_geometry"] = geometry
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "refresh_seconds": int(settings.get("refresh_seconds", 10)),
        "notifications_enabled": bool(settings.get("notifications_enabled", True)),
        "window_geometry": str(settings.get("window_geometry", "")),
    }
    temporary = CONFIG_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(CONFIG_FILE)
