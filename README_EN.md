# DriveMonitor Professional 5.0.0

DriveMonitor Professional is a modular health monitor for drives and hardware on Linux Mint. It presents SMART data and temperatures in an understandable way, highlights changes and events, and runs entirely as a regular user.

## Highlights

- HDD, SSD, NVMe and supported USB drives
- secure SMART access without password prompts during normal use
- clear computer health summary with practical recommendations
- important SMART attributes and trend analysis
- event center for multiple simultaneous messages
- temperature history for drives and system sensors
- capture of short temperature peaks between history points
- Linux Mint system update and reboot status
- scrollable interface for small and large windows
- diagnostic and debug report
- one-time welcome dialog
- About dialog with system, version and license information

## Installation

```bash
chmod +x install.sh smart-berechtigung-einrichten.sh uninstall.sh
./install.sh
```

Only during the first installation, or if SMART data cannot be read:

```bash
./smart-berechtigung-einrichten.sh
```

This script requires administrator privileges once. DriveMonitor itself continues to run as a regular user.

## Start

DriveMonitor appears in the Linux Mint application menu as **DriveMonitor Professional**. Alternatively:

```bash
drivemonitor
```

## Local data

History and preferences are stored locally only:

```text
~/.local/share/drivemonitor/history.db
~/.local/share/drivemonitor/preferences.json
```

DriveMonitor does not transmit personal data. The system update check only uses local Linux Mint or APT tools.

## Requirements

- Linux Mint 22.x or a compatible Ubuntu system
- Python 3 with Tkinter
- `smartmontools`
- `lm-sensors`
- `lsblk`

## Uninstallation

```bash
./uninstall.sh
```

The optional system-wide SMART permission helper can then be removed by an administrator as described by the uninstall script.

## Usage

- **Aktualisieren** refreshes drives, SMART data, temperatures, sensors and system updates.
- **Über** shows the version, operating system, kernel, Python version, license and GitHub link.
- The message strip opens the event center.
- The debug report supports diagnostics and support requests.
- Temperature charts become more informative with each measurement.

## Security

- The graphical application never runs as root.
- The SMART helper only permits read-only `smartctl -a -j` calls for approved device paths.
- All history data remains local.

## License

GNU General Public License v3. See `LICENSE`.

## Project

GitHub: `https://github.com/Oppi0815/DriveMonitor`

Developed for Linux Mint.
