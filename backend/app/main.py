from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from .core.settings import settings
from .db.session import get_db
from .models.alert import Alert
from .models.device import Device
from .models.telemetry_event import TelemetryEvent
from .schemas.ml import MLPredictRequest, MLPredictResponse, MLStatusResponse
from .services.ml_runtime import MLRuntime
from .services.mqtt_subscriber import MQTTSubscriber
from .services.traffic_features import TrafficFeatureGenerator


class TelemetryIngestRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    device_type: str = Field(min_length=1, max_length=50)
    timestamp: datetime
    topic: str | None = Field(default=None, max_length=255)
    temperature: float | None = None
    battery: int | None = Field(default=None, ge=0, le=100)
    firmware_version: str | None = Field(default=None, max_length=50)
    mode: str | None = Field(default=None, max_length=30)

    model_config = ConfigDict(extra="allow")


class TelemetryIngestResponse(BaseModel):
    saved_event_id: int
    alerts_created: int
    alert_ids: list[int]
    device_status: str


class DeviceSummaryResponse(BaseModel):
    device_id: str
    device_type: str
    status: str
    battery: int | None
    firmware_version: str | None
    last_seen_at: datetime | None
    risk_score: int
    risk_level: str
    main_issue: str
    recommendation: str


class AlertResponse(BaseModel):
    id: int
    device_id: str | None
    alert_type: str
    severity: str
    risk_score: int
    reason: str
    source: str
    status: str
    created_at: datetime


class TelemetryEventResponse(BaseModel):
    id: int
    device_id: str | None
    topic: str
    payload: dict[str, Any]
    received_at: datetime


class DeviceDetailResponse(BaseModel):
    device: DeviceSummaryResponse
    recent_telemetry: list[TelemetryEventResponse]
    recent_alerts: list[AlertResponse]


class SummaryResponse(BaseModel):
    total_devices: int
    online_devices: int
    active_alerts: int
    alerts_last_hour: int
    alerts_by_severity: dict[str, int]
    avg_security_score: float


app = FastAPI(title="IoT Security Monitoring Backend")

app_dir = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(app_dir / "templates"))
app.mount("/static", StaticFiles(directory=str(app_dir / "static")), name="static")

ml_runtime = MLRuntime(model_path=settings.ml_model_path)
traffic_generator = TrafficFeatureGenerator(seed=42)


def _mqtt_ingest_callback(payload_dict: dict) -> None:
    """Called by the MQTT subscriber thread for each valid message."""
    from .db.session import SessionLocal, ensure_db_initialized

    ensure_db_initialized()
    try:
        parsed = TelemetryIngestRequest.model_validate(payload_dict)
    except Exception:
        return

    db = SessionLocal()
    try:
        _ingest_telemetry(db, parsed)
    finally:
        db.close()


mqtt_subscriber = MQTTSubscriber(ingest_callback=_mqtt_ingest_callback)


@app.on_event("startup")
def _start_mqtt() -> None:
    mqtt_subscriber.start()


@app.on_event("shutdown")
def _stop_mqtt() -> None:
    mqtt_subscriber.stop()


def _ml_severity(risk_level: str) -> str:
    return {"Low": "low", "Medium": "medium", "High": "high", "Critical": "critical"}.get(
        risk_level, "medium"
    )


def _ml_risk_score(error: float, threshold: float) -> int:
    ratio = error / threshold if threshold > 0 else 0
    if ratio < 1.0:
        return 10
    if ratio < 2.0:
        return 40
    if ratio < 4.0:
        return 65
    return 85


def _default_topic(payload: TelemetryIngestRequest) -> str:
    return f"iot/devices/{payload.device_type}/{payload.device_id}/telemetry"


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _decode_payload(payload_json: str) -> dict[str, object]:
    try:
        decoded = json.loads(payload_json)
    except json.JSONDecodeError:
        return {}

    if isinstance(decoded, dict):
        return decoded
    return {}


def _risk_level(risk_score: int) -> str:
    if risk_score >= 70:
        return "Critical"
    if risk_score >= 50:
        return "High"
    if risk_score >= 25:
        return "Medium"
    return "Low"


