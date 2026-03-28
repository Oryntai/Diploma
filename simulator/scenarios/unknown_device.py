"""Scenario: Unknown device — send telemetry from a never-seen-before device."""
from __future__ import annotations

import json
import urllib.request


def run(ingest_url: str) -> None:
    device_id = "rogue-device-xyz-999"
    print(f"  Sending telemetry from unknown device '{device_id}'...")

    payload = {
        "device_id": device_id,
        "device_type": "smart_plug",
        "timestamp": "2026-03-28T12:10:00Z",
        "power_watts": 120.5,
        "voltage": 230.0,
        "is_on": True,
        "battery": 90,
        "firmware_version": "0.9.9",
        "mode": "normal",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ingest_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=5)

    print(f"  Check for 'unknown_device' alert on '{device_id}'.")
