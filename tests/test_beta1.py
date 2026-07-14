from pathlib import Path


def test_beta_version_is_consistent():
    root = Path(__file__).parents[1]
    config = (root / "drivemonitor" / "config.py").read_text()
    installer = (root / "install.sh").read_text()
    readme = (root / "README.md").read_text()
    assert 'APP_VERSION = "5.0.0"' in config
    assert "DriveMonitor Professional 5.0.0 wurde" in installer
    assert "DriveMonitor Professional 5.0.0" in readme


def test_desktop_entry_uses_professional_name():
    installer = (Path(__file__).parents[1] / "install.sh").read_text()
    assert "Name=DriveMonitor Professional" in installer
