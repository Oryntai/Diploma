from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def load_app(database_url: str):
    backend_dir = Path(__file__).resolve().parents[2] / "backend"
    backend_dir_str = str(backend_dir)
    if backend_dir_str not in sys.path:
        sys.path.insert(0, backend_dir_str)

    os.environ["DATABASE_URL"] = database_url
    os.environ.pop("ML_MODEL_PATH", None)

    module_names = [
        name for name in sys.modules if name == "app" or name.startswith("app.")
    ]
    for name in module_names:
        sys.modules.pop(name, None)

    module = importlib.import_module("app.main")
    return module.app


def test_ingest_creates_device_and_alerts(tmp_path: Path) -> None:
    app = load_app(sqlite_url(tmp_path / "platform_a.db"))
    client = TestClient(app)

    response = client.post(
        "/api/ingest/telemetry",
        json={
            "device_id": "temp-001",
            "device_type": "temperature_sensor",
            "timestamp": "2026-03-21T10:00:00Z",
            "temperature": 85.0,
            "battery": 15,
            "firmware_version": "1.0.2",
            "mode": "abnormal",
        },
    )

    assert response.status_code == 200
    ingest_payload = response.json()
    assert ingest_payload["alerts_created"] >= 3

    devices_payload = client.get("/api/devices").json()
    assert len(devices_payload) == 1
    assert devices_payload[0]["device_id"] == "temp-001"
    assert devices_payload[0]["status"] == "unverified"
    assert devices_payload[0]["risk_score"] >= 30
    assert "recommendation" in devices_payload[0]
    assert len(devices_payload[0]["recommendation"]) > 0
    assert "Verify device identity" in devices_payload[0]["recommendation"]

    alerts_payload = client.get("/api/alerts/recent").json()
    alert_types = {item["alert_type"] for item in alerts_payload}
    assert "impossible_value" in alert_types
    assert "low_battery" in alert_types
    assert "unknown_device" in alert_types


