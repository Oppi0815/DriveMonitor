from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from drivemonitor.core.command import CommandResult
from drivemonitor.maintenance import checks


def test_rc2_version_is_consistent() -> None:
    root = Path(__file__).parents[1]
    config = (root / "drivemonitor" / "config.py").read_text(encoding="utf-8")
    installer = (root / "install.sh").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert 'APP_VERSION = "5.0.0"' in config
    assert "DriveMonitor Professional 5.0.0 wurde" in installer
    assert "DriveMonitor Professional 5.0.0" in readme


def test_mintupdate_count_matches_nonempty_list_rows() -> None:
    with patch.object(checks.shutil, "which", return_value="/usr/bin/mintupdate-cli"), patch.object(
        checks, "run", return_value=CommandResult(0, "security pkg-a 1.2\nkernel pkg-b 2.0\n", "")
    ) as mocked_run:
        assert checks.count_system_updates() == 2
        mocked_run.assert_called_once_with(["/usr/bin/mintupdate-cli", "list"], timeout=30)


def test_apt_fallback_ignores_listing_header() -> None:
    def fake_which(name: str):
        if name == "mintupdate-cli":
            return None
        if name == "apt":
            return "/usr/bin/apt"
        return None

    with patch.object(checks.shutil, "which", side_effect=fake_which), patch.object(
        checks,
        "run",
        return_value=CommandResult(0, "Listing...\npkg-a/stable 1.2 amd64 [upgradable]\n\npkg-b/stable 2.0 amd64 [upgradable]\n", ""),
    ):
        assert checks.count_system_updates() == 2


def test_each_read_status_performs_a_fresh_update_check() -> None:
    values = iter([14, 0])
    with patch.object(checks, "count_system_updates", side_effect=lambda: next(values)), patch.object(
        checks, "run", return_value=CommandResult(0, "Archived and active journals take up 10M.", "")
    ), patch.object(checks.Path, "exists", return_value=False):
        assert checks.read_status().updates_available == 14
        assert checks.read_status().updates_available == 0


def test_refresh_uses_generation_guard_and_fresh_status() -> None:
    source = Path("drivemonitor/gui/window.py").read_text(encoding="utf-8")
    assert "self.refresh_generation += 1" in source
    assert "maintenance = read_status()" in source
    assert "generation != self.refresh_generation" in source
    assert "self._result_queue.put" in source
    assert "Daten und Systemupdates werden gelesen" in source
