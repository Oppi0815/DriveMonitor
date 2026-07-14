from pathlib import Path


def test_rc3_sprint3_version_is_consistent() -> None:
    root = Path(__file__).parents[1]
    assert 'APP_VERSION = "5.0.0"' in (root / "drivemonitor/config.py").read_text(encoding="utf-8")
    assert "DriveMonitor Professional 5.0.0 wurde" in (root / "install.sh").read_text(encoding="utf-8")
    assert "DriveMonitor Professional 5.0.0" in (root / "README.md").read_text(encoding="utf-8")


def test_redundant_help_menu_is_removed() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    assert "def _build_menu" not in source
    assert "menubar.add_cascade" not in source
    assert 'text="Über"' in source
    assert 'text="Hilfe"' not in source


def test_about_dialog_is_clearly_named_and_polished() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    assert 'dialog.title("Über DriveMonitor Professional")' in source
    assert '"GNU GPL v3"' in source
    assert '"Betriebssystem"' in source
    assert '"Kernel"' in source
    assert '"Python"' in source
    assert "github.com/Oppi0815/DriveMonitor" in source
    assert 'dialog.bind("<Escape>"' in source
