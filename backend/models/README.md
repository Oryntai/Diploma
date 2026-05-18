# ML model artifacts

Place trained model files in this directory.

Supported file formats by current scaffold:

- `*.joblib`
- `*.pkl` or `*.pickle`
- `*.onnx` (status tracking now, runtime adapter later)

Default configured path:

- `backend/models/best_autoencoder_ciciot23.pt`

Override path with environment variable:

- `ML_MODEL_PATH`

Example:

```bash
set ML_MODEL_PATH=models/my_trained_model.joblib
```
