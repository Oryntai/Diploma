from __future__ import annotations

import json
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .core.settings import settings
from .db.session import DATABASE_URL, get_db
from .models.alert import Alert
from .models.device import Device
from .models.registered_device import RegisteredDevice
from .models.telemetry_event import TelemetryEvent
from .services.ml_runtime import MLRuntime
from .services.network_feature_adapter import NetworkFeatureAdapter
from .services.rule_engine import RuleEngine


class HealthResponse(BaseModel):
    status: str
    service: str
    now: datetime


class CountsResponse(BaseModel):
    registered_devices: int
    runtime_devices: int
    telemetry_events: int
    alerts: int


class SystemStatusResponse(BaseModel):
    backend_status: str
    database_url: str
    database_ready: bool
    counts: CountsResponse
    ml_status: dict[str, Any]
    runtime_components: dict[str, Any]
    detection_layers: dict[str, Any]
    experiment: dict[str, Any]


class ClearDataResponse(BaseModel):
    status: str
    deleted_devices: int
    deleted_telemetry_events: int
    deleted_alerts: int
    counts: CountsResponse


class RegisteredDeviceResponse(BaseModel):
    device_id: str
    device_name: str
    device_type: str
    device_mode: str
    ip_address: str | None
    mac_address: str | None


class NetworkSample(BaseModel):
    timestamp: datetime
    device_id: str = Field(min_length=1, max_length=100)
    protocol: str = Field(min_length=1, max_length=20)
    bytes_per_second: float = Field(ge=0)
    packets_per_second: float = Field(ge=0)
    connection_count: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    packet_loss_percent: float = Field(ge=0, le=100)


class DynamicAlert(BaseModel):
    timestamp: datetime
    device_id: str
    device_name: str
    severity: str
    attack_type: str
    source: str
    message: str
    explanation: str | None = None
    reconstruction_error: float | None = None
    threshold: float | None = None
    risk_level: str | None = None


class NetworkSampleResponse(BaseModel):
    status: str
    received_sample: NetworkSample
    alerts: list[DynamicAlert]


class DemoScenarioResponse(BaseModel):
    status: str
    samples_sent: int
    alerts_created: int
    results: list[NetworkSampleResponse]


class DeviceMLTestResult(BaseModel):
    device_id: str
    device_name: str
    normal: NetworkSampleResponse
    attack: NetworkSampleResponse


class DeviceMLTestResponse(BaseModel):
    status: str
    devices_tested: int
    tests_run: int
    alerts_created: int
    results: list[DeviceMLTestResult]


ml_runtime = MLRuntime(model_path=settings.ml_model_path)
feature_adapter = NetworkFeatureAdapter()
rule_engine = RuleEngine()
network_log_path = Path(__file__).resolve().parents[2] / "logs" / "network_samples.log"

RUNTIME_COMPONENTS: dict[str, Any] = {
    "operator_interface": "FastAPI web dashboard",
    "sample_simulation": "Desktop device simulator, FastAPI demo endpoints, and CLI simulator",
    "desktop_simulator_available": True,
    "desktop_simulator_module": "desktop_simulator.main",
    "persistence": "SQLite device registry and persisted alert rows",
    "runtime_scope": "local diploma prototype",
}

DETECTION_LAYERS: dict[str, Any] = {
    "deterministic_rule_engine": {
        "enabled": True,
        "purpose": "predictable device identity and metadata checks",
        "source": "rule_engine",
    },
    "ciciot2023_feature_adapter": {
        "enabled": True,
        "feature_count": 46,
    },
    "ml_autoencoder": {
        "enabled": True,
        "source": "ml_autoencoder",
        "decision_rule": "anomaly if reconstruction error exceeds validation threshold",
    },
}

EXPERIMENTAL_RESULTS: dict[str, Any] = {
    "dataset": "CICIoT2023",
    "feature_count": 46,
    "autoencoder_epochs": 50,
    "baseline": "Isolation Forest",
    "precision": 0.9988,
    "recall": 0.9864,
    "f1_score": 0.9925,
    "runtime_validation": "simulated telemetry",
    "future_hardware_validation": "Xiaomi Mi Robot Vacuum-Mop P",
}

