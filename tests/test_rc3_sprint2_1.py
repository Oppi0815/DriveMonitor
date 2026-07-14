from pathlib import Path


def test_only_one_tooltip_can_be_active() -> None:
    source = Path("drivemonitor/gui/tooltip.py").read_text(encoding="utf-8")
    assert '_active: "ToolTip | None" = None' in source
    assert "active._hide()" in source
    assert "ToolTip._active = self" in source


def test_about_is_visible_and_keyboard_accessible() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    assert 'text="Über"' in source
    assert 'self.bind("<F1>"' in source
    assert 'dialog.title("Über DriveMonitor Professional")' in source


def test_mousewheel_scrolls_one_step() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    start = source.index("    def _on_main_mousewheel")
    end = source.index("    def refresh", start)
    function = source[start:end]
    assert function.count('self.main_canvas.yview_scroll(steps, "units")') == 1
