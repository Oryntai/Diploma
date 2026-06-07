from __future__ import annotations

import json
import pickle
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


class MLRuntime:
    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path
        self._loaded_model: Any | None = None
        self._load_lock = threading.Lock()

    @property
    def model_format(self) -> str:
        suffix = self.model_path.suffix.lower()
        if suffix in {".joblib"}:
            return "joblib"
        if suffix in {".pkl", ".pickle"}:
            return "pickle"
        if suffix in {".pt", ".pth"}:
            return "torch_autoencoder"
        if suffix == ".onnx":
            return "onnx"
        return "unknown"

    def _bundle_paths(self) -> dict[str, Path]:
        base_dir = self.model_path.parent

        def _pick(candidates: list[str]) -> Path:
            for candidate in candidates:
                path = base_dir / candidate
                if path.is_file():
                    return path
            return base_dir / candidates[0]

        return {
            "scaler": _pick(["scaler_ciciot23.pkl", "scaler.pkl"]),
            "features": _pick(
                ["features_ciciot23.json", "features_if_ciciot23.json", "features.json"]
            ),
            "threshold": _pick(["threshold_ciciot23.json", "threshold.json"]),
        }

    def get_status(self) -> dict[str, str | bool | float | int | None]:
        model_exists = self.model_path.is_file()
        model_loaded = self._loaded_model is not None
        model_format = self.model_format
        threshold: float | None = None
        feature_count: int | None = None

        ready = model_exists and model_format in {"joblib", "pickle"}
        if model_exists and model_format == "torch_autoencoder":
            bundle = self._bundle_paths()
            ready = all(path.is_file() for path in bundle.values())
            if bundle["threshold"].is_file():
                try:
                    with bundle["threshold"].open("r", encoding="utf-8") as file_obj:
                        threshold = float(json.load(file_obj)["threshold"])
                except Exception:
                    threshold = None
            if bundle["features"].is_file():
                try:
                    with bundle["features"].open("r", encoding="utf-8") as file_obj:
                        features = json.load(file_obj)
                    if isinstance(features, list):
                        feature_count = len(features)
                except Exception:
                    feature_count = None

        detail = "Model file is missing. Place trained artifact at configured path."
        if model_exists:
            detail = "Model file found. Ready to load for inference."

        if model_exists and model_format == "torch_autoencoder":
            bundle = self._bundle_paths()
            missing = [name for name, path in bundle.items() if not path.is_file()]
            if missing:
                detail = (
                    "PyTorch model found, but companion artifacts are missing: "
                    + ", ".join(missing)
                )
            else:
                detail = (
                    "PyTorch autoencoder bundle found. Ready for anomaly scoring "
                    "inference."
                )

        if model_loaded:
            detail = "Model is loaded and ready for inference."

        return {
            "model_path": str(self.model_path),
            "model_exists": model_exists,
            "model_format": model_format,
            "model_loaded": model_loaded,
            "ready_for_inference": ready,
            "threshold": threshold,
            "feature_count": feature_count,
            "detail": detail,
        }

    def _load_torch_dependencies(self) -> tuple[Any, Any, Any]:
        try:
            import joblib
            import numpy as np
            import torch
        except ImportError as exc:
            raise RuntimeError(
                "PyTorch inference requires numpy, joblib and torch packages."
            ) from exc

        return np, torch, joblib

    def _load_torch_autoencoder_bundle(self) -> dict[str, Any]:
        bundle_paths = self._bundle_paths()
        missing = [name for name, path in bundle_paths.items() if not path.is_file()]
        if missing:
            raise RuntimeError(
                "Companion artifacts are missing for PyTorch autoencoder: "
                + ", ".join(missing)
            )

        np, torch, joblib = self._load_torch_dependencies()

        try:
            with bundle_paths["features"].open("r", encoding="utf-8") as file_obj:
                feature_cols = json.load(file_obj)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Failed to read features file: {bundle_paths['features']}"
            ) from exc

        if not isinstance(feature_cols, list) or not feature_cols:
            raise RuntimeError("Features file must contain a non-empty list.")

        try:
            with bundle_paths["threshold"].open("r", encoding="utf-8") as file_obj:
                threshold_payload = json.load(file_obj)
            threshold = float(threshold_payload["threshold"])
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Failed to read threshold file: {bundle_paths['threshold']}"
            ) from exc

        try:
            scaler = joblib.load(bundle_paths["scaler"])
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Failed to load scaler artifact: {bundle_paths['scaler']}"
            ) from exc

        class Autoencoder(torch.nn.Module):
            def __init__(self, input_dim: int) -> None:
                super().__init__()
                self.encoder = torch.nn.Sequential(
                    torch.nn.Linear(input_dim, 128),
                    torch.nn.ReLU(),
                    torch.nn.Linear(128, 64),
                    torch.nn.ReLU(),
                    torch.nn.Linear(64, 32),
                    torch.nn.ReLU(),
                    torch.nn.Linear(32, 16),
                )
                self.decoder = torch.nn.Sequential(
                    torch.nn.Linear(16, 32),
                    torch.nn.ReLU(),
                    torch.nn.Linear(32, 64),
                    torch.nn.ReLU(),
                    torch.nn.Linear(64, 128),
                    torch.nn.ReLU(),
                    torch.nn.Linear(128, input_dim),
                )

            def forward(self, values: Any) -> Any:
                encoded = self.encoder(values)
                return self.decoder(encoded)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = Autoencoder(len(feature_cols)).to(device)
        try:
            state_dict = torch.load(self.model_path, map_location=device)
            model.load_state_dict(state_dict)
            model.eval()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Failed to load PyTorch model artifact: {self.model_path}"
            ) from exc

        return {
            "kind": "torch_autoencoder",
            "model": model,
            "device": device,
            "np": np,
            "torch": torch,
            "feature_cols": feature_cols,
            "scaler": scaler,
            "threshold": threshold,
        }

    def _ensure_loaded(self) -> None:
        if self._loaded_model is not None:
            return

        with self._load_lock:
            if self._loaded_model is not None:
                return

            if not self.model_path.is_file():
                raise FileNotFoundError(
                    f"Trained model file is not found: {self.model_path}"
                )

            if self.model_format == "joblib":
                try:
                    import joblib
                except ImportError as exc:
                    raise RuntimeError(
                        "joblib is not installed. Add joblib to requirements."
                    ) from exc
                try:
                    self._loaded_model = joblib.load(self.model_path)
                except Exception as exc:  # noqa: BLE001
                    raise RuntimeError(
                        f"Failed to load joblib model artifact: {self.model_path}"
                    ) from exc
                return

            if self.model_format == "pickle":
                try:
                    with self.model_path.open("rb") as model_file:
                        self._loaded_model = pickle.load(model_file)
                except Exception as exc:  # noqa: BLE001
                    raise RuntimeError(
                        f"Failed to load pickle model artifact: {self.model_path}"
                    ) from exc
                return

            if self.model_format == "torch_autoencoder":
                self._loaded_model = self._load_torch_autoencoder_bundle()
                return

            if self.model_format == "onnx":
                raise NotImplementedError(
                    "ONNX runtime adapter is not configured yet. Use joblib/pickle now "
                    "or add onnxruntime mapping in ml_runtime.py."
                )

            raise ValueError(
                "Unsupported model format. Use .joblib, .pkl, .pickle, .pt/.pth or .onnx."
            )

    @staticmethod
    def _risk_level(error: float, threshold: float) -> str:
        ratio = error / threshold if threshold > 0 else 0.0
        if ratio < 1.0:
            return "Low"
        if ratio < 50.0:
            return "Medium"
        if ratio < 150.0:
            return "High"
        return "Critical"

    def predict_with_context(
        self,
        features: Sequence[float] | Mapping[str, float | int],
    ) -> dict[str, Any]:
        self._ensure_loaded()

        model = self._loaded_model
        if model is None:
            raise RuntimeError("Model was not loaded.")

        if isinstance(model, dict) and model.get("kind") == "torch_autoencoder":
            feature_cols: list[str] = model["feature_cols"]
            threshold: float = model["threshold"]

            values: list[float]
            if isinstance(features, Mapping):
                missing = [name for name in feature_cols if name not in features]
                if missing:
                    raise ValueError(
                        "Missing features for autoencoder input: "
                        + ", ".join(missing[:10])
                    )
                try:
                    values = [float(features[name]) for name in feature_cols]
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        "Feature map contains non-numeric values."
                    ) from exc
            else:
                if len(features) != len(feature_cols):
                    raise ValueError(
                        "Feature vector size mismatch for autoencoder input: "
                        f"expected {len(feature_cols)}, got {len(features)}."
                    )
                try:
                    values = [float(value) for value in features]
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        "Feature vector contains non-numeric values."
                    ) from exc

            np = model["np"]
            torch = model["torch"]
            scaler = model["scaler"]
            autoencoder = model["model"]
            device = model["device"]

            try:
                data = np.array([values], dtype=np.float32)
                scaled = scaler.transform(data)
                tensor = torch.tensor(scaled, dtype=torch.float32).to(device)
                with torch.no_grad():
                    reconstructed = autoencoder(tensor).cpu().numpy()
                reconstruction_error = float(np.mean((scaled - reconstructed) ** 2))
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    "Model prediction failed for provided features."
                ) from exc

            label = "anomaly" if reconstruction_error > threshold else "normal"
            return {
                "prediction": reconstruction_error,
                "threshold": threshold,
                "label": label,
                "risk_level": self._risk_level(reconstruction_error, threshold),
            }

        if not hasattr(model, "predict"):
            raise RuntimeError("Loaded model has no predict() method.")

        try:
            feature_row = [float(value) for value in features]
        except (TypeError, ValueError) as exc:
            raise ValueError("Features must be a numeric list.") from exc

        try:
            raw_prediction = model.predict([feature_row])
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "Model prediction failed for provided features."
            ) from exc

        try:
            first_prediction = float(raw_prediction[0])
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("Model returned non-numeric prediction value.") from exc

        return {"prediction": first_prediction}

    def predict(self, features: Sequence[float] | Mapping[str, float | int]) -> float:
        prediction_payload = self.predict_with_context(features)
        return float(prediction_payload["prediction"])
