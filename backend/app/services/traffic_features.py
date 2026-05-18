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

# ---------------------------------------------------------------------------
# CICIoT23 scaler statistics (mean / std) extracted from scaler_ciciot23.pkl.
# ---------------------------------------------------------------------------

_SCALER_STATS: dict[str, tuple[float, float]] = {
    "flow_duration":     (39.2982,        54.2507),
    "Header_Length":     (1_015_165.5359, 1_331_985.1537),
    "Protocol Type":     (7.4873,         2.2591),
    "Duration":          (115.2364,       51.2916),
    "Rate":              (1955.9181,      19_971.9773),
    "Srate":             (1955.9181,      19_971.9773),
    "Drate":             (0.0,            1.0),
    "fin_flag_number":   (0.0,            0.0028),
    "syn_flag_number":   (0.0,            0.0063),
    "rst_flag_number":   (0.0,            0.0063),
    "psh_flag_number":   (0.0178,         0.1322),
    "ack_flag_number":   (0.8489,         0.3582),
    "ece_flag_number":   (0.0,            1.0),
    "cwr_flag_number":   (0.0,            1.0),
    "ack_count":         (0.0426,         0.1346),
    "syn_count":         (0.8013,         0.7721),
    "fin_count":         (0.0115,         0.4899),
    "urg_count":         (118.0856,       167.4301),
    "rst_count":         (1072.4524,      1244.8013),
    "HTTP":              (0.0389,         0.1934),
    "HTTPS":             (0.7109,         0.4533),
    "DNS":               (0.0018,         0.0427),
    "Telnet":            (0.0,            1.0),
    "SMTP":              (0.0,            1.0),
    "SSH":               (0.0,            1.0),
    "IRC":               (0.0,            1.0),
    "TCP":               (0.8608,         0.3461),
    "UDP":               (0.0681,         0.2519),
    "DHCP":              (0.0,            1.0),
    "ARP":               (0.0003,         0.0178),
    "ICMP":              (0.0,            0.0028),
    "IPv":               (0.9993,         0.0268),
    "LLC":               (0.9993,         0.0268),
    "Tot sum":           (6509.5443,      7656.3795),
    "Min":               (180.5950,       335.9913),
    "Max":               (1717.6257,      2017.2547),
    "AVG":               (620.0100,       668.7166),
    "Std":               (494.4687,       570.8982),
    "Tot size":          (618.7993,       674.7426),
    "IAT":               (83_664_475.1353, 83_259_692.0646),
    "Number":            (9.5159,         4.0009),
    "Magnitue":          (29.9872,        17.6069),
    "Radius":            (698.5548,       808.2908),
    "Covariance":        (641_304.9846,   1_722_217.9847),
    "Variance":          (0.8626,         0.2336),
    "Weight":            (141.9544,       103.0460),
}

# ---------------------------------------------------------------------------
# "Normal" anchor — real-space feature values obtained by passing a zero
# vector through the trained CICIoT23 autoencoder and inverse-transforming
# the reconstruction.  The autoencoder reconstructs these with error ~0.018,
# well below the anomaly threshold (0.048).
# ---------------------------------------------------------------------------

_NORMAL_ANCHOR: dict[str, float] = {
    "flow_duration":     10.38,
    "Header_Length":     206_134.69,
    "Protocol Type":     7.90,
    "Duration":          124.81,
    "Rate":              2628.35,
    "Srate":             1684.55,
    "Drate":             0.01,
    "fin_flag_number":   0.0004,
    "syn_flag_number":   0.0,
    "rst_flag_number":   0.0,
    "psh_flag_number":   0.011,
    "ack_flag_number":   0.817,
    "ece_flag_number":   0.007,
    "cwr_flag_number":   0.009,
    "ack_count":         0.0,
    "syn_count":         0.929,
    "fin_count":         0.097,
    "urg_count":         17.62,
    "rst_count":         267.46,
    "HTTP":              0.0,
    "HTTPS":             0.327,
    "DNS":               0.0,
    "Telnet":            0.0,
    "SMTP":              0.0,
    "SSH":               0.0,
    "IRC":               0.0,
    "TCP":               1.0,
    "UDP":               0.0,
    "DHCP":              0.0,
    "ARP":               0.002,
    "ICMP":              0.0,
    "IPv":               0.998,
    "LLC":               0.998,
    "Tot sum":           2653.04,
    "Min":               80.67,
    "Max":               2449.01,
    "AVG":               513.82,
    "Std":               844.28,
    "Tot size":          742.14,
    "IAT":               24_285_064.0,
    "Number":            6.63,
    "Magnitue":          30.18,
    "Radius":            1183.27,
    "Covariance":        1_008_068.25,
    "Variance":          1.003,
    "Weight":            64.75,
}