REGISTERED_DEMO_DEVICES: list[dict[str, str]] = [
    {
        "device_id": "dev-001",
        "device_name": "Room Temperature Sensor",
        "device_type": "temperature_sensor",
        "device_mode": "simulated",
        "ip_address": "192.168.1.42",
        "mac_address": "02:1A:7D:00:01:2A",
    },
    {
        "device_id": "dev-002",
        "device_name": "Smart Plug",
        "device_type": "smart_plug",
        "device_mode": "simulated",
        "ip_address": "192.168.1.43",
        "mac_address": "02:1A:7D:00:01:2B",
    },
    {
        "device_id": "dev-003",
        "device_name": "IP Security Camera",
        "device_type": "ip_camera",
        "device_mode": "simulated",
        "ip_address": "192.168.1.44",
        "mac_address": "02:1A:7D:00:01:2C",
    },
    {
        "device_id": "dev-004",
        "device_name": "Smart Door Lock",
        "device_type": "smart_door_lock",
        "device_mode": "simulated",
        "ip_address": "192.168.1.45",
        "mac_address": "02:1A:7D:00:01:2D",
    },
    {
        "device_id": "dev-005",
        "device_name": "Robot Vacuum",
        "device_type": "robot_vacuum",
        "device_mode": "simulated",
        "ip_address": "192.168.1.46",
        "mac_address": "02:1A:7D:00:01:2E",
    },
]


class _WarmupSample:
    packets_per_second = 0.2
    connection_count = 1
    bytes_per_second = 512.0
    latency_ms = 12.0
    packet_loss_percent = 0.0


def _warm_ml_runtime() -> None:
    try:
        context = feature_adapter.adapt(_WarmupSample(), "temperature_sensor")
        ml_runtime.predict_with_context(context.features)
    except Exception:
        # Status endpoint will expose the real model state; warmup must not block startup.
        return


@asynccontextmanager
async def lifespan(_: FastAPI):
    thread = threading.Thread(target=_warm_ml_runtime, daemon=True)
    thread.start()
    yield


