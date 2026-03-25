from __future__ import annotations

import importlib
import os
import pickle
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class StubModel:
    def predict(self, rows: list[list[float]]) -> list[float]:
        return [sum(rows[0])]


def load_app(model_path: str | None = None):
    backend_dir = Path(__file__).resolve().parents[2] / "backend"
    backend_dir_str = str(backend_dir)
    if backend_dir_str not in sys.path:
        sys.path.insert(0, backend_dir_str)

    if model_path is None:
        os.environ.pop("ML_MODEL_PATH", None)
    else:
        os.environ["ML_MODEL_PATH"] = model_path

    for module_name in [
        "app.main",
        "app.core.settings",
        "app.services.ml_runtime",
        "app.schemas.ml",
    ]:
        sys.modules.pop(module_name, None)

    module = importlib.import_module("app.main")
    return module.app


def test_overview_page_is_available() -> None:
    response = TestClient(load_app()).get("/")

    assert response.status_code == 200
    assert "IoT Security Monitoring Platform" in response.text
    assert "ML Integration Readiness" in response.text
    assert "Risk Class Details" in response.text
    assert "Why this class is active" in response.text
    assert "risk-explanations-data" in response.text
    assert "Inspect recent high-severity alerts" not in response.text
    assert "Recent Security Alerts" not in response.text
    assert "System Flow" not in response.text


def test_ml_status_reports_model_path_and_flags() -> None:
    response = TestClient(load_app()).get("/api/ml/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_path"].endswith("best_autoencoder_ciciot23.pt")
    assert isinstance(payload["model_exists"], bool)
    assert isinstance(payload["model_loaded"], bool)


def test_ml_predict_with_wrong_feature_count_returns_error() -> None:
    response = TestClient(load_app()).post(
        "/api/ml/predict",
        json={"features": [0.1, 0.2, 0.3]},
    )

    assert response.status_code in (400, 503)


def test_ml_predict_with_stub_model_returns_prediction(tmp_path: Path) -> None:
    model_path = tmp_path / "stub_model.pkl"
    with model_path.open("wb") as model_file:
        pickle.dump(StubModel(), model_file)

    response = TestClient(load_app(str(model_path))).post(
        "/api/ml/predict",
        json={"features": [0.1, 0.2, 0.3]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["prediction"] == pytest.approx(0.6)
    assert payload["model_format"] == "pickle"


def test_ml_status_for_onnx_is_not_ready_for_inference(tmp_path: Path) -> None:
    onnx_path = tmp_path / "model.onnx"
    onnx_path.write_bytes(b"placeholder")

    response = TestClient(load_app(str(onnx_path))).get("/api/ml/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_exists"] is True
    assert payload["model_format"] == "onnx"
    assert payload["ready_for_inference"] is False
