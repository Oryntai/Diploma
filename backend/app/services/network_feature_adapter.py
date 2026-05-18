from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from .traffic_features import TrafficFeatureGenerator


@dataclass(frozen=True, slots=True)
class NetworkFeatureContext:
    features: dict[str, float]
    mode: str
    attack_style: str | None
    reasons: list[str]


class NetworkFeatureAdapter:
    """Bridge simple simulator samples into the CICIoT2023 feature space."""

    def __init__(self, generator: TrafficFeatureGenerator | None = None) -> None:
        self._generator = generator or TrafficFeatureGenerator(seed=42)
        self._lock = threading.Lock()

    def adapt(self, sample: Any, device_type: str) -> NetworkFeatureContext:
        attack_style, reasons = self._classify_sample(sample)
        mode = "abnormal" if attack_style is not None else "normal"

        with self._lock:
            features = self._generator.generate(
                device_type=device_type,
                mode=mode,
                attack_type=attack_style,
            )

        return NetworkFeatureContext(
            features=features,
            mode=mode,
            attack_style=attack_style,
            reasons=reasons,
        )

    @staticmethod
    def _classify_sample(sample: Any) -> tuple[str | None, list[str]]:
        reasons: list[str] = []
        high_packets = float(sample.packets_per_second) > 10.0
        high_connections = int(sample.connection_count) > 20
        high_bandwidth = float(sample.bytes_per_second) > 5_000.0
        high_latency = float(sample.latency_ms) > 200.0
        high_loss = float(sample.packet_loss_percent) > 5.0
        low_bandwidth = float(sample.bytes_per_second) < 100.0
        low_packets = float(sample.packets_per_second) < 0.05
        low_connections = int(sample.connection_count) == 0
        low_latency = float(sample.latency_ms) < 1.0

        if high_packets and high_connections:
            reasons.append(
                "flood-like traffic: high packet rate and connection count"
            )
            attack_style = "DDoS"
        elif low_bandwidth:
            reasons.append("low-value anomaly: only bytes per second is abnormally low")
            attack_style = "arp_spoofing"
        elif low_packets:
            reasons.append("low-value anomaly: only packets per second is abnormally low")
            attack_style = "arp_spoofing"
        elif low_connections:
            reasons.append("low-value anomaly: only connection count is abnormally low")
            attack_style = "arp_spoofing"
        elif low_latency:
            reasons.append("low-value anomaly: only latency is abnormally low")
            attack_style = "arp_spoofing"
        elif high_packets:
            reasons.append("packet-rate anomaly: only packets per second is elevated")
            attack_style = "syn_flood"
        elif high_connections:
            reasons.append("connection-count anomaly: only connection count is elevated")
            attack_style = "port_scan"
        elif high_bandwidth:
            reasons.append("traffic volume anomaly: only bytes per second is elevated")
            attack_style = "dns_tunnel"
        elif high_latency:
            reasons.append("latency anomaly: only latency is elevated")
            attack_style = "DDoS"
        elif high_loss:
            reasons.append("packet-loss anomaly: only packet loss is elevated")
            attack_style = "DDoS"
        else:
            attack_style = None

        if high_bandwidth:
            reasons.append(f"bytes_per_second={float(sample.bytes_per_second):.1f}")
        if high_packets:
            reasons.append(f"packets_per_second={float(sample.packets_per_second):.1f}")
        if high_connections:
            reasons.append(f"connection_count={int(sample.connection_count)}")
        if high_latency:
            reasons.append(f"latency_ms={float(sample.latency_ms):.1f}")
        if high_loss:
            reasons.append(f"packet_loss_percent={float(sample.packet_loss_percent):.1f}")
        if low_bandwidth:
            reasons.append(f"bytes_per_second={float(sample.bytes_per_second):.1f}")
        if low_packets:
            reasons.append(f"packets_per_second={float(sample.packets_per_second):.3f}")
        if low_connections:
            reasons.append(f"connection_count={int(sample.connection_count)}")
        if low_latency:
            reasons.append(f"latency_ms={float(sample.latency_ms):.1f}")

        return attack_style, reasons
