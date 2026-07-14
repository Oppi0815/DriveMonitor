from __future__ import annotations

APP_NAME = "DriveMonitor"
APP_VERSION = "5.0.0"
REFRESH_MS = 15_000
SMART_HELPER = "/usr/local/libexec/drivemonitor-smartctl"
TEMP_WARNING = 50.0
TEMP_CRITICAL = 60.0

MODEL_ALIASES = {
    "ST12000NM0127": "Seagate Exos 12 TB",
    "ST4000DM000-1F2168": "Seagate Desktop HDD 4 TB",
    "WDC WDS500G2B0A": "WD Blue SSD 500 GB",
    "WD_BLACK SN850X 8000GB": "WD Black SN850X 8 TB",
    "WD_BLACK SN850X 2000GB": "WD Black SN850X 2 TB",
}
