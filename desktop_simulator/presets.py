from __future__ import annotations

import random
from datetime import UTC, datetime
from typing import Any

REGISTERED_DEVICES: dict[str, str] = {
    "dev-001": "Room Temperature Sensor",
    "dev-002": "Smart Plug",
    "dev-003": "IP Security Camera",
    "dev-004": "Smart Door Lock",
    "dev-005": "Robot Vacuum",
}

DEVICE_TYPES: dict[str, str] = {
    "temperature_sensor": "dev-001",
    "smart_plug": "dev-002",
    "ip_camera": "dev-003",
    "smart_door_lock": "dev-004",
    "robot_vacuum": "dev-005",
}

PRESETS: dict[str, dict[str, float | int | str]] = {
    "normal": {
        "protocol": "HTTP",
        "bytes_per_second": 512.0,
        "packets_per_second": 0.2,
        "connection_count": 1,
        "latency_ms": 12.0,
        "packet_loss_percent": 0.0,
    },
    "flood": {
        "protocol": "HTTP",
        "bytes_per_second": 25_000.0,
        "packets_per_second": 120.0,
        "connection_count": 80,
        "latency_ms": 450.0,
        "packet_loss_percent": 18.0,
    },
    "bandwidth_spike": {
        "protocol": "HTTP",
        "bytes_per_second": 25_000.0,
        "packets_per_second": 0.2,
        "connection_count": 1,
        "latency_ms": 12.0,
        "packet_loss_percent": 0.0,
    },
    "packet_rate_spike": {
        "protocol": "HTTP",
        "bytes_per_second": 512.0,
        "packets_per_second": 120.0,
        "connection_count": 1,
        "latency_ms": 12.0,
        "packet_loss_percent": 0.0,
    },
    "connection_fanout": {
        "protocol": "HTTP",
        "bytes_per_second": 512.0,
        "packets_per_second": 0.2,
        "connection_count": 80,
        "latency_ms": 12.0,
        "packet_loss_percent": 0.0,
    },
    "latency_spike": {
        "protocol": "HTTP",
        "bytes_per_second": 512.0,
        "packets_per_second": 0.2,
        "connection_count": 1,
        "latency_ms": 900.0,
        "packet_loss_percent": 0.0,
    },
    "packet_loss": {
        "protocol": "HTTP",
        "bytes_per_second": 512.0,
        "packets_per_second": 0.2,
        "connection_count": 1,
        "latency_ms": 12.0,
        "packet_loss_percent": 22.0,
    },
    "low_value": {
        "protocol": "HTTP",
        "bytes_per_second": 0.0,
        "packets_per_second": 0.2,
        "connection_count": 1,
        "latency_ms": 12.0,
        "packet_loss_percent": 0.0,
    },
}

PROTOCOLS: tuple[str, ...] = ("HTTP", "HTTPS", "MQTT", "TCP", "UDP", "DNS")

DEVICE_NORMAL_PROFILES: dict[str, dict[str, Any]] = {
    "temperature_sensor": {
        "protocols": ("MQTT", "HTTP"),
        "bytes_per_second": (120.0, 900.0),
        "packets_per_second": (0.08, 0.8),
        "connection_count": (1, 2),
        "latency_ms": (10.0, 80.0),
        "packet_loss_percent": (0.0, 0.8),
    },
    "smart_plug": {
        "protocols": ("MQTT", "HTTPS", "HTTP"),
        "bytes_per_second": (180.0, 1_200.0),
        "packets_per_second": (0.1, 1.4),
        "connection_count": (1, 3),
        "latency_ms": (8.0, 90.0),
        "packet_loss_percent": (0.0, 1.0),
    },
    "ip_camera": {
        "protocols": ("HTTP", "HTTPS", "TCP"),
        "bytes_per_second": (1_200.0, 4_800.0),
        "packets_per_second": (1.2, 8.5),
        "connection_count": (2, 8),
        "latency_ms": (12.0, 95.0),
        "packet_loss_percent": (0.0, 1.2),
    },
    "smart_door_lock": {
        "protocols": ("MQTT", "HTTPS"),
        "bytes_per_second": (120.0, 700.0),
        "packets_per_second": (0.06, 0.55),
        "connection_count": (1, 2),
        "latency_ms": (18.0, 120.0),
        "packet_loss_percent": (0.0, 1.0),
    },
    "robot_vacuum": {
        "protocols": ("MQTT", "HTTP", "HTTPS"),
        "bytes_per_second": (260.0, 2_200.0),
        "packets_per_second": (0.2, 3.2),
        "connection_count": (1, 5),
        "latency_ms": (14.0, 110.0),
        "packet_loss_percent": (0.0, 1.3),
    },
}