def test_device_detail_and_summary_contract(tmp_path: Path) -> None:
    app = load_app(sqlite_url(tmp_path / "platform_b.db"))
    client = TestClient(app)

    ingest_response = client.post(
        "/api/ingest/telemetry",
        json={
            "device_id": "temp-002",
            "device_type": "temperature_sensor",
            "timestamp": "2026-03-21T10:01:00Z",
            "temperature": 24.1,
            "battery": 93,
            "firmware_version": "1.0.2",
            "mode": "normal",
        },
    )
    assert ingest_response.status_code == 200

    detail_response = client.get("/api/devices/temp-002")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["device"]["device_id"] == "temp-002"
    assert len(detail_payload["recent_telemetry"]) == 1

    summary_response = client.get("/api/stats/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["total_devices"] == 1
    assert summary_payload["online_devices"] == 0
    assert summary_payload["active_alerts"] >= 1
    assert "critical" in summary_payload["alerts_by_severity"]
    assert "high" in summary_payload["alerts_by_severity"]
    assert "medium" in summary_payload["alerts_by_severity"]
    assert "low" in summary_payload["alerts_by_severity"]


def test_flood_rule_generates_message_flood_alert(tmp_path: Path) -> None:
    app = load_app(sqlite_url(tmp_path / "platform_c.db"))
    client = TestClient(app)

    for index in range(20):
        response = client.post(
            "/api/ingest/telemetry",
            json={
                "device_id": "temp-flood-001",
                "device_type": "temperature_sensor",
                "timestamp": f"2026-03-21T10:02:{index:02d}Z",
                "temperature": 24.0,
                "battery": 90,
                "firmware_version": "1.0.2",
                "mode": "normal",
            },
        )
        assert response.status_code == 200

    alerts_payload = client.get("/api/alerts/recent").json()
    alert_types = {item["alert_type"] for item in alerts_payload}
    assert "message_flood" in alert_types


def test_firmware_mismatch_alert(tmp_path: Path) -> None:
    app = load_app(sqlite_url(tmp_path / "platform_fw.db"))
    client = TestClient(app)

    client.post(
        "/api/ingest/telemetry",
        json={
            "device_id": "lock-fw-001",
            "device_type": "smart_door_lock",
            "timestamp": "2026-03-21T10:00:00Z",
            "battery": 90,
            "firmware_version": "1.0.2",
            "mode": "normal",
        },
    )

    response = client.post(
        "/api/ingest/telemetry",
        json={
            "device_id": "lock-fw-001",
            "device_type": "smart_door_lock",
            "timestamp": "2026-03-21T10:01:00Z",
            "battery": 89,
            "firmware_version": "2.0.0-hacked",
            "mode": "normal",
        },
    )
    assert response.status_code == 200

    alerts_payload = client.get("/api/alerts/recent").json()
    fw_alerts = [a for a in alerts_payload if a["alert_type"] == "firmware_mismatch"]
    assert len(fw_alerts) >= 1
    assert "2.0.0-hacked" in fw_alerts[0]["reason"]


def test_smart_plug_ingest(tmp_path: Path) -> None:
    app = load_app(sqlite_url(tmp_path / "platform_plug.db"))
    client = TestClient(app)

    response = client.post(
        "/api/ingest/telemetry",
        json={
            "device_id": "plug-001",
            "device_type": "smart_plug",
            "timestamp": "2026-03-21T10:00:00Z",
            "power_watts": 15.2,
            "voltage": 230.0,
            "is_on": True,
            "battery": 80,
            "firmware_version": "1.0.2",
            "mode": "normal",
        },
    )
    assert response.status_code == 200

    devices = client.get("/api/devices").json()
    assert any(d["device_id"] == "plug-001" for d in devices)


def test_ip_camera_ingest(tmp_path: Path) -> None:
    app = load_app(sqlite_url(tmp_path / "platform_cam.db"))
    client = TestClient(app)

    response = client.post(
        "/api/ingest/telemetry",
        json={
            "device_id": "cam-001",
            "device_type": "ip_camera",
            "timestamp": "2026-03-21T10:00:00Z",
            "fps": 25,
            "resolution": "1080p",
            "stream_active": True,
            "bandwidth_kbps": 2500.0,
            "battery": 70,
            "firmware_version": "1.0.2",
            "mode": "normal",
        },
    )
    assert response.status_code == 200

    devices = client.get("/api/devices").json()
    assert any(d["device_id"] == "cam-001" for d in devices)


def test_smart_door_lock_ingest(tmp_path: Path) -> None:
    app = load_app(sqlite_url(tmp_path / "platform_lock.db"))
    client = TestClient(app)

    response = client.post(
        "/api/ingest/telemetry",
        json={
            "device_id": "lock-001",
            "device_type": "smart_door_lock",
            "timestamp": "2026-03-21T10:00:00Z",
            "lock_state": "locked",
            "access_attempts": 0,
            "battery": 95,
            "firmware_version": "1.0.2",
            "mode": "normal",
        },
    )
    assert response.status_code == 200

    devices = client.get("/api/devices").json()
    assert any(d["device_id"] == "lock-001" for d in devices)


def test_dashboard_html_pages(tmp_path: Path) -> None:
    app = load_app(sqlite_url(tmp_path / "platform_pages.db"))
    client = TestClient(app)

    client.post(
        "/api/ingest/telemetry",
        json={
            "device_id": "page-test-001",
            "device_type": "temperature_sensor",
            "timestamp": "2026-03-21T10:00:00Z",
            "temperature": 22.0,
            "battery": 80,
            "firmware_version": "1.0.2",
            "mode": "normal",
        },
    )

    overview = client.get("/")
    assert overview.status_code == 200
    assert "IoT Security Monitoring" in overview.text

    devices_page = client.get("/dashboard/devices")
    assert devices_page.status_code == 200
    assert "page-test-001" in devices_page.text

    alerts_page = client.get("/dashboard/alerts")
    assert alerts_page.status_code == 200
    assert "All Alerts" in alerts_page.text

    detail_page = client.get("/dashboard/devices/page-test-001")
    assert detail_page.status_code == 200
    assert "page-test-001" in detail_page.text

    not_found = client.get("/dashboard/devices/nonexistent-device")
    assert not_found.status_code == 404
