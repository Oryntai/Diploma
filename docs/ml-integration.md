# ML Integration

## Purpose

The ML layer provides anomaly detection for IoT network behavior. It is used to demonstrate an intelligent security monitoring workflow rather than real packet capture.

## Model

- Type: PyTorch autoencoder.
- Feature space: CICIoT2023-style network features.
- Feature count: 46.
- Output: reconstruction error.
- Decision rule: anomaly if reconstruction error is greater than the configured threshold.

## Input Sample

The demo workflow sends a compact network sample:

```text
timestamp
device_id
protocol
bytes_per_second
packets_per_second
connection_count
latency_ms
packet_loss_percent
```

## Feature Adapter

`NetworkFeatureAdapter` converts the compact sample into the trained model feature space.

Mapping behavior:

- normal traffic uses the normal feature generator mode;
- flood-like traffic uses abnormal DDoS-style generation;
- high traffic volume uses abnormal traffic-volume generation;
- high latency or packet loss uses degraded suspicious network generation.
- single-metric attack presets isolate one abnormal value while keeping the rest normal.

This adapter is a demo bridge between simple UI samples and the trained CICIoT2023 autoencoder.

## Alert Output

When the model detects an anomaly, the backend returns an alert with:

```text
timestamp
device_id
device_name
severity
attack_type
source = ml_autoencoder
message
explanation
reconstruction_error
threshold
risk_level
```

`message` is intentionally short for the UI table. `explanation` contains the full technical reason and ML score details.

## Device Profiles

The demo registry contains five simulated IoT profiles:

- room temperature sensor;
- smart plug;
- IP security camera;
- smart door lock;
- robot vacuum.

Each profile can run a normal sample and an attack-like sample through the same ML pipeline.

## Normal And Attack Expectations

- Normal sample: no alert.
- Attack-like flood sample: one critical ML alert.
- Degraded network sample: one ML alert if model score exceeds threshold.
- Single-metric samples: separate ML alerts for bandwidth-only, packet-rate-only, connection-count-only, latency-only, and packet-loss-only anomalies.

## Runtime Policy

ML alerts are session-only during the prototype phase. They are exported to logs and reports but not written to the database.
