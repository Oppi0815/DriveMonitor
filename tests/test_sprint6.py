from pathlib import Path


def test_sparkline_module_exists_and_has_empty_state():
    source = (Path(__file__).parents[1] / "drivemonitor" / "gui" / "sparkline.py").read_text()
    assert "class Sparkline" in source
    assert "Verlauf wird aufgebaut" in source
    assert "create_line" in source


def test_main_window_uses_drive_and_sensor_history():
    source = (Path(__file__).parents[1] / "drivemonitor" / "gui" / "window.py").read_text()
    assert "load_drive_temperature_history" in source
    assert "load_sensor_temperature_history" in source
    assert 'text="Temperaturverlauf"' in source
    assert "_sensor_card" in source


def test_history_has_read_only_temperature_queries():
    source = (Path(__file__).parents[1] / "drivemonitor" / "core" / "history.py").read_text()
    assert "def load_drive_temperature_history" in source
    assert "def load_sensor_temperature_history" in source
    assert "ORDER BY recorded_at DESC" in source
    assert "reversed(rows)" in source


def test_compact_event_strip_is_present():
    source = (Path(__file__).parents[1] / "drivemonitor" / "gui" / "window.py").read_text()
    assert "keine Warnungen" in source
    assert "compact_message" in source