DEVICE_INCIDENT_PROFILES: dict[str, tuple[str, ...]] = {
    "temperature_sensor": (
        "packet_rate_spike",
        "latency_spike",
        "packet_loss",
        "low_value",
    ),
    "smart_plug": (
        "packet_rate_spike",
        "connection_fanout",
        "bandwidth_spike",
        "latency_spike",
    ),
    "ip_camera": (
        "bandwidth_spike",
        "packet_loss",
        "latency_spike",
        "flood",
    ),
    "smart_door_lock": (
        "connection_fanout",
        "packet_rate_spike",
        "latency_spike",
        "packet_loss",
    ),
    "robot_vacuum": (
        "packet_loss",
        "latency_spike",
        "bandwidth_spike",
        "flood",
    ),
}

INCIDENT_WEIGHTS: dict[str, int] = {
    "bandwidth_spike": 16,
    "packet_rate_spike": 18,
    "connection_fanout": 14,
    "latency_spike": 22,
    "packet_loss": 18,
    "low_value": 8,
    "flood": 4,
}


def build_network_sample(
    device_id: str,
    preset_name: str,
    *,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    if device_id not in REGISTERED_DEVICES:
        raise ValueError(f"Unknown registered demo device: {device_id}")
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown simulator preset: {preset_name}")

    payload = dict(PRESETS[preset_name])
    payload.update(
        {
            "timestamp": (timestamp or datetime.now(UTC)).isoformat(),
            "device_id": device_id,
        }
    )
    return payload


def build_network_sample_for_type(
    device_type: str,
    preset_name: str,
    *,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    if device_type not in DEVICE_TYPES:
        raise ValueError(f"Unknown registered demo device type: {device_type}")

    payload = build_network_sample(
        DEVICE_TYPES[device_type],
        preset_name,
        timestamp=timestamp,
    )
    payload["device_type"] = device_type
    return payload


def build_custom_network_sample_for_type(
    device_type: str,
    values: dict[str, Any],
    *,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    if device_type not in DEVICE_TYPES:
        raise ValueError(f"Unknown registered demo device type: {device_type}")

    protocol = str(values.get("protocol", "HTTP")).strip().upper()
    if not protocol:
        raise ValueError("Protocol is required.")

    bytes_per_second = _coerce_float(values, "bytes_per_second")
    packets_per_second = _coerce_float(values, "packets_per_second")
    connection_count = _coerce_int(values, "connection_count")
    latency_ms = _coerce_float(values, "latency_ms")
    packet_loss_percent = _coerce_float(values, "packet_loss_percent")

    if packet_loss_percent > 100.0:
        raise ValueError("packet_loss_percent must be <= 100.")

    return {
        "timestamp": (timestamp or datetime.now(UTC)).isoformat(),
        "device_id": DEVICE_TYPES[device_type],
        "device_type": device_type,
        "protocol": protocol,
        "bytes_per_second": bytes_per_second,
        "packets_per_second": packets_per_second,
        "connection_count": connection_count,
        "latency_ms": latency_ms,
        "packet_loss_percent": packet_loss_percent,
    }


def build_random_network_sample_for_type(
    device_type: str,
    *,
    rng: random.Random | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    randomizer = rng or random.Random()
    if randomizer.random() < 0.88:
        return build_normal_operation_sample_for_type(
            device_type,
            rng=randomizer,
            timestamp=timestamp,
        )
    return build_incident_network_sample_for_type(
        device_type,
        _choose_incident_profile(device_type, randomizer),
        rng=randomizer,
        timestamp=timestamp,
    )


def build_normal_operation_sample_for_type(
    device_type: str,
    *,
    rng: random.Random | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    randomizer = rng or random.Random()
    profile = _normal_profile_for(device_type)
    values = {
        "protocol": randomizer.choice(profile["protocols"]),
        "bytes_per_second": _rounded_uniform(randomizer, profile["bytes_per_second"]),
        "packets_per_second": _rounded_uniform(randomizer, profile["packets_per_second"], 3),
        "connection_count": randomizer.randint(*profile["connection_count"]),
        "latency_ms": _rounded_uniform(randomizer, profile["latency_ms"]),
        "packet_loss_percent": _rounded_uniform(randomizer, profile["packet_loss_percent"]),
    }
    payload = build_custom_network_sample_for_type(
        device_type,
        values,
        timestamp=timestamp,
    )
    payload["random_profile"] = "normal_operation"
    payload["stream_state"] = "normal"
    return payload


def build_incident_network_sample_for_type(
    device_type: str,
    incident_profile: str,
    *,
    rng: random.Random | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    randomizer = rng or random.Random()
    normal = build_normal_operation_sample_for_type(
        device_type,
        rng=randomizer,
        timestamp=timestamp,
    )
    values: dict[str, Any] = {
        "protocol": normal["protocol"],
        "bytes_per_second": normal["bytes_per_second"],
        "packets_per_second": normal["packets_per_second"],
        "connection_count": normal["connection_count"],
        "latency_ms": normal["latency_ms"],
        "packet_loss_percent": normal["packet_loss_percent"],
    }

    if incident_profile == "bandwidth_spike":
        values["protocol"] = randomizer.choice(("HTTP", "HTTPS", "DNS"))
        values["bytes_per_second"] = round(randomizer.uniform(5_800.0, 18_000.0), 2)
    elif incident_profile == "packet_rate_spike":
        values["protocol"] = randomizer.choice(("TCP", "UDP", "MQTT"))
        values["packets_per_second"] = round(randomizer.uniform(11.0, 95.0), 3)
    elif incident_profile == "connection_fanout":
        values["protocol"] = randomizer.choice(("TCP", "HTTP", "HTTPS"))
        values["connection_count"] = randomizer.randint(21, 70)
    elif incident_profile == "latency_spike":
        values["latency_ms"] = round(randomizer.uniform(210.0, 850.0), 2)
    elif incident_profile == "packet_loss":
        values["packet_loss_percent"] = round(randomizer.uniform(5.5, 30.0), 2)
    elif incident_profile == "low_value":
        values["bytes_per_second"] = round(randomizer.uniform(0.0, 90.0), 2)
    elif incident_profile == "flood":
        values.update(
            {
                "protocol": randomizer.choice(("HTTP", "TCP", "UDP")),
                "bytes_per_second": round(randomizer.uniform(15_000.0, 45_000.0), 2),
                "packets_per_second": round(randomizer.uniform(40.0, 180.0), 3),
                "connection_count": randomizer.randint(35, 120),
                "latency_ms": round(randomizer.uniform(250.0, 950.0), 2),
                "packet_loss_percent": round(randomizer.uniform(8.0, 35.0), 2),
            }
        )
    else:
        raise ValueError(f"Unknown incident profile: {incident_profile}")

    payload = build_custom_network_sample_for_type(
        device_type,
        values,
        timestamp=timestamp,
    )
    payload["random_profile"] = incident_profile
    payload["stream_state"] = "incident"
    return payload


class DeviceTrafficStream:
    def __init__(
        self,
        device_type: str,
        *,
        rng: random.Random | None = None,
        incident_delay_range: tuple[int, int] = (8, 16),
        incident_duration_range: tuple[int, int] = (1, 3),
    ) -> None:
        if device_type not in DEVICE_TYPES:
            raise ValueError(f"Unknown registered demo device type: {device_type}")
        self.device_type = device_type
        self._rng = rng or random.Random()
        self._incident_delay_range = incident_delay_range
        self._incident_duration_range = incident_duration_range
        self.sequence_number = 0
        self._samples_until_incident = self._rng.randint(*incident_delay_range)
        self._incident_remaining = 0
        self._current_incident: str | None = None

    def next_sample(self) -> dict[str, Any]:
        self.sequence_number += 1

        if self._incident_remaining > 0:
            payload = self._incident_sample()
        elif self._samples_until_incident > 0:
            self._samples_until_incident -= 1
            payload = build_normal_operation_sample_for_type(
                self.device_type,
                rng=self._rng,
            )
        else:
            self._current_incident = _choose_incident_profile(self.device_type, self._rng)
            self._incident_remaining = self._rng.randint(*self._incident_duration_range)
            payload = self._incident_sample()

        payload["stream_sample"] = self.sequence_number
        if payload["stream_state"] == "normal":
            payload["samples_until_next_incident"] = self._samples_until_incident
        return payload

    def _incident_sample(self) -> dict[str, Any]:
        if self._current_incident is None:
            self._current_incident = _choose_incident_profile(self.device_type, self._rng)
        payload = build_incident_network_sample_for_type(
            self.device_type,
            self._current_incident,
            rng=self._rng,
        )
        self._incident_remaining -= 1
        payload["incident_remaining"] = self._incident_remaining
        if self._incident_remaining <= 0:
            self._current_incident = None
            self._samples_until_incident = self._rng.randint(*self._incident_delay_range)
        return payload


def _normal_profile_for(device_type: str) -> dict[str, Any]:
    try:
        return DEVICE_NORMAL_PROFILES[device_type]
    except KeyError as exc:
        raise ValueError(f"Unknown registered demo device type: {device_type}") from exc


def _choose_incident_profile(device_type: str, rng: random.Random) -> str:
    try:
        profiles = DEVICE_INCIDENT_PROFILES[device_type]
    except KeyError as exc:
        raise ValueError(f"Unknown registered demo device type: {device_type}") from exc
    return rng.choices(
        profiles,
        weights=[INCIDENT_WEIGHTS[name] for name in profiles],
        k=1,
    )[0]


def _rounded_uniform(
    rng: random.Random,
    value_range: tuple[float, float],
    digits: int = 2,
) -> float:
    return round(rng.uniform(*value_range), digits)


def _coerce_float(values: dict[str, Any], field: str) -> float:
    try:
        value = float(values[field])
    except KeyError as exc:
        raise ValueError(f"{field} is required.") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric.") from exc
    if value < 0.0:
        raise ValueError(f"{field} must be >= 0.")
    return value


def _coerce_int(values: dict[str, Any], field: str) -> int:
    try:
        value = int(float(values[field]))
    except KeyError as exc:
        raise ValueError(f"{field} is required.") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer.") from exc
    if value < 0:
        raise ValueError(f"{field} must be >= 0.")
    return value