app = FastAPI(title="IoT Security Monitoring", lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")
session_alerts: list[DynamicAlert] = []


def _counts(db: Session) -> CountsResponse:
    return CountsResponse(
        registered_devices=int(db.scalar(select(func.count(RegisteredDevice.id))) or 0),
        runtime_devices=int(db.scalar(select(func.count(Device.id))) or 0),
        telemetry_events=int(db.scalar(select(func.count(TelemetryEvent.id))) or 0),
        alerts=int(db.scalar(select(func.count(Alert.id))) or 0),
    )


def _severity_score(severity: str | None) -> int:
    return {
        "critical": 95,
        "high": 80,
        "medium": 55,
        "low": 25,
    }.get((severity or "low").lower(), 25)


def _registered_device_cards(db: Session) -> list[dict[str, Any]]:
    devices = _ensure_registered_demo_devices(db)
    active_by_device: dict[str, list[DynamicAlert]] = {}
    for alert in session_alerts:
        active_by_device.setdefault(alert.device_id, []).append(alert)

    cards: list[dict[str, Any]] = []
    for device in devices:
        alerts = active_by_device.get(device.device_id, [])
        top_alert = max(alerts, key=lambda item: _severity_score(item.severity), default=None)
        risk_score = _severity_score(top_alert.severity if top_alert else "low")
        risk_level = (top_alert.risk_level if top_alert else "Low") or "Low"
        cards.append(
            {
                "device_id": device.device_id,
                "device_name": device.device_name,
                "device_type": device.device_type,
                "status": "online",
                "battery": None,
                "firmware_version": "simulated",
                "last_seen_at": datetime.now(UTC),
                "risk_level": risk_level,
                "risk_score": risk_score,
                "main_issue": top_alert.message if top_alert else "No active anomaly",
                "recommendation": (
                    "Inspect the latest network sample and isolate the device if traffic persists."
                    if top_alert
                    else "Keep monitoring baseline traffic."
                ),
            }
        )
    return cards


def _summary(db: Session) -> dict[str, Any]:
    devices = _registered_device_cards(db)
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for alert in session_alerts:
        severity_counts[alert.severity.lower()] = severity_counts.get(alert.severity.lower(), 0) + 1

    avg_score = 100
    if devices:
        avg_score = round(sum(100 - int(device["risk_score"]) for device in devices) / len(devices), 1)
    return {
        "total_devices": len(devices),
        "online_devices": len(devices),
        "active_alerts": len(session_alerts),
        "avg_security_score": avg_score,
        "alerts_by_severity": severity_counts,
    }


def _alert_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, alert in enumerate(reversed(session_alerts), start=1):
        rows.append(
            {
                "id": index,
                "alert_key": _alert_key(alert),
                "device_id": alert.device_id,
                "device_href": _device_href(alert.device_id),
                "alert_type": _alert_type_label(alert),
                "raw_alert_type": alert.attack_type,
                "severity": alert.severity,
                "risk_score": _severity_score(alert.severity),
                "source": alert.source,
                "source_label": _source_label(alert.source),
                "reason": alert.message,
                "details": _alert_details(alert),
                "created_at": alert.timestamp,
            }
        )
    return rows


def _device_href(device_id: str) -> str | None:
    registered_ids = {device["device_id"] for device in REGISTERED_DEMO_DEVICES}
    if device_id not in registered_ids:
        return None
    return f"/dashboard/devices/{device_id}"


def _alert_key(alert: DynamicAlert) -> str:
    return "|".join(
        [
            alert.timestamp.isoformat(timespec="microseconds"),
            alert.device_id,
            alert.attack_type,
            alert.source,
        ]
    )


def _source_label(source: str) -> str:
    return {
        "rule_engine": "Rule Engine",
        "ml_autoencoder": "ML Autoencoder",
        "ml_model": "ML Model",
    }.get(source, source.replace("_", " ").title())


def _alert_type_label(alert: DynamicAlert) -> str:
    labels = {
        "ml_flood_anomaly": "Flood anomaly",
        "ml_packet_rate_anomaly": "Packet-rate spike",
        "ml_connection_fanout_anomaly": "Connection fan-out",
        "ml_bandwidth_anomaly": "Bandwidth spike",
        "ml_latency_anomaly": "Latency spike",
        "ml_packet_loss_anomaly": "Packet-loss spike",
        "ml_low_value_anomaly": "Low-value anomaly",
        "ml_network_anomaly": "ML anomaly",
        "unknown_device": "Unknown device",
    }
    return labels.get(alert.attack_type, alert.attack_type.replace("_", " ").title())


def _alert_details(alert: DynamicAlert) -> str | None:
    parts: list[str] = []
    if alert.reconstruction_error is not None and alert.threshold is not None:
        parts.append(
            f"ML score {alert.reconstruction_error:.6f} > threshold {alert.threshold:.6f}"
        )
    if alert.risk_level:
        parts.append(f"Risk level: {alert.risk_level}")
    if alert.explanation:
        parts.append(alert.explanation)
    return " | ".join(parts) if parts else None


def _risk_explanations(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    labels = {
        "critical": ("Critical", "90-100", "Immediate isolation may be required."),
        "high": ("High", "70-89", "Traffic pattern needs operator attention."),
        "medium": ("Medium", "40-69", "Monitor the device and compare with baseline."),
        "low": ("Low", "0-39", "No urgent action."),
    }
    return {
        key: {
            "label": label,
            "current_count": summary["alerts_by_severity"].get(key, 0),
            "class_description": description,
            "score_range": score_range,
            "why_now": "Current session rule and ML alerts drive this class.",
            "typical_causes": ["traffic volume spike", "packet rate spike", "connection fan-out", "latency or packet loss anomaly"],
            "current_reasons": [alert.message for alert in session_alerts if alert.severity == key],
        }
        for key, (label, score_range, description) in labels.items()
    }


def _ensure_registered_demo_devices(db: Session) -> list[RegisteredDevice]:
    old_device = db.scalar(
        select(RegisteredDevice).where(
            RegisteredDevice.device_id == "room-temp-sensor-001"
        )
    )
    if old_device is not None:
        old_device.device_id = "dev-001"
        old_device.device_name = "Room Temperature Sensor"
        old_device.device_type = "temperature_sensor"
        old_device.device_mode = "simulated"
        old_device.ip_address = old_device.ip_address or "192.168.1.42"
        old_device.mac_address = old_device.mac_address or "02:1A:7D:00:01:2A"
        db.commit()

    devices: list[RegisteredDevice] = []
    for payload in REGISTERED_DEMO_DEVICES:
        device = db.scalar(
            select(RegisteredDevice).where(
                RegisteredDevice.device_id == payload["device_id"]
            )
        )
        if device is None:
            device = RegisteredDevice(**payload)
            db.add(device)
            db.commit()
            db.refresh(device)
        else:
            changed = False
            for key, value in payload.items():
                if getattr(device, key) != value:
                    setattr(device, key, value)
                    changed = True
            if changed:
                db.commit()
                db.refresh(device)
        devices.append(device)
    return devices


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="backend",
        now=datetime.now(UTC),
    )


@app.get("/api/system/status", response_model=SystemStatusResponse)
def system_status(db: Session = Depends(get_db)) -> SystemStatusResponse:
    _ensure_registered_demo_devices(db)
    return SystemStatusResponse(
        backend_status="ok",
        database_url=DATABASE_URL,
        database_ready=True,
        counts=_counts(db),
        ml_status=ml_runtime.get_status(),
        runtime_components=RUNTIME_COMPONENTS,
        detection_layers=DETECTION_LAYERS,
        experiment=EXPERIMENTAL_RESULTS,
    )


@app.get("/api/ml/status")
def ml_status() -> dict[str, Any]:
    return ml_runtime.get_status()


def _evaluate_rule_sample(
    sample: NetworkSample,
    device_name: str,
    registered_device: bool,
) -> list[DynamicAlert]:
    alerts: list[DynamicAlert] = []
    for finding in rule_engine.evaluate(sample, registered_device=registered_device):
        alerts.append(
            DynamicAlert(
                timestamp=datetime.now(UTC),
                device_id=sample.device_id,
                device_name=device_name,
                severity=finding.severity,
                attack_type=finding.attack_type,
                source="rule_engine",
                message=finding.message,
                explanation=f"rule_id={finding.rule_id}; {finding.explanation}",
                reconstruction_error=None,
                threshold=None,
                risk_level=finding.risk_level,
            )
        )
    return alerts


def _evaluate_network_sample(
    sample: NetworkSample,
    device_name: str,
    device_type: str,
) -> list[DynamicAlert]:
    context = feature_adapter.adapt(sample, device_type)
    prediction = ml_runtime.predict_with_context(context.features)
    reconstruction_error = float(prediction["prediction"])
    threshold = float(prediction["threshold"])
    risk_level = str(prediction["risk_level"])
    label = str(prediction["label"])

    if label != "anomaly":
        return []

    reason = "; ".join(context.reasons) if context.reasons else "model detected anomalous CICIoT feature pattern"
    explanation = (
        f"reconstruction_error={reconstruction_error:.6f}; "
        f"threshold={threshold:.6f}; "
        f"risk_level={risk_level}; "
        f"reason: {reason}"
    )
    message = _short_alert_message(context.attack_style, reason)
    return [
        DynamicAlert(
            timestamp=datetime.now(UTC),
            device_id=sample.device_id,
            device_name=device_name,
            severity=risk_level.lower(),
            attack_type=_ml_attack_type(context.attack_style, reason),
            source="ml_autoencoder",
            message=message,
            explanation=explanation,
            reconstruction_error=reconstruction_error,
            threshold=threshold,
            risk_level=risk_level,
        )
    ]


def _ml_attack_type(attack_style: str | None, reason: str) -> str:
    reason_lower = reason.lower()
    if attack_style == "DDoS":
        if "latency anomaly" in reason_lower:
            return "ml_latency_anomaly"
        if "packet-loss anomaly" in reason_lower:
            return "ml_packet_loss_anomaly"
        return "ml_flood_anomaly"
    if attack_style == "syn_flood":
        return "ml_packet_rate_anomaly"
    if attack_style == "port_scan":
        return "ml_connection_fanout_anomaly"
    if attack_style == "arp_spoofing" and "low-value anomaly" in reason_lower:
        return "ml_low_value_anomaly"
    if attack_style == "dns_tunnel" or "traffic volume" in reason_lower:
        return "ml_bandwidth_anomaly"
    return "ml_network_anomaly"


def _short_alert_message(attack_style: str | None, reason: str) -> str:
    reason_lower = reason.lower()
    if attack_style == "DDoS" and "degraded" not in reason_lower:
        if "latency anomaly" in reason_lower:
            return "Latency-only network anomaly detected"
        if "packet-loss anomaly" in reason_lower:
            return "Packet-loss-only network anomaly detected"
        return "Flood-like network anomaly detected"
    if attack_style == "syn_flood":
        return "Packet-rate-only network anomaly detected"
    if attack_style == "port_scan":
        return "Connection-count-only network anomaly detected"
    if attack_style == "arp_spoofing" and "low-value anomaly" in reason_lower:
        return "Low-value-only network anomaly detected"
    if attack_style == "dns_tunnel" or "traffic volume" in reason_lower:
        return "Bandwidth-only traffic anomaly detected"
    if "degraded" in reason_lower or "latency" in reason_lower or "packet_loss" in reason_lower:
        return "Suspicious degraded network state detected"
    return "Unknown anomalous network pattern detected"


def _persist_alerts(db: Session, alerts: list[DynamicAlert]) -> None:
    if not alerts:
        return

    for alert in alerts:
        db.add(
            Alert(
                device_id=alert.device_id,
                alert_type=alert.attack_type,
                severity=alert.severity,
                risk_score=_severity_score(alert.severity),
                reason=alert.explanation or alert.message,
                source=alert.source,
                status="open",
                created_at=alert.timestamp,
            )
        )
    db.commit()


def _process_network_sample(
    sample: NetworkSample,
) -> NetworkSampleResponse:
    from .db.session import SessionLocal, ensure_db_initialized

    ensure_db_initialized()
    db = SessionLocal()
    try:
        _ensure_registered_demo_devices(db)
        device = db.scalar(
            select(RegisteredDevice).where(RegisteredDevice.device_id == sample.device_id)
        )
        device_name = device.device_name if device is not None else "Unknown device"
        device_type = device.device_type if device is not None else "temperature_sensor"
        rule_alerts = _evaluate_rule_sample(
            sample,
            device_name=device_name,
            registered_device=device is not None,
        )
        ml_alerts = _evaluate_network_sample(sample, device_name, device_type)
        alerts = [*rule_alerts, *ml_alerts]
        _persist_alerts(db, alerts)
    finally:
        db.close()

    network_log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "received_at": datetime.now(UTC).isoformat(),
        "sample": sample.model_dump(mode="json"),
        "alerts": [alert.model_dump(mode="json") for alert in alerts],
    }
    with network_log_path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(payload, ensure_ascii=False) + "\n")
    session_alerts.extend(alerts)
    return NetworkSampleResponse(status="accepted", received_sample=sample, alerts=alerts)


