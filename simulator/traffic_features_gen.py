"""Thin wrapper around TrafficFeatureGenerator for the GUI app."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow importing from backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.traffic_features import TrafficFeatureGenerator

_gen = TrafficFeatureGenerator(seed=42)


def generate_attack_features(attack_type: str) -> dict[str, float]:
    return _gen.generate(device_type="ip_camera", mode="abnormal", attack_type=attack_type)