def _current_device_risk_map(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Alert.device_id, func.max(Alert.risk_score))
        .where(Alert.status == "open", Alert.device_id.is_not(None))
        .group_by(Alert.device_id)
    ).all()
    return {
        str(device_id): int(max_score or 0)
        for device_id, max_score in rows
        if device_id is not None
    }


def _current_device_issue_map(db: Session) -> dict[str, str]:
    rows = db.execute(
        select(Alert.device_id, Alert.reason)
        .where(Alert.status == "open", Alert.device_id.is_not(None))
        .order_by(desc(Alert.created_at))
    ).all()

    issues: dict[str, str] = {}
    for device_id, reason in rows:
        if device_id is None:
            continue
        if device_id not in issues:
            issues[str(device_id)] = reason
    return issues


def _current_device_alert_type_map(db: Session) -> dict[str, str]:
    rows = db.execute(
        select(Alert.device_id, Alert.alert_type)
        .where(Alert.status == "open", Alert.device_id.is_not(None))
        .order_by(desc(Alert.created_at))
    ).all()

    alert_types: dict[str, str] = {}
    for device_id, alert_type in rows:
        if device_id is None:
            continue
        key = str(device_id)
        if key not in alert_types:
            alert_types[key] = alert_type
    return alert_types


def _recommendation_for_device(
    *,
    status: str,
    risk_level: str,
    alert_type: str | None,
) -> str:
    if status == "unverified":
        return "Verify device identity and approve only if source is trusted."

    recommendation_by_alert = {
        "unknown_device": "Validate device identity before allowing trusted telemetry.",
        "impossible_value": "Check sensor integrity and isolate device until values normalize.",
        "low_battery": "Recharge or replace battery and monitor stability.",
        "message_flood": "Throttle telemetry rate and inspect firmware or adapter loop.",
        "firmware_mismatch": "Verify firmware integrity and compare hash against known good version.",
        "ml_anomaly": "ML model detected anomalous traffic. Investigate network behavior and isolate if confirmed.",
    }
    if alert_type in recommendation_by_alert:
        return recommendation_by_alert[alert_type]

    if risk_level == "Critical":
        return "Escalate immediately and contain affected device communication."
    if risk_level == "High":
        return "Investigate now and confirm root cause with recent telemetry."
    if risk_level == "Medium":
        return "Schedule operator check and watch the next telemetry cycle."
    return "No urgent action required, continue baseline monitoring."


def _latest_battery_for_device(db: Session, device_id: str) -> int | None:
    latest_event = db.scalar(
        select(TelemetryEvent)
        .where(TelemetryEvent.device_id == device_id)
        .order_by(desc(TelemetryEvent.received_at))
        .limit(1)
    )
    if latest_event is None:
        return None

    decoded_payload = _decode_payload(latest_event.payload_json)
    battery = decoded_payload.get("battery")
    if isinstance(battery, int):
        return battery
    return None


def _to_alert_response(alert: Alert) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        device_id=alert.device_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        risk_score=alert.risk_score,
        reason=alert.reason,
        source=alert.source,
        status=alert.status,
        created_at=alert.created_at,
    )


def _to_device_summary(
    db: Session,
    device: Device,
    risk_map: dict[str, int],
    issue_map: dict[str, str],
    alert_type_map: dict[str, str],
) -> DeviceSummaryResponse:
    risk_score = risk_map.get(device.device_id, 0)
    risk_level = _risk_level(risk_score)
    main_issue = issue_map.get(device.device_id, "None")
    alert_type = alert_type_map.get(device.device_id)
    battery = _latest_battery_for_device(db, device.device_id)
    return DeviceSummaryResponse(
        device_id=device.device_id,
        device_type=device.device_type,
        status=device.status,
        battery=battery,
        firmware_version=device.firmware_version,
        last_seen_at=device.last_seen_at,
        risk_score=risk_score,
        risk_level=risk_level,
        main_issue=main_issue,
        recommendation=_recommendation_for_device(
            status=device.status,
            risk_level=risk_level,
            alert_type=alert_type,
        ),
    )


