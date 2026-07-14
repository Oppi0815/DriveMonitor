from pathlib import Path


def test_main_window_contains_scrollable_page():
    source = (Path(__file__).parents[1] / "drivemonitor" / "gui" / "window.py").read_text()
    assert "self.main_canvas = tk.Canvas" in source
    assert "self.main_scrollbar = tk.Scrollbar" in source
    assert "command=self.main_canvas.yview" in source
    assert "self.main_canvas.itemconfigure(self._page_window, width=event.width)" in source


def test_linux_mousewheel_is_supported():
    source = (Path(__file__).parents[1] / "drivemonitor" / "gui" / "window.py").read_text()
    assert '"<Button-4>"' in source
    assert '"<Button-5>"' in source
