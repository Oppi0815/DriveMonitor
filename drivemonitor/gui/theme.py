BG = "#f3f6f8"
CARD = "#ffffff"
TEXT = "#1f2937"
MUTED = "#6b7280"
BORDER = "#dfe5ea"
GREEN = "#15803d"
YELLOW = "#b45309"
RED = "#b91c1c"
BLUE = "#2563eb"
SELECTED = "#eaf2ff"

def temp_color(value: float | None) -> str:
    if value is None: return MUTED
    if value < 45: return GREEN
    if value < 55: return YELLOW
    return RED