@app.post("/api/network/sample", response_model=NetworkSampleResponse)
def receive_network_sample(
    sample: NetworkSample,
    db: Session = Depends(get_db),
) -> NetworkSampleResponse:
    _ensure_registered_demo_devices(db)
    return _process_network_sample(sample)


def _normal_sample_for(device_id: str, timestamp: datetime) -> NetworkSample:
    return NetworkSample(
        timestamp=timestamp,
        device_id=device_id,
        protocol="HTTP",
        bytes_per_second=512.0,
        packets_per_second=0.2,
        connection_count=1,
        latency_ms=12.0,
        packet_loss_percent=0.0,
    )


def _attack_sample_for(device_id: str, timestamp: datetime) -> NetworkSample:
    return NetworkSample(
        timestamp=timestamp,
        device_id=device_id,
        protocol="HTTP",
        bytes_per_second=25000.0,
        packets_per_second=120.0,
        connection_count=80,
        latency_ms=450.0,
        packet_loss_percent=18.0,
    )


def _single_metric_attack_samples_for(
    device_id: str,
    timestamp: datetime,
) -> list[NetworkSample]:
    return [
        NetworkSample(
            timestamp=timestamp,
            device_id=device_id,
            protocol="HTTP",
            bytes_per_second=25000.0,
            packets_per_second=0.2,
            connection_count=1,
            latency_ms=12.0,
            packet_loss_percent=0.0,
        ),
        NetworkSample(
            timestamp=timestamp,
            device_id=device_id,
            protocol="HTTP",
            bytes_per_second=512.0,
            packets_per_second=120.0,
            connection_count=1,
            latency_ms=12.0,
            packet_loss_percent=0.0,
        ),
        NetworkSample(
            timestamp=timestamp,
            device_id=device_id,
            protocol="HTTP",
            bytes_per_second=512.0,
            packets_per_second=0.2,
            connection_count=80,
            latency_ms=12.0,
            packet_loss_percent=0.0,
        ),
        NetworkSample(
            timestamp=timestamp,
            device_id=device_id,
            protocol="HTTP",
            bytes_per_second=512.0,
            packets_per_second=0.2,
            connection_count=1,
            latency_ms=900.0,
            packet_loss_percent=0.0,
        ),
        NetworkSample(
            timestamp=timestamp,
            device_id=device_id,
            protocol="HTTP",
            bytes_per_second=512.0,
            packets_per_second=0.2,
            connection_count=1,
            latency_ms=12.0,
            packet_loss_percent=22.0,
        ),
    ]


