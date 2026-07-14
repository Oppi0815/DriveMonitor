from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from drivemonitor.core.command import run


@dataclass(slots=True)
class MaintenanceStatus:
    updates_available: int | None
    reboot_required: bool
    journal_size: str


def _count_mint_updates() -> int | None:
    """Return the update count reported by Linux Mint's Update Manager.

    ``mintupdate-cli list`` uses the same APT update selection logic as the
    graphical Linux Mint Update Manager.  Calling it for every DriveMonitor
    refresh also reloads the package state after updates were installed while
    DriveMonitor was running.
    """

    executable = shutil.which("mintupdate-cli")
    if not executable:
        return None

    result = run([executable, "list"], timeout=30)
    if result.returncode != 0:
        return None

    return sum(1 for line in result.stdout.splitlines() if line.strip())


def _count_apt_updates() -> int | None:
    """Portable fallback for Ubuntu-compatible systems without mintupdate."""

    executable = shutil.which("apt") or "/usr/bin/apt"
    result = run([executable, "list", "--upgradable"], timeout=20)
    if result.returncode != 0:
        return None

    lines = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith("listing"):
            continue
        lines.append(line)
    return len(lines)


def count_system_updates() -> int | None:
    """Read the current system-update count without using a stored value."""

    mint_count = _count_mint_updates()
    if mint_count is not None:
        return mint_count
    return _count_apt_updates()


def read_status() -> MaintenanceStatus:
    """Collect a fresh maintenance status for every dashboard refresh."""

    updates = count_system_updates()
    journal = run(["journalctl", "--disk-usage"], timeout=8)
    return MaintenanceStatus(
        updates_available=updates,
        reboot_required=Path("/var/run/reboot-required").exists(),
        journal_size=journal.stdout.strip() or "Nicht verfügbar",
    )
