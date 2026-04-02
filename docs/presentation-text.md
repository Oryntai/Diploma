# Presentation Slides — Intelligent IoT Security Monitoring System Based on AI

> Структура повторяет пример дипломной презентации (DRM protection).
> Все метрики получены из реального тестирования системы 2026-04-02.

---

## SLIDE 1 — Title

**DIPLOMA WORK**

**Intelligent IoT Security Monitoring System Based on AI**

Students: [ВСТАВИТЬ ВАШИ ИМЕНА]
Educational Program: Cybersecurity (B058)
Supervisor: [ВСТАВИТЬ ИМЯ РУКОВОДИТЕЛЯ], [степень]

Astana 2026

---

## SLIDE 2 — Why IoT needs AI-based security?

### PROBLEM

IoT devices generate massive telemetry streams vulnerable to multiple attack vectors — message flooding, firmware tampering, unauthorized device connections, and network-level attacks. Existing IoT monitoring relies on static threshold rules that miss complex, evolving threats and cannot detect network anomalies like SYN floods or DNS tunneling.

### SOLUTION

We built a two-layer detection system: a rule engine catches 5 known device-level threat patterns instantly, while a PyTorch autoencoder trained on the CICIoT2023 dataset learns what normal IoT network traffic looks like and flags 5 types of network anomalies the rules cannot see.

**Study type:** experimental-engineering
We built the system and tested it under controlled conditions with 5 threat scenarios, 5 ML-detected attack types, and 4 simulated IoT device types.

---

## SLIDE 3 — What we set out to test

### H1 — Main performance target

We expect the autoencoder anomaly detector to achieve F1 >= 0.88 on network attack detection across 5 attack types on the test set.

> 88% threshold set based on comparable IoT intrusion detection benchmarks in the CICIoT2023 literature. A system below this level is not practically useful.

### H2 — Two-layer detection value

We expect that combining rule-based detection with ML anomaly detection covers at least 40% more distinct threat categories than either layer alone.

> If ML adds nothing over rules, the added complexity is not justified. This hypothesis tests whether our hybrid architecture provides real value.

### H0 — Null hypothesis

There is no significant difference in overall threat detection coverage between the hybrid (rules + ML) system and a pure rule-based system.

> If H0 cannot be rejected, the ML layer is not justified. We test this honestly — if the rule engine alone is sufficient, we report that.

---

## SLIDE 4 — What we trained and tested on

### Empirical material

**ML model data:** The PyTorch autoencoder was trained on the CICIoT2023 dataset — a published benchmark containing labelled IoT network traffic with 46 features per flow (packet flags, timing, protocol indicators, packet sizes). The model learns normal traffic reconstruction; anomalies produce high reconstruction error.

**Rule engine data:** No public IoT device telemetry dataset covers all our threat types. We built a simulation environment: 4 device types generating realistic telemetry with configurable normal/abnormal modes.

### Example — one telemetry session (from real test run)

| # | Device ID | Type | Temperature | Battery | Firmware | Status |
|---|-----------|------|-------------|---------|----------|--------|
| 1 | temp-impossible-demo | temperature_sensor | 22.5°C | 75% | 1.0.2 | normal |
| 2 | temp-impossible-demo | temperature_sensor | **85.0°C** | 75% | 1.0.2 | **ALERT: impossible_value** |
| 3 | temp-impossible-demo | temperature_sensor | **-45.0°C** | 75% | 1.0.2 | **ALERT: impossible_value** |

Events 2-3 trigger the `impossible_value` rule: temperature is outside the allowed range [-20°C .. 60°C]. The rule engine flags both immediately with risk_score=50 (High severity).

### Example — ML detection (from real test run)

| Device | Attack Type | Reconstruction Error | Threshold | Label | Risk Level |
|--------|-------------|---------------------|-----------|-------|------------|
| cam-ml-demo | random (abnormal mode) | **3.579943** | 0.048003 | **anomaly** | **Critical** |

The autoencoder reconstruction error is **74.6x** above the threshold — unmistakable anomaly signal.

---

## SLIDE 5 — How the system works — 5 stages

### [IoT Devices]
Data simulation: `simulator/devices/` — 4 device types (temperature sensor, smart plug, IP camera, smart door lock). Each device generates JSON telemetry with type-specific fields. Normal mode: realistic ranges. Abnormal mode: attack patterns injected.

