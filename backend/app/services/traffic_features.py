from __future__ import annotations

import random

FEATURE_NAMES: list[str] = [
    "flow_duration", "Header_Length", "Protocol Type", "Duration", "Rate",
    "Srate", "Drate", "fin_flag_number", "syn_flag_number", "rst_flag_number",
    "psh_flag_number", "ack_flag_number", "ece_flag_number", "cwr_flag_number",
    "ack_count", "syn_count", "fin_count", "urg_count", "rst_count",
    "HTTP", "HTTPS", "DNS", "Telnet", "SMTP", "SSH", "IRC",
    "TCP", "UDP", "DHCP", "ARP", "ICMP", "IPv", "LLC",
    "Tot sum", "Min", "Max", "AVG", "Std",
    "Tot size", "IAT", "Number", "Magnitue", "Radius",
    "Covariance", "Variance", "Weight",
]

_PROTOCOL_FEATURES = {
    "HTTP", "HTTPS", "DNS", "Telnet", "SMTP", "SSH", "IRC",
    "TCP", "UDP", "DHCP", "ARP", "ICMP", "IPv", "LLC",
}

DEVICE_PROFILES: dict[str, dict[str, float]] = {
    "temperature_sensor": {
        "flow_duration": 50.0, "Header_Length": 40.0, "Protocol Type": 6.0,
        "Duration": 0.05, "Rate": 2.0, "Srate": 1.0, "Drate": 1.0,
        "fin_flag_number": 1.0, "syn_flag_number": 1.0, "rst_flag_number": 0.0,
        "psh_flag_number": 1.0, "ack_flag_number": 2.0, "ece_flag_number": 0.0,
        "cwr_flag_number": 0.0, "ack_count": 4.0, "syn_count": 1.0,
        "fin_count": 1.0, "urg_count": 0.0, "rst_count": 0.0,
        "HTTP": 0.0, "HTTPS": 0.0, "DNS": 0.0, "Telnet": 0.0,
        "SMTP": 0.0, "SSH": 0.0, "IRC": 0.0,
        "TCP": 1.0, "UDP": 0.0, "DHCP": 0.0, "ARP": 0.0,
        "ICMP": 0.0, "IPv": 1.0, "LLC": 0.0,
        "Tot sum": 320.0, "Min": 40.0, "Max": 120.0, "AVG": 64.0, "Std": 20.0,
        "Tot size": 320.0, "IAT": 25.0, "Number": 5.0, "Magnitue": 143.0,
        "Radius": 28.0, "Covariance": 400.0, "Variance": 400.0, "Weight": 5.0,
    },
    "smart_plug": {
        "flow_duration": 30.0, "Header_Length": 40.0, "Protocol Type": 6.0,
        "Duration": 0.03, "Rate": 3.0, "Srate": 1.5, "Drate": 1.5,
        "fin_flag_number": 1.0, "syn_flag_number": 1.0, "rst_flag_number": 0.0,
        "psh_flag_number": 1.0, "ack_flag_number": 3.0, "ece_flag_number": 0.0,
        "cwr_flag_number": 0.0, "ack_count": 5.0, "syn_count": 1.0,
        "fin_count": 1.0, "urg_count": 0.0, "rst_count": 0.0,
        "HTTP": 0.0, "HTTPS": 1.0, "DNS": 0.0, "Telnet": 0.0,
        "SMTP": 0.0, "SSH": 0.0, "IRC": 0.0,
        "TCP": 1.0, "UDP": 0.0, "DHCP": 0.0, "ARP": 0.0,
        "ICMP": 0.0, "IPv": 1.0, "LLC": 0.0,
        "Tot sum": 400.0, "Min": 40.0, "Max": 150.0, "AVG": 80.0, "Std": 25.0,
        "Tot size": 400.0, "IAT": 15.0, "Number": 6.0, "Magnitue": 196.0,
        "Radius": 35.0, "Covariance": 625.0, "Variance": 625.0, "Weight": 6.0,
    },
    "ip_camera": {
        "flow_duration": 5000.0, "Header_Length": 40.0, "Protocol Type": 17.0,
        "Duration": 5.0, "Rate": 200.0, "Srate": 100.0, "Drate": 100.0,
        "fin_flag_number": 0.0, "syn_flag_number": 0.0, "rst_flag_number": 0.0,
        "psh_flag_number": 0.0, "ack_flag_number": 0.0, "ece_flag_number": 0.0,
        "cwr_flag_number": 0.0, "ack_count": 0.0, "syn_count": 0.0,
        "fin_count": 0.0, "urg_count": 0.0, "rst_count": 0.0,
        "HTTP": 0.0, "HTTPS": 0.0, "DNS": 0.0, "Telnet": 0.0,
        "SMTP": 0.0, "SSH": 0.0, "IRC": 0.0,
        "TCP": 0.0, "UDP": 1.0, "DHCP": 0.0, "ARP": 0.0,
        "ICMP": 0.0, "IPv": 1.0, "LLC": 0.0,
        "Tot sum": 150000.0, "Min": 500.0, "Max": 1400.0, "AVG": 1000.0,
        "Std": 200.0, "Tot size": 150000.0, "IAT": 5.0, "Number": 150.0,
        "Magnitue": 12247.0, "Radius": 100.0, "Covariance": 40000.0,
        "Variance": 40000.0, "Weight": 150.0,
    },
    "smart_door_lock": {
        "flow_duration": 20.0, "Header_Length": 40.0, "Protocol Type": 6.0,
        "Duration": 0.02, "Rate": 5.0, "Srate": 2.5, "Drate": 2.5,
        "fin_flag_number": 1.0, "syn_flag_number": 1.0, "rst_flag_number": 0.0,
        "psh_flag_number": 1.0, "ack_flag_number": 3.0, "ece_flag_number": 0.0,
        "cwr_flag_number": 0.0, "ack_count": 6.0, "syn_count": 1.0,
        "fin_count": 1.0, "urg_count": 0.0, "rst_count": 0.0,
        "HTTP": 0.0, "HTTPS": 1.0, "DNS": 0.0, "Telnet": 0.0,
        "SMTP": 0.0, "SSH": 0.0, "IRC": 0.0,
        "TCP": 1.0, "UDP": 0.0, "DHCP": 0.0, "ARP": 0.0,
        "ICMP": 0.0, "IPv": 1.0, "LLC": 0.0,
        "Tot sum": 256.0, "Min": 40.0, "Max": 100.0, "AVG": 64.0, "Std": 15.0,
        "Tot size": 256.0, "IAT": 10.0, "Number": 4.0, "Magnitue": 128.0,
        "Radius": 22.0, "Covariance": 225.0, "Variance": 225.0, "Weight": 4.0,
    },
}


