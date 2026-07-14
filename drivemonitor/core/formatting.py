from __future__ import annotations

def human_bytes(value: int | float | None) -> str:
    if value is None:
        return "—"
    number = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if number < 1024 or unit == "PB":
            text = f"{number:.1f} {unit}"
            return text.replace(".0 ", " ")
        number /= 1024
    return "—"
