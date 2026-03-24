from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_model_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (_backend_dir() / path).resolve()


@dataclass(frozen=True, slots=True)
class Settings:
    ml_model_path: Path
    flood_window_seconds: int
    flood_threshold: int
    min_temperature_c: float
    max_temperature_c: float
    low_battery_threshold: int


settings = Settings(
    ml_model_path=_resolve_model_path(
        os.getenv("ML_MODEL_PATH", "models/security_model.joblib"),
    ),
    flood_window_seconds=_env_int("RULE_FLOOD_WINDOW_SECONDS", 60),
    flood_threshold=_env_int("RULE_FLOOD_THRESHOLD", 20),
    min_temperature_c=_env_float("RULE_MIN_TEMPERATURE_C", -20.0),
    max_temperature_c=_env_float("RULE_MAX_TEMPERATURE_C", 60.0),
    low_battery_threshold=_env_int("RULE_LOW_BATTERY_THRESHOLD", 20),
)