DEMO_SCENARIO_PROFILES: dict[str, list[str]] = {
    "dev-001": [
        "normal",
        "packet_rate_spike",
        "latency_spike",
        "bandwidth_spike",
        "packet_loss",
        "low_value",
        "connection_fanout",
    ],
    "dev-002": [
        "normal",
        "connection_fanout",
        "bandwidth_spike",
        "packet_rate_spike",
        "flood",
        "latency_spike",
        "bandwidth_spike",
    ],
    "dev-003": [
        "normal",
        "bandwidth_spike",
        "flood",
        "packet_loss",
        "connection_fanout",
        "bandwidth_spike",
        "flood",
    ],
    "dev-004": [
        "normal",
        "latency_spike",
        "packet_loss",
        "connection_fanout",
        "low_value",
        "packet_rate_spike",
        "connection_fanout",
    ],
    "dev-005": [
        "normal",
        "bandwidth_spike",
        "packet_rate_spike",
        "flood",
        "packet_loss",
        "low_value",
        "flood",
    ],
}


def _profile_sample_for(
    device_id: str,
    timestamp: datetime,
    profile: str,
) -> NetworkSample:
    if profile == "normal":
        return _normal_sample_for(device_id, timestamp)
    if profile == "flood":
        return _attack_sample_for(device_id, timestamp)

    overrides: dict[str, Any] = {
        "bandwidth_spike": {
            "bytes_per_second": 25000.0,
            "packets_per_second": 0.2,
            "connection_count": 1,
            "latency_ms": 12.0,
            "packet_loss_percent": 0.0,
        },
        "packet_rate_spike": {
            "bytes_per_second": 512.0,
            "packets_per_second": 120.0,
            "connection_count": 1,
            "latency_ms": 12.0,
            "packet_loss_percent": 0.0,
        },
        "connection_fanout": {
            "bytes_per_second": 512.0,
            "packets_per_second": 0.2,
            "connection_count": 80,
            "latency_ms": 12.0,
            "packet_loss_percent": 0.0,
        },
        "latency_spike": {
            "bytes_per_second": 512.0,
            "packets_per_second": 0.2,
            "connection_count": 1,
            "latency_ms": 900.0,
            "packet_loss_percent": 0.0,
        },
        "packet_loss": {
            "bytes_per_second": 512.0,
            "packets_per_second": 0.2,
            "connection_count": 1,
            "latency_ms": 12.0,
            "packet_loss_percent": 22.0,
        },
        "low_value": {
            "bytes_per_second": 0.0,
            "packets_per_second": 0.2,
            "connection_count": 1,
            "latency_ms": 12.0,
            "packet_loss_percent": 0.0,
        },
    }.get(profile)
    if overrides is None:
        raise ValueError(f"Unknown demo scenario profile: {profile}")

    return NetworkSample(
        timestamp=timestamp,
        device_id=device_id,
        protocol="HTTP",
        **overrides,
    )


