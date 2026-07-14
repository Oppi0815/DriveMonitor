from pathlib import Path


def test_rc3_sprint2_version_is_consistent() -> None:
    root = Path(__file__).parents[1]
    assert 'APP_VERSION = "5.0.0"' in (root / "drivemonitor/config.py").read_text(encoding="utf-8")
    assert "DriveMonitor Professional 5.0.0 wurde" in (root / "install.sh").read_text(encoding="utf-8")
    assert "DriveMonitor Professional 5.0.0" in (root / "README.md").read_text(encoding="utf-8")


def test_about_dialog_is_present() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    assert "def _build_menu" not in source
    assert "Über DriveMonitor Professional" in source
    assert "def _show_about" in source
    assert "github.com/Oppi0815/DriveMonitor" in source


def test_tooltips_and_event_symbols_are_present() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    tooltip_source = Path("drivemonitor/gui/tooltip.py").read_text(encoding="utf-8")
    assert "class ToolTip" in tooltip_source
    assert "CRC-Fehler entstehen meist" in source
    assert 'symbol = "✖"' in source
    assert '"⚠"' in source
    assert '"ℹ"' in source


def test_dynamic_footer_is_present() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    assert "def _footer_text" in source
    assert "Letzte SMART-Prüfung" in source
    assert "self._update_footer()" in source
