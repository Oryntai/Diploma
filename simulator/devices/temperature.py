from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from random import Random


@dataclass(slots=True)
class TemperatureSensor:
    device_id: str
    mode: str = "normal"
    seed: int = 0
    interval_seconds: float = 5.0
    firmware_version: str = "1.0.2"
    device_type: str = "temperature_sensor"
    _random: Random = field(init=False, repr=False)
    _emission_index: int = field(default=0, init=False, repr=False)
    _base_timestamp: datetime = field(
        default=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._random = Random(self.seed)

    def next_payload(self) -> dict[str, str | int | float]:
        timestamp = self._base_timestamp + timedelta(
            seconds=self._emission_index * self.interval_seconds,
        )
        payload = {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            "temperature": self._temperature_reading(),
            "battery": self._battery_level(),
            "firmware_version": self.firmware_version,
            "mode": self.mode,
        }
        self._emission_index += 1
        return payload

    def _temperature_reading(self) -> float:
        if self.mode == "abnormal":
            return round(70.0 + self._random.uniform(0.0, 10.0), 1)
        return round(24.0 + self._random.uniform(-1.0, 1.0), 1)

    def _battery_level(self) -> int:
        if self.mode == "abnormal":
            return self._random.randint(10, 25)
        return self._random.randint(85, 100)
