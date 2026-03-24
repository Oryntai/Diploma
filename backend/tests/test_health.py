from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def load_app():
    backend_dir = Path(__file__).resolve().parents[2] / "backend"
    backend_dir_str = str(backend_dir)
    if backend_dir_str not in sys.path:
        sys.path.insert(0, backend_dir_str)
    module = importlib.import_module("app.main")
    return module.app


def test_health_endpoint_returns_expected_payload() -> None:
    response = TestClient(load_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "backend",
    }
