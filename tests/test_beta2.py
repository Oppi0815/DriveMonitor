from __future__ import annotations

import json
from pathlib import Path

from drivemonitor.core import preferences


def test_preferences_roundtrip(tmp_path: Path) -> None:
    old_dir = preferences.APP_DATA_DIR
    old_file = preferences.PREFERENCES_FILE
    try:
        preferences.APP_DATA_DIR = tmp_path
        preferences.PREFERENCES_FILE = tmp_path / "preferences.json"
        assert preferences.welcome_was_shown() is False
        preferences.mark_welcome_shown()
        assert preferences.welcome_was_shown() is True
        saved = json.loads(preferences.PREFERENCES_FILE.read_text(encoding="utf-8"))
        assert saved["welcome_5_shown"] is True
    finally:
        preferences.APP_DATA_DIR = old_dir
        preferences.PREFERENCES_FILE = old_file


def test_dashboard_final_elements_are_present() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    assert "Rechnerzustand" in source
    assert "Alle erkannten Laufwerke werden regelmäßig geprüft" in source
    assert "Linux Mint" in source
