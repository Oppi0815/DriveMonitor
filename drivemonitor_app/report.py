from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any


def _value(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return escape(str(value))


def create_html_report(path: str | Path, drives: list[dict[str, Any]], hostname: str) -> Path:
    target = Path(path)
    rows: list[str] = []
    for drive in drives:
        details = "".join(
            f"<tr><td>{escape(label)}</td><td>{escape(value)}</td><td>{escape(state)}</td></tr>"
            for label, value, state in drive.get("smart_details", [])
        )
        usage = drive.get("usage") or {}
        partitions = []
        for part in usage.get("partitions", []):
            mounts = ", ".join(part.get("mountpoints", [])) or "—"
            partitions.append(
                f"<li>{escape(part.get('device', '—'))}: {escape(part.get('filesystem', '—'))} → {escape(mounts)}</li>"
            )
        rows.append(f"""
<section>
  <h2>{_value(drive.get('name'))}</h2>
  <p class="status {escape(drive.get('condition_state', 'neutral'))}">
    Gesamtzustand: {_value(drive.get('condition'))} · SMART: {_value(drive.get('health'))}
  </p>
  <table>
    <tr><th>Gerät</th><td>{_value(drive.get('device'))}</td><th>Typ</th><td>{_value(drive.get('icon'))}</td></tr>
    <tr><th>Kapazität</th><td>{_value(drive.get('size'))}</td><th>Schnittstelle</th><td>{_value(drive.get('transport'))}</td></tr>
    <tr><th>Temperatur</th><td>{_value(drive.get('temp'))} °C</td><th>Firmware</th><td>{_value(drive.get('firmware'))}</td></tr>
    <tr><th>Seriennummer</th><td>{_value(drive.get('serial'))}</td><th>Betriebsstunden</th><td>{_value(drive.get('hours'))}</td></tr>
    <tr><th>Einschaltungen</th><td>{_value(drive.get('cycles'))}</td><th>SSD-Lebensdauer</th><td>{_value(drive.get('life'))} %</td></tr>
  </table>
  <h3>Wichtige SMART-Werte</h3>
  <table><tr><th>Wert</th><th>Ergebnis</th><th>Bewertung</th></tr>{details}</table>
  <h3>Partitionen</h3><ul>{''.join(partitions) or '<li>Keine Partitionsdaten verfügbar</li>'}</ul>
</section>""")

    generated = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    document = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><title>DriveMonitor SMART-Bericht</title>
<style>
body{{font-family:Arial,sans-serif;max-width:1050px;margin:30px auto;color:#1f2937;background:#f3f6f8}}
h1{{margin-bottom:4px}} .meta{{color:#6b7280;margin-top:0}} section{{background:white;border:1px solid #dfe5ea;padding:18px;margin:18px 0}}
table{{border-collapse:collapse;width:100%;margin:8px 0 14px}} th,td{{border:1px solid #dfe5ea;padding:7px;text-align:left}} th{{background:#f8fafc}}
.status{{padding:9px;font-weight:bold}} .ok{{background:#ecfdf5;color:#15803d}} .warn{{background:#fff7ed;color:#c2410c}}
.critical{{background:#fef2f2;color:#b91c1c}} .neutral{{background:#f8fafc;color:#6b7280}}
footer{{color:#6b7280;font-size:12px;margin-top:24px}}
</style></head><body>
<h1>DriveMonitor 4.5 Professional</h1><p class="meta">SMART-Bericht für {escape(hostname)} · erstellt am {generated}</p>
{''.join(rows)}
<footer>Dieser Bericht ersetzt keine Datensicherung. Bei Warnungen sollten wichtige Daten umgehend gesichert werden.</footer>
</body></html>"""
    target.write_text(document, encoding="utf-8")
    return target
