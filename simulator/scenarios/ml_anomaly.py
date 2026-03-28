"""Scenario: ML anomaly — send abnormal-mode IP camera telemetry triggering ML detection."""
from __future__ import annotations

import json
import urllib.request


def run(ingest_url: str) -> None:
    device_id = "cam-ml-demo"

    print(f"  Sending abnormal IP camera telemetry from '{device_id}'...")
    payload = {
        "device_id": device_id,
        "device_type": "ip_camera",
        "timestamp": "2026-03-28T12:20:00Z",
        "fps": 1,
        "resolution": "360p",
        "stream_active": False,
        "bandwidth_kbps": 12500.0,
        "battery": 5,
        "firmware_version": "1.0.2",
        "mode": "abnormal",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ingest_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=5)

    print(f"  Check for 'ml_anomaly' alert on '{device_id}'.")
