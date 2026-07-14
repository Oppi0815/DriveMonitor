from __future__ import annotations

from pathlib import Path


def test_rc3_sprint1_version_is_consistent() -> None:
    root = Path(__file__).parents[1]
    config = (root / "drivemonitor" / "config.py").read_text(encoding="utf-8")
    installer = (root / "install.sh").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert 'APP_VERSION = "5.0.0"' in config
    assert "DriveMonitor Professional 5.0.0 wurde" in installer
    assert "DriveMonitor Professional 5.0.0" in readme


def test_refresh_is_guarded_against_overlap() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    assert "self.refresh_in_progress = False" in source
    assert "if self.closing or self.refresh_in_progress:" in source
    assert "self.refresh_in_progress = True" in source
    assert "def _finish_refresh_cycle" in source


def test_worker_uses_threadsafe_result_queue() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    assert "queue.Queue" in source
    assert "self._result_queue.put" in source
    assert "def _poll_results" in source
    assert "self.after(100, self._poll_results)" in source


def test_close_cancels_automatic_refresh() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    assert 'self.protocol("WM_DELETE_WINDOW", self._on_close)' in source
    assert "def _on_close" in source
    assert "self.after_cancel(self.refresh_job)" in source