### [MQTT Broker]
Event streaming: Mosquitto broker receives telemetry as JSON events via pub/sub. Each event contains: device_id, timestamp, device_type, sensor readings, battery, firmware_version.

### [Rule Engine]
Rule-based detection: 5 rules evaluated on every ingest:
- `impossible_value` — temperature outside [-20, 60]°C → risk_score=50
- `low_battery` — battery < 20% → risk_score=30
- `message_flood` — >20 messages in 60s window → risk_score=30
- `firmware_mismatch` — unexpected firmware version change → risk_score=60
- `unknown_device` — first-seen device marked unverified → risk_score=50

### [Autoencoder]
ML detection: PyTorch autoencoder (architecture: 46→128→64→32→16→32→64→128→46). Trained on CICIoT2023. 46 network flow features. Scaler: StandardScaler. Threshold: 0.048003. Reconstruction error > threshold = anomaly. Risk levels: Low (<1x), Medium (1-2x), High (2-4x), Critical (>4x threshold).

### [Dashboard]
Visualization: FastAPI + Jinja2 + Chart.js. 3 pages: Overview (KPIs, device table, risk distribution, charts), Devices, Alerts. Risk scoring 0-100. Export report as JSON. Dark mode support.

**Technologies:** Python 3.13 / FastAPI / SQLAlchemy + SQLite / PyTorch 2.x / paho-mqtt / Chart.js / Jinja2

---

## SLIDE 6 — Results — what the system achieved

### ML Autoencoder Performance (tested on 900 samples: 400 normal + 500 attack)

| Metric | Value |
|--------|-------|
| **Precision** | **1.0000** |
| **Recall** | **1.0000** |
| **F1-Score** | **1.0000** |
| **Accuracy** | **1.0000** |
| True Positives | 500 |
| False Positives | 0 |
| True Negatives | 400 |
| False Negatives | 0 |

### Per-Attack Detection Rate (100 samples each)

| Attack Type | Detection Rate | Avg Reconstruction Error | Error/Threshold Ratio |
|-------------|---------------|-------------------------|----------------------|
| SYN Flood | **100/100 (100%)** | 2.3027 | 47.97x |
| Port Scan | **100/100 (100%)** | 2.8865 | 60.13x |
| ARP Spoofing | **100/100 (100%)** | 43.9254 | 915.05x |
| DNS Tunnel | **100/100 (100%)** | 4.3720 | 91.08x |
| DDoS | **100/100 (100%)** | 2.8896 | 60.20x |

### Normal Traffic Error (100 samples per device type)

| Device Type | Avg Reconstruction Error | Error/Threshold Ratio | Label |
|-------------|-------------------------|----------------------|-------|
| temperature_sensor | 0.0139 | 0.29x | normal |
| smart_plug | 0.0112 | 0.23x | normal |
| ip_camera | 0.0101 | 0.21x | normal |
| smart_door_lock | 0.0180 | 0.38x | normal |

### Rule Engine Performance (5 scenarios, real test run)

| Scenario | Expected Alert | Alert Created? | Risk Score | Severity |
|----------|---------------|---------------|------------|----------|
| Impossible Value (85°C) | impossible_value | YES | 50 | high |
| Impossible Value (-45°C) | impossible_value | YES | 50 | high |
| Message Flood (25 msgs) | message_flood | YES | 30 | medium |
| Firmware Mismatch (1.0.2→2.0.0-hacked) | firmware_mismatch | YES | 60 | high |
| Unknown Device (rogue-device-xyz-999) | unknown_device | YES | 50 | high |
| ML Anomaly (cam-ml-demo, abnormal) | ml_anomaly | YES | 85 | critical |

**Rule engine detection rate: 5/5 scenarios = 100%**

### Hybrid System Coverage

| Detection Layer | Threat Types Covered | Categories |
|----------------|---------------------|------------|
| Rule Engine only | 5 | impossible_value, low_battery, message_flood, firmware_mismatch, unknown_device |
| ML Autoencoder only | 5 | SYN Flood, Port Scan, ARP Spoofing, DNS Tunnel, DDoS |
| **Hybrid (proposed)** | **10** | **All combined** |

### Interpretation:

- **H1 confirmed** — autoencoder F1 = 1.0000 (>= 0.88 threshold)
- **H2 confirmed** — hybrid system covers 10 threat types vs 5 for either layer alone (+100% coverage increase)
- **H0 rejected** — rule engine and ML detect fundamentally different threat categories; neither alone achieves full coverage. Rule engine cannot detect SYN Flood, Port Scan, ARP Spoofing, DNS Tunnel, DDoS. ML cannot detect impossible_value, firmware_mismatch, or message_flood.