def _demo_scenario_samples(devices: list[RegisteredDevice], now: datetime) -> list[NetworkSample]:
    samples: list[NetworkSample] = []
    for device in devices:
        profiles = DEMO_SCENARIO_PROFILES.get(device.device_id, ["normal", "flood"])
        for offset, profile in enumerate(profiles):
            samples.append(_profile_sample_for(device.device_id, now + timedelta(seconds=offset), profile))

    samples.append(
        NetworkSample(
            timestamp=now + timedelta(seconds=60),
            device_id="rogue-device-001",
            protocol="HTTP",
            bytes_per_second=512.0,
            packets_per_second=0.2,
            connection_count=1,
            latency_ms=12.0,
            packet_loss_percent=0.0,
        )
    )
    return samples


@app.post("/api/demo/scenario", response_model=DemoScenarioResponse)
def run_demo_scenario(db: Session = Depends(get_db)) -> DemoScenarioResponse:
    devices = _ensure_registered_demo_devices(db)
    now = datetime.now(UTC)
    samples = _demo_scenario_samples(devices, now)
    results = [_process_network_sample(sample) for sample in samples]
    alerts_created = sum(len(result.alerts) for result in results)
    return DemoScenarioResponse(
        status="completed",
        samples_sent=len(results),
        alerts_created=alerts_created,
        results=results,
    )