def _evaluate_telemetry_rules(
    db: Session,
    payload: TelemetryIngestRequest,
    existing_device: Device | None = None,
) -> list[Alert]:
    alerts: list[Alert] = []

    if payload.temperature is not None and (
        payload.temperature < settings.min_temperature_c
        or payload.temperature > settings.max_temperature_c
    ):
        alerts.append(
            Alert(
                device_id=payload.device_id,
                alert_type="impossible_value",
                severity="high",
                risk_score=50,
                reason=(
                    "Temperature value is out of accepted range: "
                    f"{payload.temperature}C (allowed "
                    f"{settings.min_temperature_c}C..{settings.max_temperature_c}C)."
                ),
                source="rule_engine",
            )
        )

    if payload.battery is not None and payload.battery < settings.low_battery_threshold:
        alerts.append(
            Alert(
                device_id=payload.device_id,
                alert_type="low_battery",
                severity="medium",
                risk_score=30,
                reason=(
                    "Battery dropped below threshold: "
                    f"{payload.battery}% < {settings.low_battery_threshold}%."
                ),
                source="rule_engine",
            )
        )

    flood_window_start = datetime.now(UTC) - timedelta(
        seconds=settings.flood_window_seconds
    )
    events_in_window = db.scalar(
        select(func.count(TelemetryEvent.id)).where(
            TelemetryEvent.device_id == payload.device_id,
            TelemetryEvent.received_at >= flood_window_start,
        )
    )
    existing_flood_alert = db.scalar(
        select(Alert.id).where(
            Alert.device_id == payload.device_id,
            Alert.alert_type == "message_flood",
            Alert.created_at >= flood_window_start,
        )
    )

    if (
        int(events_in_window or 0) >= settings.flood_threshold
        and existing_flood_alert is None
    ):
        alerts.append(
            Alert(
                device_id=payload.device_id,
                alert_type="message_flood",
                severity="medium",
                risk_score=30,
                reason=(
                    "Telemetry flood detected: "
                    f"{int(events_in_window or 0)} messages in "
                    f"{settings.flood_window_seconds}s window."
                ),
                source="rule_engine",
            )
        )

    if (
        payload.firmware_version is not None
        and existing_device is not None
        and existing_device.firmware_version is not None
        and payload.firmware_version != existing_device.firmware_version
    ):
        alerts.append(
            Alert(
                device_id=payload.device_id,
                alert_type="firmware_mismatch",
                severity="high",
                risk_score=60,
                reason=(
                    f"Firmware version changed unexpectedly: "
                    f"'{existing_device.firmware_version}' -> "
                    f"'{payload.firmware_version}'. "
                    f"Possible unauthorized update or device spoofing."
                ),
                source="rule_engine",
            )
        )

    return alerts


