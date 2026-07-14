from pathlib import Path


def test_rc1_version_is_consistent() -> None:
    root = Path(__file__).parents[1]
    config = (root / "drivemonitor" / "config.py").read_text(encoding="utf-8")
    installer = (root / "install.sh").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert 'APP_VERSION = "5.0.0"' in config
    assert "DriveMonitor Professional 5.0.0 wurde" in installer
    assert "DriveMonitor Professional 5.0.0" in readme


def test_summary_has_no_duplicate_health_card() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    summary_start = source.index("    def _render_summary")
    summary_end = source.index("    def _last_check_text")
    summary_source = source[summary_start:summary_end]
    assert '"Systemgesundheit"' not in summary_source
    assert '"Laufwerke"' in summary_source
    assert '"Temperaturen"' in summary_source
    assert '"Systemupdates"' in summary_source
    assert '"Letzte Prüfung"' in summary_source


def test_relative_last_check_text_is_present() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    assert "gerade eben" in source
    assert "vor 1 Minute" in source
    assert "automatisch aktualisiert" in source
