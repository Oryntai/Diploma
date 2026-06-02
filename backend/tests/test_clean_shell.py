from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def load_main_module(database_url: str):
    backend_dir = Path(__file__).resolve().parents[2] / "backend"
    repo_root = Path(__file__).resolve().parents[2]
    for path in (backend_dir, repo_root):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

    os.environ["DATABASE_URL"] = database_url
    os.environ.pop("ML_MODEL_PATH", None)

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name, None)

    return importlib.import_module("app.main")


def test_health_and_status_contract(tmp_path: Path) -> None:
    module = load_main_module(sqlite_url(tmp_path / "clean_shell.db"))
    client = TestClient(module.app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    status = client.get("/api/system/status")
    assert status.status_code == 200
    payload = status.json()
    assert payload["backend_status"] == "ok"
    assert payload["database_ready"] is True
    assert payload["counts"] == {
        "registered_devices": 5,
        "runtime_devices": 0,
        "telemetry_events": 0,
        "alerts": 0,
    }
    assert payload["ml_status"]["model_exists"] is True

    devices = client.get("/api/registered-devices")
    assert devices.status_code == 200
    assert devices.json() == [
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


def test_clear_data_endpoint_is_idempotent(tmp_path: Path) -> None:
    module = load_main_module(sqlite_url(tmp_path / "clear.db"))
    client = TestClient(module.app)

    first = client.post("/api/data/clear")
    second = client.post("/api/data/clear")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["counts"] == {
        "registered_devices": 5,
        "runtime_devices": 0,
        "telemetry_events": 0,
        "alerts": 0,
    }


def test_network_sample_endpoint_accepts_payload(tmp_path: Path) -> None:
    module = load_main_module(sqlite_url(tmp_path / "sample.db"))
    client = TestClient(module.app)

    response = client.post(
        "/api/network/sample",
        json={
            "timestamp": "2026-05-17T14:30:00+05:00",
            "device_id": "dev-001",
            "protocol": "HTTP",
            "bytes_per_second": 512.0,
            "packets_per_second": 0.2,
            "connection_count": 1,
            "latency_ms": 12.0,
            "packet_loss_percent": 0.0,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert response.json()["alerts"] == []

    attack_response = client.post(
        "/api/network/sample",
        json={
            "timestamp": "2026-05-17T17:35:12+05:00",
            "device_id": "dev-001",
            "protocol": "HTTP",
            "bytes_per_second": 25000.0,
            "packets_per_second": 120.0,
            "connection_count": 80,
            "latency_ms": 450.0,
            "packet_loss_percent": 18.0,
        },
    )
    assert attack_response.status_code == 200
    alert = attack_response.json()["alerts"][0]
    assert alert["severity"] == "critical"
    assert alert["attack_type"] == "unknown_device_traffic"
    assert alert["source"] == "ml_autoencoder"
    assert alert["risk_level"] == "Critical"
    assert alert["reconstruction_error"] > alert["threshold"]
    assert alert["message"] == "Flood-like network anomaly detected"
    assert "reconstruction_error=" in alert["explanation"]
    assert "threshold=" in alert["explanation"]

    status = client.get("/api/system/status")
    assert status.json()["counts"] == {
        "registered_devices": 5,
        "runtime_devices": 0,
        "telemetry_events": 0,
        "alerts": 0,
    }


def test_fastapi_dashboard_pages_and_scan(tmp_path: Path) -> None:
    module = load_main_module(sqlite_url(tmp_path / "dashboard.db"))
    client = TestClient(module.app)

    for path in ("/", "/dashboard/devices", "/dashboard/devices/dev-001", "/dashboard/alerts"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "IoT Security Monitoring" in response.text

    scan = client.post("/api/scan/run")
    assert scan.status_code == 200
    assert scan.json()["status"] == "completed"

    summary = client.get("/api/stats/summary")
    assert summary.status_code == 200
    assert summary.json()["total_devices"] == 5
    assert summary.json()["active_alerts"] >= 30

    alerts = client.get("/api/alerts")
    assert alerts.status_code == 200
    assert len(alerts.json()) >= 30


def test_single_metric_attack_pipelines(tmp_path: Path) -> None:
    module = load_main_module(sqlite_url(tmp_path / "single-metric.db"))
    client = TestClient(module.app)

    cases = [
        (
            "bandwidth",
            {
                "bytes_per_second": 25000.0,
                "packets_per_second": 0.2,
                "connection_count": 1,
                "latency_ms": 12.0,
                "packet_loss_percent": 0.0,
            },
            "Bandwidth-only traffic anomaly detected",
        ),
        (
            "packets",
            {
                "bytes_per_second": 512.0,
                "packets_per_second": 120.0,
                "connection_count": 1,
                "latency_ms": 12.0,
                "packet_loss_percent": 0.0,
            },
            "Packet-rate-only network anomaly detected",
        ),
        (
            "connections",
            {
                "bytes_per_second": 512.0,
                "packets_per_second": 0.2,
                "connection_count": 80,
                "latency_ms": 12.0,
                "packet_loss_percent": 0.0,
            },
            "Connection-count-only network anomaly detected",
        ),
        (
            "latency",
            {
                "bytes_per_second": 512.0,
                "packets_per_second": 0.2,
                "connection_count": 1,
                "latency_ms": 900.0,
                "packet_loss_percent": 0.0,
            },
            "Latency-only network anomaly detected",
        ),
        (
            "packet_loss",
            {
                "bytes_per_second": 512.0,
                "packets_per_second": 0.2,
                "connection_count": 1,
                "latency_ms": 12.0,
                "packet_loss_percent": 22.0,
            },
            "Packet-loss-only network anomaly detected",
        ),
        (
            "low_value",
            {
                "bytes_per_second": 0.0,
                "packets_per_second": 0.2,
                "connection_count": 1,
                "latency_ms": 12.0,
                "packet_loss_percent": 0.0,
            },
            "Low-value-only network anomaly detected",
        ),
    ]

    for label, overrides, expected_message in cases:
        response = client.post(
            "/api/network/sample",
            json={
                "timestamp": "2026-05-17T17:35:12+05:00",
                "device_id": "dev-001",
                "protocol": "HTTP",
                **overrides,
            },
        )
        assert response.status_code == 200, label
        alerts = response.json()["alerts"]
        assert len(alerts) == 1, label
        assert alerts[0]["source"] == "ml_autoencoder"
        assert alerts[0]["message"] == expected_message


def test_demo_scenario_produces_session_alerts_without_db_writes(tmp_path: Path) -> None:
    module = load_main_module(sqlite_url(tmp_path / "scenario.db"))
    client = TestClient(module.app)

    response = client.post("/api/demo/scenario")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["samples_sent"] == 35
    assert payload["alerts_created"] >= 30
    assert len(payload["results"]) == 35
    scenario_alerts = [
        alert
        for result in payload["results"]
        for alert in result["alerts"]
    ]
    assert any(alert["source"] == "ml_autoencoder" for alert in scenario_alerts)

    status = client.get("/api/system/status")
    assert status.json()["counts"] == {
        "registered_devices": 5,
        "runtime_devices": 0,
        "telemetry_events": 0,
        "alerts": 0,
    }


def test_device_ml_tests_cover_all_registered_devices(tmp_path: Path) -> None:
    module = load_main_module(sqlite_url(tmp_path / "device-tests.db"))
    client = TestClient(module.app)

    response = client.post("/api/demo/device-tests")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["devices_tested"] == 5
    assert payload["tests_run"] == 10
    assert payload["alerts_created"] >= 5
    assert {item["device_id"] for item in payload["results"]} == {
        "dev-001",
        "dev-002",
        "dev-003",
        "dev-004",
        "dev-005",
    }
    for item in payload["results"]:
        assert item["normal"]["alerts"] == []
        assert len(item["attack"]["alerts"]) >= 1
        assert item["attack"]["alerts"][0]["source"] == "ml_autoencoder"

    status = client.get("/api/system/status")
    assert status.json()["counts"] == {
        "registered_devices": 5,
        "runtime_devices": 0,
        "telemetry_events": 0,
        "alerts": 0,
    }


def test_gitignore_keeps_runtime_artifacts_out_of_git() -> None:
    root = Path(__file__).resolve().parents[2]
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")

    assert ".claude/" in gitignore
    assert ".playwright-mcp/" in gitignore
    assert "logs/*" in gitignore
    assert "!logs/.gitkeep" in gitignore
    assert "reports/*" in gitignore
    assert "!reports/.gitkeep" in gitignore
    assert (root / "logs" / ".gitkeep").is_file()
    assert (root / "reports" / ".gitkeep").is_file()
