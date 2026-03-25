from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from random import Random


@dataclass(slots=True)
class SmartDoorLockDevice:
    device_id: str
    mode: str = "normal"
    seed: int = 0
    interval_seconds: float = 5.0
    firmware_version: str = "1.2.5"
    device_type: str = "smart_door_lock"
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
            "lock_state": self._lock_state(),
            "access_attempts": self._access_attempts(),
            "battery": self._battery_level(),
            "firmware_version": self.firmware_version,
            "mode": self.mode,
        }
        self._emission_index += 1
        return payload

    def _lock_state(self) -> str:
        if self.mode == "abnormal":
            return self._random.choice(["locked", "unlocked", "unlocked", "unlocked"])
        return self._random.choice(["locked", "locked", "locked", "unlocked"])

    def _access_attempts(self) -> int:
        if self.mode == "abnormal":
            return self._random.randint(10, 50)
        return self._random.randint(0, 2)

    def _battery_level(self) -> int:
        if self.mode == "abnormal":
            return self._random.randint(3, 15)
        return self._random.randint(70, 100)
