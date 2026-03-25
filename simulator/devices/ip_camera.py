from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from random import Random


@dataclass(slots=True)
class IPCameraDevice:
    device_id: str
    mode: str = "normal"
    seed: int = 0
    interval_seconds: float = 5.0
    firmware_version: str = "3.4.1"
    device_type: str = "ip_camera"
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
            "fps": self._fps(),
            "resolution": self._resolution(),
            "stream_active": self._stream_active(),
            "bandwidth_kbps": self._bandwidth(),
            "battery": self._battery_level(),
            "firmware_version": self.firmware_version,
            "mode": self.mode,
        }
        self._emission_index += 1
        return payload

    def _fps(self) -> int:
        if self.mode == "abnormal":
            return self._random.randint(1, 8)
        return self._random.randint(24, 30)

    def _resolution(self) -> str:
        if self.mode == "abnormal":
            return self._random.choice(["240p", "360p", "480p"])
        return "1080p"

    def _stream_active(self) -> bool:
        if self.mode == "abnormal":
            return self._random.choice([True, False])
        return True

    def _bandwidth(self) -> float:
        if self.mode == "abnormal":
            return round(self._random.uniform(8000.0, 15000.0), 1)
        return round(self._random.uniform(1500.0, 3000.0), 1)

    def _battery_level(self) -> int:
        if self.mode == "abnormal":
            return self._random.randint(5, 20)
        return self._random.randint(70, 100)