def _ingest_telemetry(
    db: Session, payload: TelemetryIngestRequest
) -> TelemetryIngestResponse:
    normalized_ts = _normalize_timestamp(payload.timestamp)
    existing_device = db.scalar(
        select(Device).where(Device.device_id == payload.device_id)
    )
    generated_alerts: list[Alert] = []

    if existing_device is None:
        existing_device = Device(
            device_id=payload.device_id,
            device_type=payload.device_type,
            status="unverified",
            firmware_version=payload.firmware_version,
            last_seen_at=normalized_ts,
        )
        db.add(existing_device)
        generated_alerts.append(
            Alert(
                device_id=payload.device_id,
                alert_type="unknown_device",
                severity="high",
                risk_score=50,
                reason=(
                    "First-seen device is marked unverified. "
                    "Review identity before treating as trusted."
                ),
                source="rule_engine",
            )
        )
    else:
        existing_device.device_type = payload.device_type
        if existing_device.status != "unverified":
            existing_device.status = "online"
        current_last_seen = existing_device.last_seen_at
        if current_last_seen is not None and current_last_seen.tzinfo is None:
            current_last_seen = current_last_seen.replace(tzinfo=UTC)
        if current_last_seen is None or normalized_ts >= current_last_seen:
            existing_device.last_seen_at = normalized_ts

    payload_json = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False)
    telemetry_event = TelemetryEvent(
        device_id=payload.device_id,
        topic=payload.topic or _default_topic(payload),
        payload_json=payload_json,
    )
    db.add(telemetry_event)
    db.flush()

    generated_alerts.extend(
        _evaluate_telemetry_rules(db, payload, existing_device=existing_device)
    )

    if existing_device is not None and payload.firmware_version:
        existing_device.firmware_version = payload.firmware_version

    if ml_runtime.get_status().get("ready_for_inference"):
        try:
            features = traffic_generator.generate(
                device_type=payload.device_type,
                mode=payload.mode or "normal",
            )
            result = ml_runtime.predict_with_context(features)
            if result.get("label") == "anomaly":
                generated_alerts.append(
                    Alert(
                        device_id=payload.device_id,
                        alert_type="ml_anomaly",
                        severity=_ml_severity(result.get("risk_level", "Medium")),
                        risk_score=_ml_risk_score(
                            result["prediction"], result.get("threshold", 0.048)
                        ),
                        reason=(
                            f"ML model detected anomalous network behavior. "
                            f"Reconstruction error: {result['prediction']:.6f} "
                            f"(threshold: {result.get('threshold', 0.048):.6f}). "
                            f"Risk level: {result.get('risk_level', 'Unknown')}."
                        ),
                        source="ml_model",
                    )
                )
        except Exception:
            pass

    for alert in generated_alerts:
        db.add(alert)

    db.commit()
    db.refresh(telemetry_event)

    alert_ids: list[int] = []
    for alert in generated_alerts:
        db.refresh(alert)
        alert_ids.append(alert.id)

    return TelemetryIngestResponse(
        saved_event_id=telemetry_event.id,
        alerts_created=len(generated_alerts),
        alert_ids=alert_ids,
        device_status=existing_device.status,
    )


def _list_devices(db: Session, limit: int = 100) -> list[DeviceSummaryResponse]:
    devices = db.scalars(
        select(Device)
        .order_by(desc(Device.last_seen_at), Device.device_id)
        .limit(limit)
    ).all()
    risk_map = _current_device_risk_map(db)
    issue_map = _current_device_issue_map(db)
    alert_type_map = _current_device_alert_type_map(db)
    return [
        _to_device_summary(db, item, risk_map, issue_map, alert_type_map)
        for item in devices
    ]


def _list_alerts(db: Session, limit: int = 100) -> list[AlertResponse]:
    alerts = db.scalars(
        select(Alert).order_by(desc(Alert.created_at)).limit(limit)
    ).all()
    return [_to_alert_response(alert) for alert in alerts]


def _get_device_detail(
    db: Session,
    device_id: str,
    telemetry_limit: int = 20,
    alerts_limit: int = 20,
) -> DeviceDetailResponse | None:
    device = db.scalar(select(Device).where(Device.device_id == device_id))
    if device is None:
        return None

    risk_map = _current_device_risk_map(db)
    issue_map = _current_device_issue_map(db)
    alert_type_map = _current_device_alert_type_map(db)
    device_response = _to_device_summary(
        db,
        device,
        risk_map,
        issue_map,
        alert_type_map,
    )

    recent_events = db.scalars(
        select(TelemetryEvent)
        .where(TelemetryEvent.device_id == device_id)
        .order_by(desc(TelemetryEvent.received_at))
        .limit(telemetry_limit)
    ).all()
    recent_alerts = db.scalars(
        select(Alert)
        .where(Alert.device_id == device_id)
        .order_by(desc(Alert.created_at))
        .limit(alerts_limit)
    ).all()

    return DeviceDetailResponse(
        device=device_response,
        recent_telemetry=[
            TelemetryEventResponse(
                id=event.id,
                device_id=event.device_id,
                topic=event.topic,
                payload=_decode_payload(event.payload_json),
                received_at=event.received_at,
            )
            for event in recent_events
        ],
        recent_alerts=[_to_alert_response(alert) for alert in recent_alerts],
    )


