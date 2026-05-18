from __future__ import annotations

import json
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI
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
network_log_path = Path(__file__).resolve().parents[2] / "logs" / "network_samples.log"

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


app = FastAPI(title="IoT Security Monitoring Backend", lifespan=lifespan)


def _counts(db: Session) -> CountsResponse:
    return CountsResponse(
        registered_devices=int(db.scalar(select(func.count(RegisteredDevice.id))) or 0),
        runtime_devices=int(db.scalar(select(func.count(Device.id))) or 0),
        telemetry_events=int(db.scalar(select(func.count(TelemetryEvent.id))) or 0),
        alerts=int(db.scalar(select(func.count(Alert.id))) or 0),
    )


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
    )


@app.get("/api/ml/status")
def ml_status() -> dict[str, Any]:
    return ml_runtime.get_status()


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
            attack_type="unknown_device_traffic",
            source="ml_autoencoder",
            message=message,
            explanation=explanation,
            reconstruction_error=reconstruction_error,
            threshold=threshold,
            risk_level=risk_level,
        )
    ]


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
    finally:
        db.close()

    alerts = _evaluate_network_sample(sample, device_name, device_type)
    network_log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "received_at": datetime.now(UTC).isoformat(),
        "sample": sample.model_dump(mode="json"),
        "alerts": [alert.model_dump(mode="json") for alert in alerts],
    }
    with network_log_path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(payload, ensure_ascii=False) + "\n")
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


@app.post("/api/demo/scenario", response_model=DemoScenarioResponse)
def run_demo_scenario(db: Session = Depends(get_db)) -> DemoScenarioResponse:
    devices = _ensure_registered_demo_devices(db)
    now = datetime.now(UTC)
    samples = []
    for device in devices:
        samples.append(_normal_sample_for(device.device_id, now))
        samples.append(_attack_sample_for(device.device_id, now))
        samples.extend(_single_metric_attack_samples_for(device.device_id, now))
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


@app.post("/api/data/clear", response_model=ClearDataResponse)
def clear_data(db: Session = Depends(get_db)) -> ClearDataResponse:
    deleted_alerts = db.execute(delete(Alert)).rowcount or 0
    deleted_telemetry = db.execute(delete(TelemetryEvent)).rowcount or 0
    deleted_devices = db.execute(delete(Device)).rowcount or 0
    db.commit()
    _ensure_registered_demo_devices(db)
    return ClearDataResponse(
        status="cleared",
        deleted_devices=deleted_devices,
        deleted_telemetry_events=deleted_telemetry,
        deleted_alerts=deleted_alerts,
        counts=_counts(db),
    )