@app.post("/api/demo/device-tests", response_model=DeviceMLTestResponse)
def run_device_ml_tests(db: Session = Depends(get_db)) -> DeviceMLTestResponse:
    devices = _ensure_registered_demo_devices(db)
    now = datetime.now(UTC)
    results: list[DeviceMLTestResult] = []
    for device in devices:
        normal = _process_network_sample(_normal_sample_for(device.device_id, now))
        attack = _process_network_sample(_attack_sample_for(device.device_id, now))
        results.append(
            DeviceMLTestResult(
                device_id=device.device_id,
                device_name=device.device_name,
                normal=normal,
                attack=attack,
            )
        )
    alerts_created = sum(
        len(item.normal.alerts) + len(item.attack.alerts)
        for item in results
    )
    return DeviceMLTestResponse(
        status="completed",
        devices_tested=len(results),
        tests_run=len(results) * 2,
        alerts_created=alerts_created,
        results=results,
    )


@app.get("/api/registered-devices", response_model=list[RegisteredDeviceResponse])
def registered_devices(db: Session = Depends(get_db)) -> list[RegisteredDeviceResponse]:
    _ensure_registered_demo_devices(db)
    devices = db.scalars(select(RegisteredDevice).order_by(RegisteredDevice.device_id)).all()
    return [
        RegisteredDeviceResponse(
            device_id=device.device_id,
            device_name=device.device_name,
            device_type=device.device_type,
            device_mode=device.device_mode,
            ip_address=device.ip_address,
            mac_address=device.mac_address,
        )
        for device in devices
    ]


