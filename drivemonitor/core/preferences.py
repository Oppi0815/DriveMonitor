from __future__ import annotations

import json
from pathlib import Path

APP_DATA_DIR = Path.home() / ".local" / "share" / "drivemonitor"
PREFERENCES_FILE = APP_DATA_DIR / "preferences.json"


def load_preferences() -> dict[str, object]:
    try:
        data = json.loads(PREFERENCES_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_preferences(preferences: dict[str, object]) -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = PREFERENCES_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(preferences, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(PREFERENCES_FILE)


def welcome_was_shown() -> bool:
    return bool(load_preferences().get("welcome_5_shown", False))


def mark_welcome_shown() -> None:
    preferences = load_preferences()
    preferences["welcome_5_shown"] = True
    save_preferences(preferences)