# ---------------------------------------------------------------------------
# Per-device-type offsets from _NORMAL_ANCHOR, in units of scaler std.
# Small (|offset| <= 0.08) to stay within autoencoder tolerance.
# ---------------------------------------------------------------------------

_DEVICE_OFFSETS: dict[str, dict[str, float]] = {
    "temperature_sensor": {
        "flow_duration": 0.02, "Duration": 0.01, "Number": -0.02,
        "Tot sum": -0.02, "Weight": 0.01,
    },
    "smart_plug": {
        "flow_duration": -0.01, "Duration": -0.01, "Rate": 0.01,
        "Tot sum": 0.02, "Number": 0.02, "Weight": -0.01,
    },
    "ip_camera": {
        "flow_duration": 0.04, "Duration": 0.03, "Rate": 0.02,
        "Tot sum": 0.04, "Tot size": 0.03, "Number": 0.04,
        "Header_Length": 0.03,
    },
    "smart_door_lock": {
        "flow_duration": -0.02, "Duration": -0.01, "Rate": -0.01,
        "Number": -0.02, "Tot sum": -0.02, "Weight": 0.02,
    },
    "robot_vacuum": {
        "flow_duration": 0.01, "Duration": 0.02, "Rate": 0.015,
        "Tot sum": 0.015, "Number": 0.01, "Weight": -0.015,
    },
}


# ---------------------------------------------------------------------------
# Attack modifiers — shift features by 3-8 scaler std from the anchor
# to cause high autoencoder reconstruction error.
# ---------------------------------------------------------------------------

def _apply_syn_flood(features: dict[str, float], rng: random.Random) -> None:
    mean, std = _SCALER_STATS["syn_flag_number"]
    features["syn_flag_number"] = mean + std * rng.uniform(5, 8)
    mean, std = _SCALER_STATS["syn_count"]
    features["syn_count"] = mean + std * rng.uniform(4, 7)
    mean, std = _SCALER_STATS["Rate"]
    features["Rate"] = mean + std * rng.uniform(3, 6)
    mean, std = _SCALER_STATS["Srate"]
    features["Srate"] = mean + std * rng.uniform(3, 6)
    mean, std = _SCALER_STATS["Number"]
    features["Number"] = mean + std * rng.uniform(4, 8)
    features["ack_flag_number"] = 0.0
    features["ack_count"] = 0.0


def _apply_port_scan(features: dict[str, float], rng: random.Random) -> None:
    mean, std = _SCALER_STATS["rst_flag_number"]
    features["rst_flag_number"] = mean + std * rng.uniform(5, 8)
    mean, std = _SCALER_STATS["rst_count"]
    features["rst_count"] = mean + std * rng.uniform(4, 7)
    mean, std = _SCALER_STATS["syn_flag_number"]
    features["syn_flag_number"] = mean + std * rng.uniform(4, 7)
    mean, std = _SCALER_STATS["syn_count"]
    features["syn_count"] = mean + std * rng.uniform(3, 6)
    mean, std = _SCALER_STATS["Number"]
    features["Number"] = mean + std * rng.uniform(3, 6)
    mean, std = _SCALER_STATS["Rate"]
    features["Rate"] = mean + std * rng.uniform(3, 5)
    features["fin_count"] = 0.0


