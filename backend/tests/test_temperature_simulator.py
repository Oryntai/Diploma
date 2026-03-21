from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_temperature_sensor_class():
    module_path = (
        Path(__file__).resolve().parents[2] / "simulator" / "devices" / "temperature.py"
    )
    spec = importlib.util.spec_from_file_location("temperature_device", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.TemperatureSensor


def test_temperature_sensor_seed_repeats_first_payload() -> None:
    temperature_sensor = load_temperature_sensor_class()
    first_sensor = temperature_sensor(device_id="temp-001", seed=42)
    second_sensor = temperature_sensor(device_id="temp-001", seed=42)

    first_payload = first_sensor.next_payload()
    second_payload = second_sensor.next_payload()

    assert first_payload == second_payload
    assert first_payload == {
        "device_id": "temp-001",
        "device_type": "temperature_sensor",
        "timestamp": "2026-03-20T10:00:00Z",
        "temperature": 24.3,
        "battery": 85,
        "firmware_version": "1.0.2",
        "mode": "normal",
    }
