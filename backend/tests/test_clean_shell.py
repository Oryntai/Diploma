from __future__ import annotations

import importlib
import os
import random
import sys
from collections import Counter
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
    assert payload["runtime_components"]["operator_interface"] == "FastAPI web dashboard"
    assert payload["runtime_components"]["desktop_simulator_available"] is True
    assert payload["runtime_components"]["desktop_simulator_module"] == "desktop_simulator.main"
    assert payload["detection_layers"]["deterministic_rule_engine"]["enabled"] is True
    assert payload["detection_layers"]["ml_autoencoder"]["enabled"] is True
    assert payload["experiment"]["dataset"] == "CICIoT2023"
    assert payload["experiment"]["f1_score"] == 0.9925

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
    alerts = attack_response.json()["alerts"]
    sources = {alert["source"] for alert in alerts}
    assert sources == {"ml_autoencoder"}

    alert = alerts[0]
    assert alert["severity"] == "high"
    assert alert["attack_type"] == "ml_flood_anomaly"
    assert alert["source"] == "ml_autoencoder"
    assert alert["risk_level"] == "High"
    assert alert["reconstruction_error"] > alert["threshold"]
    assert alert["message"] == "Flood-like network anomaly detected"
    assert "reconstruction_error=" in alert["explanation"]
    assert "threshold=" in alert["explanation"]

    status = client.get("/api/system/status")
    assert status.json()["counts"] == {
        "registered_devices": 5,
        "runtime_devices": 0,
        "telemetry_events": 0,
        "alerts": len(alerts),
    }

    alert_rows = client.get("/api/alerts").json()
    ml_row = next(row for row in alert_rows if row["source"] == "ml_autoencoder")
    assert ml_row["alert_type"] == "Flood anomaly"
    assert ml_row["raw_alert_type"] == "ml_flood_anomaly"
    assert ml_row["source_label"] == "ML Autoencoder"
    assert ml_row["reason"] == "Flood-like network anomaly detected"
    assert "ML score" in ml_row["details"]

    repeat_response = client.post(
        "/api/network/sample",
        json={
            "timestamp": "2026-05-17T18:35:12+05:00",
            "device_id": "dev-001",
            "protocol": "HTTP",
            "bytes_per_second": 25000.0,
            "packets_per_second": 120.0,
            "connection_count": 80,
            "latency_ms": 450.0,
            "packet_loss_percent": 18.0,
        },
    )
    repeat_alert = repeat_response.json()["alerts"][0]
    assert repeat_alert["source"] == "ml_autoencoder"
    assert repeat_alert["attack_type"] == alert["attack_type"]
    assert repeat_alert["message"] == alert["message"]
    assert repeat_alert["reconstruction_error"] == alert["reconstruction_error"]


def test_rule_engine_only_flags_unregistered_devices(tmp_path: Path) -> None:
    module = load_main_module(sqlite_url(tmp_path / "unknown-device.db"))
    client = TestClient(module.app)

    response = client.post(
        "/api/network/sample",
        json={
            "timestamp": "2026-05-17T14:30:00+05:00",
            "device_id": "rogue-device-001",
            "protocol": "HTTP",
            "bytes_per_second": 512.0,
            "packets_per_second": 0.2,
            "connection_count": 1,
            "latency_ms": 12.0,
            "packet_loss_percent": 0.0,
        },
    )

    assert response.status_code == 200
    alerts = response.json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["source"] == "rule_engine"
    assert alerts[0]["attack_type"] == "unknown_device"
    assert alerts[0]["message"] == "Unregistered IoT device sent traffic"
    alert_rows = client.get("/api/alerts").json()
    assert alert_rows[0]["device_id"] == "rogue-device-001"
    assert alert_rows[0]["device_href"] is None


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
        sources = {alert["source"] for alert in alerts}
        assert sources == {"ml_autoencoder"}, label
        assert alerts[0]["message"] == expected_message


