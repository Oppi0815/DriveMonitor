#!/usr/bin/env bash
set -euo pipefail
USER_NAME="${SUDO_USER:-$USER}"
echo "Die sichere SMART-Freigabe wird für Benutzer '$USER_NAME' eingerichtet."
echo "Dafür ist einmalig das Administratorpasswort nötig."
sudo install -d -m 755 /usr/local/libexec
TMP_HELPER="$(mktemp)"
cat > "$TMP_HELPER" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
# Erlaubt ausschließlich lesende Komplettabfragen als JSON.
if [ "$#" -lt 3 ]; then
    echo "Ungültiger Aufruf" >&2
    exit 2
fi
if [ "$1" != "-a" ] || [ "$2" != "-j" ]; then
    echo "Nur smartctl -a -j ist erlaubt" >&2
    exit 2
fi
shift 2
ARGS=(-a -j)
if [ "${1:-}" = "-d" ]; then
    case "${2:-}" in
        sat|sat,12|sat,16|scsi|usbjmicron|sntjmicron|sntrealtek) ;;
        *) echo "Nicht erlaubter Gerätetyp" >&2; exit 2 ;;
    esac
    ARGS+=("-d" "$2")
    shift 2
fi
DEVICE="${1:-}"
case "$DEVICE" in
    /dev/sd[a-z]|/dev/sd[a-z][a-z]|/dev/nvme[0-9]n[0-9]) ;;
    *) echo "Nicht erlaubtes Gerät" >&2; exit 2 ;;
esac
[ "$#" -eq 1 ] || { echo "Zu viele Argumente" >&2; exit 2; }
exec /usr/sbin/smartctl "${ARGS[@]}" "$DEVICE"
EOF
sudo install -o root -g root -m 755 "$TMP_HELPER" /usr/local/libexec/drivemonitor-smartctl
rm -f "$TMP_HELPER"
TMP_SUDOERS="$(mktemp)"
printf '%s ALL=(root) NOPASSWD: /usr/local/libexec/drivemonitor-smartctl *
' "$USER_NAME" > "$TMP_SUDOERS"
sudo visudo -cf "$TMP_SUDOERS"
sudo install -o root -g root -m 440 "$TMP_SUDOERS" /etc/sudoers.d/drivemonitor-smartctl
rm -f "$TMP_SUDOERS"
echo "SMART-Freigabe eingerichtet. DriveMonitor selbst läuft weiterhin als normaler Benutzer."
