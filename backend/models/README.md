# ML model artifacts

Place trained model files in this directory.

Supported file formats by current scaffold:

- `*.joblib`
- `*.pkl` or `*.pickle`
- `*.onnx` (status tracking now, runtime adapter later)

Default configured path:

- `backend/models/security_model.joblib`

Override path with environment variable:

- `ML_MODEL_PATH`

Example:

```bash
set ML_MODEL_PATH=backend/models/my_trained_model.joblib
```
