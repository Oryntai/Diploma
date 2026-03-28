"""Scenario: Message flood — send 25 messages in rapid succession from one device."""
from __future__ import annotations

import json
import time
import urllib.request


def run(ingest_url: str) -> None:
    device_id = "flood-sensor-demo"
    count = 25

    print(f"  Sending {count} rapid messages from '{device_id}'...")
    for i in range(count):
        payload = {
            "device_id": device_id,
            "device_type": "temperature_sensor",
            "timestamp": f"2026-03-28T12:00:{i:02d}Z",
            "temperature": 22.0 + (i % 5) * 0.1,
            "battery": 80,
            "firmware_version": "1.0.2",
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
        if i % 5 == 0:
            print(f"    sent {i+1}/{count}")
        time.sleep(0.05)

    print(f"  Flood complete: {count} messages sent. Check for 'message_flood' alert.")
