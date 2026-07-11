#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

python3 -m compileall -q "$ROOT/drivemonitor.py" "$ROOT/drivemonitor_app"
for file in "$ROOT"/*.sh; do
    bash -n "$file"
done
python3 -m py_compile "$ROOT/helpers/drivemonitor-smartctl"

PYTHONPATH="$ROOT" python3 - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from drivemonitor_app import config
from drivemonitor_app.report import create_html_report
from drivemonitor_app.settings import load_settings
from drivemonitor_app.smart import extract_smart_details

assert config.APP_VERSION == "4.5.1 Professional"
assert isinstance(load_settings(), dict)
assert extract_smart_details({})

with TemporaryDirectory() as tmp:
    target = Path(tmp) / "report.html"
    create_html_report(target, [], "testsystem")
    assert target.is_file() and target.stat().st_size > 0
PY

find "$ROOT" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$ROOT" -type f -name '*.pyc' -delete

echo "Prüfung erfolgreich: Syntax, Modulimporte, Einstellungen und Berichtserzeugung sind fehlerfrei."
