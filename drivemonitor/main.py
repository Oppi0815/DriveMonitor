from __future__ import annotations

import os
from .gui.window import run_app

def main() -> None:
    if os.geteuid() == 0:
        raise SystemExit("DriveMonitor darf nicht als root gestartet werden.")
    run_app()

if __name__ == "__main__":
    main()
