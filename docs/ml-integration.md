# ML integration scaffold

This document describes how to connect a trained model to the current web/backend scaffold.

## Where to place the trained model

Default location:

- `backend/models/security_model.joblib`

Alternative location:

- put the file anywhere and set `ML_MODEL_PATH`.

Windows example:

```bash
set ML_MODEL_PATH=models/my_trained_model.joblib
```

PowerShell example:

```powershell
$env:ML_MODEL_PATH = "models/my_trained_model.joblib"
```

## Supported formats

- `.joblib`
- `.pkl` / `.pickle`
- `.pt` / `.pth` (PyTorch autoencoder bundle)
- `.onnx` (file readiness now, inference adapter to be added)

### PyTorch bundle layout

If you use the CICIoT23 autoencoder, keep these files in one directory:

- `best_autoencoder_ciciot23.pt`
- `scaler_ciciot23.pkl`
- `features_if_ciciot23.json` (or `features_ciciot23.json`)
- `threshold_ciciot23.json`

PowerShell example:

```powershell
$env:ML_MODEL_PATH = "models/best_autoencoder_ciciot23.pt"
```

## What is already prepared

- ML path configuration: `backend/app/core/settings.py`
- Runtime loader and status logic: `backend/app/services/ml_runtime.py`
- API schema contracts: `backend/app/schemas/ml.py`
- API routes:
  - `GET /api/ml/status`
  - `POST /api/ml/predict`
- Dashboard page with ML readiness block: `GET /`

## Integration contract for your teammate

If the model has `predict()` with sklearn-like API, no extra backend changes are needed.
For PyTorch autoencoder bundle, backend returns anomaly score as `prediction`
plus optional fields: `label`, `risk_level`, `threshold`.

Expected request:

```json
{
  "features": [0.1, 0.2, 0.3]
}
```

Expected response:

```json
{
  "prediction": 0.0,
  "model_format": "joblib",
  "model_path": "D:/Diploma/backend/models/security_model.joblib"
}
```

## Notes

- Keep model artifacts versioned by filename, for example `security_model_v1.joblib`.
- Store training metadata near the artifact (`metrics`, `feature order`, `trained_at`).
- Do not load untrusted pickle files from unknown sources.
