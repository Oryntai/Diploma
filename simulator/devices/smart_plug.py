from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from random import Random


@dataclass(slots=True)
class SmartPlugDevice:
    device_id: str
    mode: str = "normal"
    seed: int = 0
    interval_seconds: float = 5.0
    firmware_version: str = "2.1.0"
    device_type: str = "smart_plug"
    _random: Random = field(init=False, repr=False)
    _emission_index: int = field(default=0, init=False, repr=False)
    _base_timestamp: datetime = field(
        default=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._random = Random(self.seed)

    def next_payload(self) -> dict[str, str | int | float | bool]:
        timestamp = self._base_timestamp + timedelta(
            seconds=self._emission_index * self.interval_seconds,
        )
        payload: dict[str, str | int | float | bool] = {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            "power_watts": self._power_reading(),
            "voltage": self._voltage_reading(),
            "is_on": self._is_on(),
            "battery": self._battery_level(),
            "firmware_version": self.firmware_version,
            "mode": self.mode,
        }
        self._emission_index += 1
        return payload

    def _power_reading(self) -> float:
        if self.mode == "abnormal":
            return round(self._random.uniform(500.0, 2000.0), 1)
        return round(self._random.uniform(5.0, 15.0), 1)

    def _voltage_reading(self) -> float:
        if self.mode == "abnormal":
            return round(self._random.uniform(180.0, 280.0), 1)
        return round(self._random.uniform(218.0, 242.0), 1)

    def _is_on(self) -> bool:
        if self.mode == "abnormal":
            return self._random.choice([True, False])
        return True

    def _battery_level(self) -> int:
        if self.mode == "abnormal":
            return self._random.randint(5, 20)
        return self._random.randint(80, 100)