def _get_summary(db: Session) -> SummaryResponse:
    total_devices = int(db.scalar(select(func.count(Device.id))) or 0)
    online_devices = int(
        db.scalar(select(func.count(Device.id)).where(Device.status == "online")) or 0
    )
    active_alerts = int(
        db.scalar(select(func.count(Alert.id)).where(Alert.status == "open")) or 0
    )

    last_hour_border = datetime.now(UTC) - timedelta(hours=1)
    alerts_last_hour = int(
        db.scalar(
            select(func.count(Alert.id)).where(Alert.created_at >= last_hour_border)
        )
        or 0
    )

    severity_rows = db.execute(
        select(Alert.severity, func.count(Alert.id))
        .where(Alert.status == "open")
        .group_by(Alert.severity)
    ).all()
    alerts_by_severity = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    for severity, count in severity_rows:
        severity_key = str(severity).lower()
        if severity_key in alerts_by_severity:
            alerts_by_severity[severity_key] = int(count)

    risk_map = _current_device_risk_map(db)
    all_device_ids = db.scalars(select(Device.device_id)).all()
    if not all_device_ids:
        avg_security_score = 100.0
    else:
        average_risk = sum(
            risk_map.get(device_id, 0) for device_id in all_device_ids
        ) / len(all_device_ids)
        avg_security_score = round(max(0.0, 100.0 - average_risk), 1)

    return SummaryResponse(
        total_devices=total_devices,
        online_devices=online_devices,
        active_alerts=active_alerts,
        alerts_last_hour=alerts_last_hour,
        alerts_by_severity=alerts_by_severity,
        avg_security_score=avg_security_score,
    )


def _build_risk_explanations(
    db: Session,
    alerts_by_severity: dict[str, int],
) -> dict[str, dict[str, Any]]:
    base_explanations: dict[str, dict[str, Any]] = {
        "critical": {
            "label": "Critical",
            "score_range": "70-100 risk points",
            "class_description": (
                "Highest urgency class. Indicates immediate compromise risk or "
                "multiple severe signals that need incident response now."
            ),
            "typical_causes": [
                "Device spoofing combined with repeated suspicious telemetry",
                "Multiple high-impact alerts from one device in short time",
                "Escalation from unresolved high-severity incidents",
            ],
        },
        "high": {
            "label": "High",
            "score_range": "50-69 risk points",
            "class_description": (
                "Strong indicator of abnormal or potentially malicious behavior. "
                "Needs prompt investigation and mitigation."
            ),
            "typical_causes": [
                "Impossible sensor values outside allowed bounds",
                "Unknown/unverified device identity",
                "Behavior inconsistent with baseline for this device type",
            ],
        },
        "medium": {
            "label": "Medium",
            "score_range": "25-49 risk points",
            "class_description": (
                "Not immediately critical, but suspicious enough to track closely "
                "and validate against expected device behavior."
            ),
            "typical_causes": [
                "Message flood exceeding configured rate window",
                "Battery or operational degradation affecting reliability",
                "Repeated warning-pattern events without hard failure",
            ],
        },
        "low": {
            "label": "Low",
            "score_range": "0-24 risk points",
            "class_description": (
                "Minor anomalies or informational deviations. Usually safe to monitor "
                "without urgent response."
            ),
            "typical_causes": [
                "Transient fluctuations that remain inside expected limits",
                "Single low-impact warning without recurrence",
                "Background telemetry noise from unstable environment",
            ],
        },
    }

    explanations: dict[str, dict[str, Any]] = {}
    for severity, metadata in base_explanations.items():
        rows = db.execute(
            select(Alert.device_id, Alert.reason)
            .where(Alert.status == "open", func.lower(Alert.severity) == severity)
            .order_by(desc(Alert.created_at))
            .limit(5)
        ).all()

        current_reasons: list[str] = []
        seen: set[str] = set()
        for device_id, reason in rows:
            reason_text = f"{device_id}: {reason}" if device_id else reason
            if reason_text not in seen:
                current_reasons.append(reason_text)
                seen.add(reason_text)

        current_count = int(alerts_by_severity.get(severity, 0))
        if current_count > 0:
            why_now = (
                f"{current_count} open alert(s) are currently mapped to "
                f"{metadata['label']} severity."
            )
        else:
            why_now = "No open alerts in this class right now."

        explanations[severity] = {
            **metadata,
            "current_count": current_count,
            "why_now": why_now,
            "current_reasons": current_reasons,
        }

    return explanations


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "backend",
    }


