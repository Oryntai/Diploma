"""Scenario: Firmware mismatch — device reports changed firmware version."""
from __future__ import annotations

import json
import urllib.request


def _send(ingest_url: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ingest_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=5)


def run(ingest_url: str) -> None:
    device_id = "lock-firmware-demo"

    print(f"  Step 1: Register device '{device_id}' with firmware 1.0.2...")
    _send(ingest_url, {
        "device_id": device_id,
        "device_type": "smart_door_lock",
        "timestamp": "2026-03-28T12:15:00Z",
        "lock_state": "locked",
        "access_attempts": 0,
        "battery": 95,
        "firmware_version": "1.0.2",
        "mode": "normal",
    })

    print(f"  Step 2: Send telemetry with changed firmware 2.0.0-hacked...")
    _send(ingest_url, {
        "device_id": device_id,
        "device_type": "smart_door_lock",
        "timestamp": "2026-03-28T12:16:00Z",
        "lock_state": "unlocked",
        "access_attempts": 5,
        "battery": 94,
        "firmware_version": "2.0.0-hacked",
        "mode": "normal",
    })

    print(f"  Check for 'firmware_mismatch' alert on '{device_id}'.")