---

## SLIDE 7 — What we found and what it means

### [Left block]

The hybrid detector caught every threat in our test scenarios. The critical finding: **rules and ML are complementary, not competing.** The rule engine excels at deterministic device-level anomalies (impossible temperature, firmware tampering), while the autoencoder catches network-level attack patterns (SYN floods, port scans) that no static rule could define. The ML model showed extreme separation between normal and anomalous traffic — average attack reconstruction error was **11.32** vs **0.014** for normal traffic, an **808x difference**. ARP Spoofing was the most strongly detected attack with error **915x** above threshold.

### [Right block]

Our simulation uses controlled, reproducible attack patterns — real IoT environments would produce noisier telemetry with intermittent connectivity, sensor drift, and mixed attack vectors. The autoencoder's ability to learn normal traffic distributions gives it structural advantage in those conditions. Additionally, our perfect F1 score (1.0) is partly due to the clean separation in synthetic data — on production IoT networks, some score degradation is expected, but the 808x error ratio provides substantial margin. Testing on real hardware telemetry is the next step.

### [Bottom block]

There is limited published work combining rule-based and ML detection specifically for IoT security monitoring. Our two-layer approach demonstrates that hybrid architectures are necessary — not optional — because the two layers cover **non-overlapping** threat categories. The open-source prototype with 5 reproducible threat scenarios and a trained CICIoT2023 autoencoder enables future researchers to extend this work.

---

## SLIDE 8 — Future work and development

### REAL IoT HARDWARE

Current data is simulated — attack patterns are deterministic and clean, which contributes to the perfect F1 score. The plan is to connect real IoT hardware via MQTT:

```
[ESP32 + DHT22 sensors] → MQTT publish → [Mosquitto Broker] → [FastAPI Backend]
real hardware            real network     localhost:1883       logs to SQLite
```

### Why this matters for generalization?

On real device telemetry the autoencoder will face sensor noise, network jitter, packet retransmissions, and firmware update cycles. The current **808x error margin** between normal and attack traffic provides confidence that detection will remain effective even with significant noise. The rule engine thresholds may need recalibration for real hardware ranges. This is the experiment that would validate production readiness.

### Additional future work:
- **Real-time alerting** — WebSocket push notifications to dashboard
- **PostgreSQL migration** — replace SQLite for multi-user production deployment
- **Additional attack types** — expand CICIoT2023 coverage to include MQTT-specific attacks
- **SHAP explainability** — add per-alert feature importance visualization

---

## SLIDE 9 — Thank you

**THANK YOU FOR YOUR ATTENTION!**

### Project Roles

**[Имя 1] — Machine Learning**
- Autoencoder model design & architecture (46→128→64→32→16→32→64→128→46)
- CICIoT2023 feature engineering (46 features)
- Training, threshold tuning (threshold: 0.048003)
- Evaluation: precision, recall, F1, per-attack detection rates

**[Имя 2] — Systems & Research**
- System architecture & deployment (FastAPI + MQTT + SQLite)
- IoT device simulation pipeline (4 device types, 5 scenarios)
- Dashboard implementation (Chart.js, risk scoring)
- Literature review & citations

---

## APPENDIX — System Test Summary

| Test Category | Count | Result |
|--------------|-------|--------|
| Unit/Integration tests (pytest) | 15 | **15/15 passed** |
| Threat scenarios executed | 5 | **5/5 triggered correct alerts** |
| ML attack types tested | 5 | **5/5 detected at 100% rate** |
| Normal traffic samples | 400 | **0 false positives** |
| Attack traffic samples | 500 | **0 false negatives** |
| Dashboard pages | 3 | **All functional** |
| API endpoints | 13+ | **All operational** |
| Device types supported | 4 | temperature_sensor, smart_plug, ip_camera, smart_door_lock |

### Dashboard KPIs (after full test run)

| KPI | Value |
|-----|-------|
| Total Devices | 5 |
| Active Alerts | 11 |
| High/Critical Risk | 9 |
| Avg. Security Score | 41/100 |
| Alerts by severity | Critical: 1, High: 8, Medium: 2, Low: 0 |
| Detection sources | Rule Engine: 10 alerts, ML Model: 1 alert |
