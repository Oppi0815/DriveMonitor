from __future__ import annotations

import subprocess
from dataclasses import dataclass

@dataclass(slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str

def run(command: list[str], timeout: int = 12) -> CommandResult:
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)
    except (OSError, subprocess.SubprocessError) as exc:
        return CommandResult(999, "", str(exc))