@app.get("/", response_class=HTMLResponse)
def overview(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    summary = _get_summary(db)
    devices = _list_devices(db, limit=12)
    risk_explanations = _build_risk_explanations(db, summary.alerts_by_severity)
    status = ml_runtime.get_status()

    return templates.TemplateResponse(
        request=request,
        name="overview.html",
        context={
            "ml_status": status,
            "model_env_key": "ML_MODEL_PATH",
            "summary": summary,
            "devices": devices,
            "risk_explanations": risk_explanations,
        },
    )


@app.get("/dashboard/devices", response_class=HTMLResponse)
def dashboard_devices(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    summary = _get_summary(db)
    devices = _list_devices(db, limit=200)
    return templates.TemplateResponse(
        request=request,
        name="devices.html",
        context={"summary": summary, "devices": devices},
    )


@app.get("/dashboard/alerts", response_class=HTMLResponse)
def dashboard_alerts(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    alerts = _list_alerts(db, limit=200)
    return templates.TemplateResponse(
        request=request,
        name="alerts.html",
        context={"alerts": alerts},
    )


@app.get("/dashboard/devices/{device_id}", response_class=HTMLResponse)
def dashboard_device_detail(
    request: Request, device_id: str, db: Session = Depends(get_db)
) -> HTMLResponse:
    detail = _get_device_detail(db, device_id=device_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return templates.TemplateResponse(
        request=request,
        name="device_detail.html",
        context={"detail": detail},
    )


@app.post("/api/ingest/telemetry", response_model=TelemetryIngestResponse)
def ingest_telemetry_route(
    payload: TelemetryIngestRequest,
    db: Session = Depends(get_db),
) -> TelemetryIngestResponse:
    return _ingest_telemetry(db, payload)


@app.get("/api/devices", response_model=list[DeviceSummaryResponse])
def devices(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[DeviceSummaryResponse]:
    return _list_devices(db, limit=limit)


@app.get("/api/devices/{device_id}", response_model=DeviceDetailResponse)
def device_detail(
    device_id: str,
    telemetry_limit: int = Query(default=20, ge=1, le=200),
    alerts_limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> DeviceDetailResponse:
    response = _get_device_detail(
        db,
        device_id=device_id,
        telemetry_limit=telemetry_limit,
        alerts_limit=alerts_limit,
    )
    if response is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return response


@app.get("/api/alerts", response_model=list[AlertResponse])
def alerts(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[AlertResponse]:
    return _list_alerts(db, limit=limit)


@app.get("/api/alerts/recent", response_model=list[AlertResponse])
def recent_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[AlertResponse]:
    return _list_alerts(db, limit=limit)


@app.get("/api/stats/summary", response_model=SummaryResponse)
def stats_summary(db: Session = Depends(get_db)) -> SummaryResponse:
    return _get_summary(db)


@app.get("/api/ml/status", response_model=MLStatusResponse)
def ml_status() -> MLStatusResponse:
    return MLStatusResponse.model_validate(ml_runtime.get_status())


@app.post("/api/ml/predict", response_model=MLPredictResponse)
def ml_predict(payload: MLPredictRequest) -> MLPredictResponse:
    try:
        prediction_payload = ml_runtime.predict_with_context(payload.features)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MLPredictResponse(
        prediction=float(prediction_payload["prediction"]),
        model_format=ml_runtime.model_format,
        model_path=str(ml_runtime.model_path),
        threshold=prediction_payload.get("threshold"),
        label=prediction_payload.get("label"),
        risk_level=prediction_payload.get("risk_level"),
    )
