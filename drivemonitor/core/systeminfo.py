from __future__ import annotations

import os
import platform
import socket
from .models import SystemInfo

def load_system_info() -> SystemInfo:
    try:
        pretty = platform.freedesktop_os_release().get("PRETTY_NAME", platform.system())
    except OSError:
        pretty = platform.system()
    return SystemInfo(socket.gethostname(), pretty, platform.release(), os.environ.get("XDG_CURRENT_DESKTOP", "—"))
