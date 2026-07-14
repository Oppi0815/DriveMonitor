from drivemonitor.core.formatting import human_bytes
from drivemonitor.gui.theme import temp_color, GREEN, YELLOW, RED

def test_human_bytes():
    assert human_bytes(1024) == "1 KB"
    assert human_bytes(None) == "—"

def test_temperature_colors():
    assert temp_color(40) == GREEN
    assert temp_color(50) == YELLOW
    assert temp_color(60) == RED
