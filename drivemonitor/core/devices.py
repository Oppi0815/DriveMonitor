from __future__ import annotations

import json
from typing import Any
from .command import run

def list_block_devices() -> list[dict[str, Any]]:
    result = run(["lsblk", "-J", "-b", "-d", "-o", "NAME,MODEL,SIZE,TRAN,TYPE,ROTA"], timeout=8)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    devices: list[dict[str, Any]] = []
    for item in payload.get("blockdevices", []):
        name = str(item.get("name") or "")
        if item.get("type") != "disk" or not (name.startswith("sd") or name.startswith("nvme")):
            continue
        devices.append({
            "device": f"/dev/{name}",
            "name": name,
            "model": str(item.get("model") or "").strip(),
            "size": int(item.get("size") or 0),
            "transport": str(item.get("tran") or "").strip().upper(),
            "rotational": bool(int(item.get("rota") or 0)),
        })
    return devices