def _apply_arp_spoofing(features: dict[str, float], rng: random.Random) -> None:
    features["ARP"] = 1.0
    features["TCP"] = 0.0
    features["UDP"] = 0.0
    mean, std = _SCALER_STATS["Header_Length"]
    features["Header_Length"] = mean - std * rng.uniform(0.6, 0.75)
    mean, std = _SCALER_STATS["Drate"]
    features["Drate"] = mean + std * rng.uniform(5, 8)
    mean, std = _SCALER_STATS["Rate"]
    features["Rate"] = mean + std * rng.uniform(3, 5)
    mean, std = _SCALER_STATS["Number"]
    features["Number"] = mean + std * rng.uniform(4, 7)


def _apply_dns_tunnel(features: dict[str, float], rng: random.Random) -> None:
    features["DNS"] = 1.0
    features["UDP"] = 1.0
    features["TCP"] = 0.0
    mean, std = _SCALER_STATS["Tot size"]
    features["Tot size"] = mean + std * rng.uniform(5, 8)
    mean, std = _SCALER_STATS["Tot sum"]
    features["Tot sum"] = mean + std * rng.uniform(5, 8)
    mean, std = _SCALER_STATS["AVG"]
    features["AVG"] = mean + std * rng.uniform(4, 7)
    mean, std = _SCALER_STATS["Max"]
    features["Max"] = mean + std * rng.uniform(3, 6)
    mean, std = _SCALER_STATS["flow_duration"]
    features["flow_duration"] = mean + std * rng.uniform(4, 8)
    mean, std = _SCALER_STATS["Number"]
    features["Number"] = mean + std * rng.uniform(3, 6)


def _apply_ddos(features: dict[str, float], rng: random.Random) -> None:
    mean, std = _SCALER_STATS["Rate"]
    features["Rate"] = mean + std * rng.uniform(5, 10)
    mean, std = _SCALER_STATS["Srate"]
    features["Srate"] = mean + std * rng.uniform(5, 10)
    mean, std = _SCALER_STATS["Number"]
    features["Number"] = mean + std * rng.uniform(5, 10)
    mean, std = _SCALER_STATS["Tot sum"]
    features["Tot sum"] = mean + std * rng.uniform(4, 8)
    mean, std = _SCALER_STATS["Tot size"]
    features["Tot size"] = mean + std * rng.uniform(4, 8)
    mean, std = _SCALER_STATS["Header_Length"]
    features["Header_Length"] = mean + std * rng.uniform(3, 6)


_ATTACK_FUNCTIONS = [
    _apply_syn_flood,
    _apply_port_scan,
    _apply_arp_spoofing,
    _apply_dns_tunnel,
    _apply_ddos,
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
        offsets = _DEVICE_OFFSETS.get(
            device_type, _DEVICE_OFFSETS["temperature_sensor"],
        )
        features: dict[str, float] = {}

        for name in FEATURE_NAMES:
            _mean, std = _SCALER_STATS[name]
            anchor = _NORMAL_ANCHOR[name]
            device_offset = offsets.get(name, 0.0)

            if name in _PROTOCOL_FEATURES:
                features[name] = max(0.0, anchor + std * device_offset)
            else:
                noise = self._rng.gauss(0, std * 0.05)
                features[name] = max(0.0, anchor + std * device_offset + noise)

        if mode == "abnormal":
            attack_map = {
                "syn_flood": _apply_syn_flood,
                "port_scan": _apply_port_scan,
                "arp_spoofing": _apply_arp_spoofing,
                "dns_tunnel": _apply_dns_tunnel,
                "DDoS": _apply_ddos,
            }
            if attack_type and attack_type in attack_map:
                attack_map[attack_type](features, self._rng)
            else:
                attack_fn = self._rng.choice(_ATTACK_FUNCTIONS)
                attack_fn(features, self._rng)

        return features