@app.get("/", response_class=HTMLResponse)
def dashboard_overview(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    summary = _summary(db)
    return templates.TemplateResponse(
        request,
        "overview.html",
        {
            "summary": summary,
            "devices": _registered_device_cards(db),
            "ml_status": ml_runtime.get_status(),
            "model_env_key": "ML_MODEL_PATH",
            "risk_explanations": _risk_explanations(summary),
        },
    )


@app.get("/dashboard/devices", response_class=HTMLResponse)
def dashboard_devices(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "devices.html",
        {"summary": _summary(db), "devices": _registered_device_cards(db)},
    )


@app.get("/dashboard/devices/{device_id}", response_class=HTMLResponse)
def dashboard_device_detail(
    device_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    devices = _registered_device_cards(db)
    device = next((item for item in devices if item["device_id"] == device_id), None)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    detail = {
        "device": device,
        "recent_alerts": [row for row in _alert_rows() if row["device_id"] == device_id],
        "recent_telemetry": [],
    }
    return templates.TemplateResponse(request, "device_detail.html", {"detail": detail})


@app.get("/dashboard/alerts", response_class=HTMLResponse)
def dashboard_alerts(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "alerts.html", {"alerts": _alert_rows()})


@app.get("/api/devices")
def api_devices(
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return _registered_device_cards(db)[:limit]


@app.get("/api/devices/{device_id}")
def api_device(device_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    device = next(
        (item for item in _registered_device_cards(db) if item["device_id"] == device_id),
        None,
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@app.get("/api/alerts")
def api_alerts(limit: int = 200) -> list[dict[str, Any]]:
    return _alert_rows()[:limit]


@app.get("/api/stats/summary")
def api_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    return _summary(db)


@app.get("/api/stats/charts")
def api_charts() -> dict[str, dict[str, int]]:
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    type_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for alert in session_alerts:
        severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
        alert_type = _alert_type_label(alert)
        type_counts[alert_type] = type_counts.get(alert_type, 0) + 1
        source_counts[alert.source] = source_counts.get(alert.source, 0) + 1
    return {
        "alerts_by_severity": severity_counts,
        "alerts_by_type": type_counts,
        "alerts_by_source": source_counts,
    }


@app.post("/api/scan/run")
def scan_run(db: Session = Depends(get_db)) -> dict[str, Any]:
    result = run_demo_scenario(db)
    return {
        "status": result.status,
        "results": [
            f"{result.samples_sent} samples processed",
            f"{result.alerts_created} alerts created",
        ],
    }


@app.get("/api/export/report", response_class=PlainTextResponse)
def export_report(db: Session = Depends(get_db)) -> PlainTextResponse:
    summary = _summary(db)
    lines = [
        "IoT Security Monitoring Report",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Devices: {summary['total_devices']}",
        f"Active alerts: {summary['active_alerts']}",
        "",
        "Alerts:",
    ]
    lines.extend(
        f"- {row['created_at'].isoformat()} {row['device_id']} {row['severity']} {row['reason']}"
        for row in _alert_rows()
    )
    return PlainTextResponse(
        "\n".join(lines),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=iot-security-report.txt"},
    )


@app.post("/api/data/clear", response_model=ClearDataResponse)
def clear_data(db: Session = Depends(get_db)) -> ClearDataResponse:
    deleted_alerts = db.execute(delete(Alert)).rowcount or 0
    deleted_telemetry = db.execute(delete(TelemetryEvent)).rowcount or 0
    deleted_devices = db.execute(delete(Device)).rowcount or 0
    db.commit()
    session_alerts.clear()
    _ensure_registered_demo_devices(db)
    return ClearDataResponse(
        status="cleared",
        deleted_devices=deleted_devices,
        deleted_telemetry_events=deleted_telemetry,
        deleted_alerts=deleted_alerts,
        counts=_counts(db),
    )
