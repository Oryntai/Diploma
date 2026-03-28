"""Scenario: Impossible value — send temperature readings outside allowed range."""
from __future__ import annotations

import json
import urllib.request


def run(ingest_url: str) -> None:
    payloads = [
        {"temp": 22.5, "label": "normal baseline"},
        {"temp": 85.0, "label": "impossible high (85C)"},
        {"temp": -45.0, "label": "impossible low (-45C)"},
    ]

    for p in payloads:
        print(f"  Sending temperature {p['temp']}C ({p['label']})...")
        payload = {
            "device_id": "temp-impossible-demo",
            "device_type": "temperature_sensor",
            "timestamp": "2026-03-28T12:05:00Z",
            "temperature": p["temp"],
            "battery": 75,
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

    print("  Check for 'impossible_value' alerts on 'temp-impossible-demo'.")