def _apply_syn_flood(features: dict[str, float], rng: random.Random) -> None:
    features["syn_flag_number"] = rng.uniform(50.0, 200.0)
    features["syn_count"] = rng.uniform(100.0, 500.0)
    features["Rate"] = rng.uniform(1000.0, 5000.0)
    features["Srate"] = rng.uniform(500.0, 2500.0)
    features["flow_duration"] = rng.uniform(1.0, 10.0)
    features["Number"] = rng.uniform(200.0, 1000.0)
    features["ack_flag_number"] = 0.0
    features["ack_count"] = 0.0


def _apply_port_scan(features: dict[str, float], rng: random.Random) -> None:
    features["rst_flag_number"] = rng.uniform(20.0, 100.0)
    features["rst_count"] = rng.uniform(50.0, 200.0)
    features["syn_flag_number"] = rng.uniform(30.0, 150.0)
    features["syn_count"] = rng.uniform(30.0, 150.0)
    features["flow_duration"] = rng.uniform(0.5, 5.0)
    features["Number"] = rng.uniform(100.0, 500.0)
    features["Rate"] = rng.uniform(500.0, 3000.0)
    features["fin_count"] = 0.0


def _apply_arp_spoofing(features: dict[str, float], rng: random.Random) -> None:
    features["ARP"] = 1.0
    features["TCP"] = 0.0
    features["UDP"] = 0.0
    features["Header_Length"] = rng.uniform(28.0, 42.0)
    features["Drate"] = rng.uniform(50.0, 200.0)
    features["flow_duration"] = rng.uniform(1.0, 5.0)
    features["Rate"] = rng.uniform(100.0, 500.0)
    features["Number"] = rng.uniform(50.0, 300.0)


def _apply_dns_tunnel(features: dict[str, float], rng: random.Random) -> None:
    features["DNS"] = 1.0
    features["UDP"] = 1.0
    features["TCP"] = 0.0
    features["Tot size"] = rng.uniform(50000.0, 200000.0)
    features["Tot sum"] = rng.uniform(50000.0, 200000.0)
    features["AVG"] = rng.uniform(500.0, 2000.0)
    features["Max"] = rng.uniform(1000.0, 4000.0)
    features["flow_duration"] = rng.uniform(1000.0, 10000.0)
    features["Number"] = rng.uniform(50.0, 300.0)


_ATTACK_FUNCTIONS = [
    _apply_syn_flood,
    _apply_port_scan,
    _apply_arp_spoofing,
    _apply_dns_tunnel,
]


class TrafficFeatureGenerator:
    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    def generate(
        self,
        device_type: str,
        mode: str = "normal",
        attack_type: str | None = None,
    ) -> dict[str, float]:
        profile = DEVICE_PROFILES.get(device_type, DEVICE_PROFILES["temperature_sensor"])
        features: dict[str, float] = {}

        for name in FEATURE_NAMES:
            base = profile.get(name, 0.0)
            if name in _PROTOCOL_FEATURES:
                features[name] = base
            else:
                noise = self._rng.gauss(0, abs(base) * 0.08 + 0.01)
                features[name] = max(0.0, base + noise)

        if mode == "abnormal":
            attack_map = {
                "syn_flood": _apply_syn_flood,
                "port_scan": _apply_port_scan,
                "arp_spoofing": _apply_arp_spoofing,
                "dns_tunnel": _apply_dns_tunnel,
            }
            if attack_type and attack_type in attack_map:
                attack_map[attack_type](features, self._rng)
            else:
                attack_fn = self._rng.choice(_ATTACK_FUNCTIONS)
                attack_fn(features, self._rng)

        return features
