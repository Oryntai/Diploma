from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app():
    module_path = Path(__file__).resolve().parents[2] / "backend" / "app" / "main.py"
    spec = importlib.util.spec_from_file_location("backend_app_main", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.app


def test_health_endpoint_returns_expected_payload() -> None:
    response = TestClient(load_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "backend",
    }