def test_demo_scenario_persists_rule_and_ml_alerts(tmp_path: Path) -> None:
    module = load_main_module(sqlite_url(tmp_path / "scenario.db"))
    client = TestClient(module.app)

    response = client.post("/api/demo/scenario")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["samples_sent"] == 36
    assert payload["alerts_created"] == 31
    assert len(payload["results"]) == 36
    scenario_alerts = [
        alert
        for result in payload["results"]
        for alert in result["alerts"]
    ]
    assert any(alert["source"] == "ml_autoencoder" for alert in scenario_alerts)
    assert any(alert["source"] == "rule_engine" for alert in scenario_alerts)
    assert any(alert["device_id"] == "rogue-device-001" for alert in scenario_alerts)
    assert Counter(alert["severity"] for alert in scenario_alerts) == {
        "high": 19,
        "medium": 9,
        "critical": 3,
    }

    status = client.get("/api/system/status")
    assert status.json()["counts"] == {
        "registered_devices": 5,
        "runtime_devices": 0,
        "telemetry_events": 0,
        "alerts": payload["alerts_created"],
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
        attack_sources = {alert["source"] for alert in item["attack"]["alerts"]}
        assert attack_sources == {"ml_autoencoder"}

    status = client.get("/api/system/status")
    assert status.json()["counts"] == {
        "registered_devices": 5,
        "runtime_devices": 0,
        "telemetry_events": 0,
        "alerts": payload["alerts_created"],
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


def test_desktop_simulator_builds_fastapi_network_samples() -> None:
    from desktop_simulator.api_client import build_url
    from desktop_simulator.presets import (
        DEVICE_TYPES,
        PRESETS,
        DeviceTrafficStream,
        build_custom_network_sample_for_type,
        build_network_sample_for_type,
        build_random_network_sample_for_type,
    )

    assert DEVICE_TYPES["robot_vacuum"] == "dev-005"
    assert "flood" in PRESETS

    normal = build_network_sample_for_type("temperature_sensor", "normal")
    assert normal["device_id"] == "dev-001"
    assert normal["device_type"] == "temperature_sensor"
    assert normal["protocol"] == "HTTP"
    assert normal["bytes_per_second"] == 512.0
    assert normal["packets_per_second"] == 0.2

    flood = build_network_sample_for_type("temperature_sensor", "flood")
    assert flood["bytes_per_second"] == 25_000.0
    assert flood["packets_per_second"] == 120.0
    assert flood["connection_count"] == 80

    custom = build_custom_network_sample_for_type(
        "robot_vacuum",
        {
            "protocol": "mqtt",
            "bytes_per_second": "2048.5",
            "packets_per_second": "3.25",
            "connection_count": "4",
            "latency_ms": "44.5",
            "packet_loss_percent": "1.2",
        },
    )
    assert custom["device_id"] == "dev-005"
    assert custom["device_type"] == "robot_vacuum"
    assert custom["protocol"] == "MQTT"
    assert custom["bytes_per_second"] == 2048.5
    assert custom["packets_per_second"] == 3.25
    assert custom["connection_count"] == 4

    random_sample = build_random_network_sample_for_type(
        "robot_vacuum",
        rng=random.Random(0),
    )
    assert random_sample["device_id"] == "dev-005"
    assert random_sample["device_type"] == "robot_vacuum"
    assert random_sample["random_profile"] == "normal_operation"
    assert random_sample["stream_state"] == "normal"
    assert 0 <= random_sample["packet_loss_percent"] <= 100

    stream = DeviceTrafficStream(
        "ip_camera",
        rng=random.Random(42),
        incident_delay_range=(3, 3),
        incident_duration_range=(2, 2),
    )
    streamed = [stream.next_sample() for _ in range(6)]
    assert [sample["stream_state"] for sample in streamed] == [
        "normal",
        "normal",
        "normal",
        "incident",
        "incident",
        "normal",
    ]
    assert streamed[0]["device_type"] == "ip_camera"
    assert streamed[0]["device_id"] == "dev-003"
    assert streamed[3]["random_profile"] in {
        "bandwidth_spike",
        "packet_loss",
        "latency_spike",
        "flood",
    }
    assert build_url("http://127.0.0.1:8000/", "/api/network/sample") == (
        "http://127.0.0.1:8000/api/network/sample"
    )
